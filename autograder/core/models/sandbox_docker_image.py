import enum
import os

from django.conf import settings
from django.core import exceptions
from django.db import models, transaction

import autograder.core.fields as ag_fields
import autograder.core.utils as core_ut

from .ag_model_base import AutograderModel, AutograderModelManager
from .course import Course


def get_default_image_pk():
    return SandboxDockerImage.objects.get(display_name='Default', course=None).pk


class SandboxDockerImage(AutograderModel):
    """
    Contains the information required to identify and load sandbox
    Docker images when running test suites.
    """

    class Meta:
        ordering = ('display_name',)
        unique_together = ('display_name', 'course')

    name = ag_fields.ShortStringField(
        blank=False,
        unique=True,
        help_text="""A string uniquely identifying this sandbox image.
                     This field is required and cannot be edited after
                     creation.""")

    display_name = ag_fields.ShortStringField(
        blank=False,
        help_text="""A human-readable name for this sandbox image.
                     Must be unique among images belonging to a course.
                     This field is required.""")

    course = models.ForeignKey(
        Course,
        blank=True, null=True, default=None,
        on_delete=models.CASCADE,
        related_name='sandbox_docker_images',
        help_text="The course this image is associated with.")

    tag = models.TextField(
        blank=False,
        help_text="""The full name and tag that can be used to fetch the image
                     with the 'docker pull' command, e.g. localhost:5555/eecs280:latest."""
    )

    def full_clean(self, *args, **kwargs):
        if not self.name:
            self.name = self.display_name
            if self.course is not None:
                self.name += str(self.course.pk)

        return super().full_clean(*args, **kwargs)

    SERIALIZABLE_FIELDS = [
        'pk',
        'display_name',
        'course',
        'last_modified',
    ]

    EDITABLE_FIELDS = [
        'display_name',
    ]


class _BuildSandboxDockerImageManager(AutograderModelManager):
    @transaction.atomic
    def validate_and_create(
        self, files, course, image=None
    ) -> 'BuildSandboxDockerImageTask':
        pending_tasks_for_image = BuildSandboxDockerImageTask.objects.filter(
            image=image,
            status__in=[BuildImageStatus.queued, BuildImageStatus.in_progress]
        )
        if image is not None and pending_tasks_for_image.exists():
            raise exceptions.ValidationError({'image': 'There is a '})

        build_task = self.model(
            course=course,
            image=image,
        )
        # Create the directory to put the files in (needs a pk)
        build_task.save()

        if 'Dockerfile' not in [file_.name for file_ in files]:
            raise exceptions.ValidationError({
                'files': 'Image builds must include a file named "Dockerfile"'
            })

        for file_ in files:
            core_ut.check_filename(file_.name)
            build_task.filenames.append(file_.name)
            write_dest = os.path.join(
                build_task.build_dir,
                file_.name
            )
            with open(write_dest, 'wb') as f:
                for chunk in file_.chunks():
                    f.write(chunk)

        build_task.full_clean()
        build_task.save()
        return build_task


class BuildImageStatus(enum.Enum):
    queued = 'queued'
    in_progress = 'in_progress'
    done = 'done'
    image_invalid = 'image_invalid'
    cancelled = 'cancelled'
    internal_error = 'internal_error'


class BuildSandboxDockerImageTask(AutograderModel):
    objects = _BuildSandboxDockerImageManager()

    status = ag_fields.EnumField(
        BuildImageStatus, blank=True, default=BuildImageStatus.queued,
        help_text="The status of the build."
    )

    return_code = models.IntegerField(
        blank=True, null=True, default=None,
        help_text="The exit status of the build command."
    )

    timed_out = models.BooleanField(
        blank=True, default=False,
        help_text="True if the build timed out."
    )

    filenames = ag_fields.StringArrayField(
        blank=True, default=list,
        help_text="The names of the files uploaded by the user."
    )

    course = models.ForeignKey(
        'core.Course', related_name='build_sandbox_docker_image_tasks',
        on_delete=models.CASCADE,
        blank=True, null=True, default=None,
        help_text="""The course this task is associated with.
            Only superusers can create or update images with no associated course.
        """
    )

    image = models.ForeignKey(
        SandboxDockerImage, blank=True, null=True, default=None,
        on_delete=models.CASCADE,
        help_text="""When initially null, indicates that a new image will be created.
            That new image will then be set as the value for this field.

            When not null initially, indicates that the specified image
            should be updated when the build finishes."""
    )

    validation_error_msg = models.TextField(
        blank=True,
        help_text="Information for the user as to while the built image is invalid."
    )

    internal_error_msg = models.TextField(
        blank=True,
        help_text="If an internal error occurs, the error message will be stored here."
    )

    @property
    def output_filename(self) -> str:
        return os.path.join(
            self.build_dir,
            f'__build{self.pk}_output',
        )

    @property
    def build_dir(self) -> str:
        return get_build_sandbox_docker_image_task_dir(self)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        dirname = self.build_dir
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

    def clean(self, *args, **kwargs):
        if self.image is None:
            return

        if self.image.course != self.course:
            raise exceptions.ValidationError({
                'image':
                    'Image to update must belong to the same course as the build task.'
            })

    SERIALIZABLE_FIELDS = [
        'pk',
        'status',
        'return_code',
        'timed_out',
        'filenames',
        'course_id',
        'image',
        'validation_error_msg',
        'internal_error_msg',
    ]

    SERIALIZE_RELATED = [
        'image',
    ]


def get_build_sandbox_docker_image_task_dir(build_task: BuildSandboxDockerImageTask) -> str:
    path_parts = [
        settings.MEDIA_ROOT,
        'image_builds',
    ]
    if build_task.course is not None:
        path_parts.append(f'course{build_task.course.pk}')
    return os.path.join(
        *path_parts,
        f'task{build_task.pk}',
    )
