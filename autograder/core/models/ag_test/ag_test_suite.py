from django.db import models

import autograder.core.fields as ag_fields
from autograder.core import constants
from ..ag_model_base import AutograderModel
from ..project import ExpectedStudentFilePattern, Project, UploadedFile


class AGTestSuiteFeedbackConfig(AutograderModel):
    """
    Contains feedback options for an AGTestSuite.
    """

    show_individual_tests = models.BooleanField(
        default=True,
        help_text='''Whether to show information about individual tests in a suite or just a
                     points summary (if available).''')

    # Is this redundant with the visibility setting in AGTestCommand?
    show_setup_command = models.BooleanField(
        default=True, help_text="Whether to show information about a suite's setup command.")

    SERIALIZABLE_FIELDS = (
        'show_individual_tests',
        'show_setup_command',
    )

    EDITABLE_FIELDS = (
        'show_individual_tests',
        'show_setup_command',
    )


def make_default_suite_fdbk() -> int:
    """
    Creates a new default AGTestSuiteFeedbackConfig object and returns its pk
    """
    return AGTestSuiteFeedbackConfig.objects.validate_and_create().pk


class AGTestSuite(AutograderModel):
    """
    A group of autograder test cases to be run inside the same sandbox.

    Related object fields:
        setup_command -- A command to be run before any of the test cases in this suite are run.
            This command is run exactly *once* at the beginning of the suite,
            NOT before each individual test.
    """

    class Meta:
        unique_together = ('name', 'project')
        order_with_respect_to = 'project'

    name = ag_fields.ShortStringField(
        help_text='''The name used to identify this suite.
                     Must be non-empty and non-null.
                     Must be unique among suites that belong to the same project.
                     This field is REQUIRED.''')

    project = models.ForeignKey(Project, related_name='ag_test_suites',
                                help_text='''The project this suite belongs to.
                                             This field is sREQUIRED.''')

    project_files_needed = models.ManyToManyField(
        UploadedFile,
        help_text='''The project files that will be copied into the sandbox before the suite's
                     tests are run.''')

    student_files_needed = models.ManyToManyField(
        ExpectedStudentFilePattern,
        help_text='''Student-submitted files matching these patterns will be copied into the
                     sandbox before the suite's tests are run.''')

    docker_image_to_use = ag_fields.ShortStringField(
        choices=zip(constants.SUPPORTED_DOCKER_IMAGES, constants.SUPPORTED_DOCKER_IMAGES),
        default=constants.DEFAULT_DOCKER_IMAGE,
        help_text='''The name of the Docker image that the sandbox should be created using.''')

    allow_network_access = models.BooleanField(
        default=False,
        help_text='''Specifies whether the sandbox should allow commands run inside of it to
                     make network calls outside of the sandbox.''')

    deferred = models.BooleanField(
        default=False,
        help_text='''If true, this test suite can be graded asynchronously. Deferred suites that
                     have yet to be graded do not prevent members of a group from submitting
                     again.''')

    normal_fdbk_config = models.OneToOneField(
        AGTestSuiteFeedbackConfig, default=make_default_suite_fdbk,
        related_name='+',
        help_text='Feedback settings for a normal submission.')
    ultimate_submission_fdbk_config = models.OneToOneField(
        AGTestSuiteFeedbackConfig, default=make_default_suite_fdbk,
        related_name='+',
        help_text='Feedback settings for an ultimate submission.')
    past_limit_submission_fdbk_config = models.OneToOneField(
        AGTestSuiteFeedbackConfig, default=make_default_suite_fdbk,
        related_name='+',
        help_text='Feedback settings for a submission that is past the daily limit.')
    staff_viewer_fdbk_config = models.OneToOneField(
        AGTestSuiteFeedbackConfig, default=make_default_suite_fdbk,
        related_name='+',
        help_text='Feedback settings for a staff member viewing a submission from another group.')

    SERIALIZABLE_FIELDS = (
        'name',
        'project',
        'project_files_needed',
        'student_files_needed',
        'allow_network_access',
        'deferred',
    )

    EDITABLE_FIELDS = (
        'name',
        'project_files_needed',
        'student_files_needed',
        'allow_network_access',
        'deferred',
    )
