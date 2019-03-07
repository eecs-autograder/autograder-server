from django.db import models

import autograder.core.fields as ag_fields
from autograder.core.models import AutograderModel


# NOTE: Migration 0036 creates a "default" image entry in the database,
# but only if we aren't running tests. For tests, we've added a fixture
# in autograder/core/fixture/default_sandbox_image.json to create the
# default image for tests (the UnitTestBase class handles loading the fixture).
#
# IMPORTANT: If the version of the default image changes, be sure to update
# the tag field in autograder/core/fixture/default_sandbox_image.json
class SandboxDockerImage(AutograderModel):
    """
    Contains the information required to identify and load sandbox
    Docker images when running test suites.
    """

    class Meta:
        ordering = ('display_name',)

    name = ag_fields.ShortStringField(
        blank=False,
        unique=True,
        help_text="""A string uniquely identifying this sandbox image.
                     This field is required and cannot be edited after
                     creation.""")

    display_name = ag_fields.ShortStringField(
        blank=False,
        unique=True,
        help_text="""A human-readable name for this sandbox image.
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
        'display_name',
        'tag',
    ]

    EDITABLE_FIELDS = [
        'display_name',
        'tag',
    ]
