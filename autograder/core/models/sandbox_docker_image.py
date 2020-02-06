from django.db import models

import autograder.core.fields as ag_fields

from .ag_model_base import AutograderModel
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
    ]

    EDITABLE_FIELDS = [
        'display_name',
        'tag',
    ]
