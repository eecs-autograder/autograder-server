from django.db import models

import autograder.core.fields as ag_fields
from autograder.core.models import AutograderModel


class SandboxDockerImage(AutograderModel):
    name = ag_fields.ShortStringField(
        blank=False, unique=True,
        help_text="""A human-readable name used to identify this sandbox image.
                     This field is required.""")

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
        'tag',
    ]

    EDITABLE_FIELDS = [
        'name',
        'tag',
    ]
