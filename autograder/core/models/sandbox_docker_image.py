import enum
import os

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
                     with the 'docker pull' command, e.g. jameslp/eecs280:2.
                     This should include a specific
                     version for the image, and the version number should be
                     incremented by the user every time the image is updated,
                     otherwise the new version of the image will not be
                     fetched."""
    )

    validation_warning = models.TextField(
        blank=True,
        help_text="Warning text from image validation. If empty, then validation succeeded.")

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
        'tag',
        'validation_warning',
    ]

    EDITABLE_FIELDS = [
        'display_name',
        'tag',
    ]


class _BuildSandboxDockerImageManager(AutograderModelManager):
    @transaction.atomic
    def validate_and_create(self, files, course, image_to_update=None):
        build_task = self.model(
            course=course,
            image_to_update=image_to_update,
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
                get_build_sandbox_docker_image_task_dir(build_task),
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
    succeeded = 'succeeded'
    cancelled = 'cancelled'
    failed = 'failed'


class BuildSandboxDockerImageTask(AutograderModel):
    objects = _BuildSandboxDockerImageManager()

    status = ag_fields.EnumField(
        BuildImageStatus, blank=True, default=BuildImageStatus.queued,
        help_text="The status of the build."
    )

    filenames = ag_fields.StringArrayField(
        blank=True, default=list,
        help_text="The names of the files uploaded by the user."
    )

    course = models.ForeignKey(
        'core.Course', related_name='build_sandbox_docker_image_tasks',
        on_delete=models.CASCADE,
        help_text="The course this task is associated with."
    )

    image_to_update = models.ForeignKey(
        SandboxDockerImage, blank=True, null=True, default=None,
        on_delete=models.SET_NULL,
        help_text="""When null, indicates that a new image will be created.
            Otherwise, refers to the image to be updated on build success."""
    )

    @property
    def output_filename(self) -> str:
        return os.path.join(
            get_build_sandbox_docker_image_task_dir(self),
            f'__build{self.pk}_output',
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        dirname = get_build_sandbox_docker_image_task_dir(self)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

    def clean(self, *args, **kwargs):
        if self.image_to_update is None:
            return

        if self.image_to_update.course is None:
            raise exceptions.ValidationError(
                {'image_to_update': 'Image to update must belong to a course.'})

        if self.image_to_update.course != self.course:
            raise exceptions.ValidationError({
                'image_to_update':
                    'Image to update must belong to the same course as the build task.'
            })


def get_build_sandbox_docker_image_task_dir(build_task: BuildSandboxDockerImageTask) -> str:
    return os.path.join(
        core_ut.get_course_root_dir(build_task.course),
        'image_builds',
        f'task{build_task.pk}',
    )
