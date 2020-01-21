from django.db import models

import autograder.core.fields as ag_fields

from .ag_model_base import AutograderModel
from .course import Course


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
        # unique=True,
        help_text="""A human-readable name for this sandbox image.
                     This field is required.""")

    course = models.ForeignKey(
        Course,
        blank=True, null=True, default=None,
        on_delete=models.CASCADE,
        help_text="The course this image is associated with.")

    tag = models.TextField(
        blank=False,
        help_text="""The full tag that can be used to fetch the image with
                     the 'docker pull' command. This should include a specific
                     version for the image, and the version number should be
                     incremented every time the image is updated, otherwise
                     the new version of the image may not be fetched."""
    )

    SERIALIZABLE_FIELDS = [
        'pk',
        'name',
        'display_name',
        'tag',
    ]

    EDITABLE_FIELDS = [
        'display_name',
        'tag',
    ]
