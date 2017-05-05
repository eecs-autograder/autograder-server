from django.db import models

import autograder.core.fields as ag_fields
from ..ag_model_base import AutograderModel


class AGTestCaseFeedbackConfig(AutograderModel):
    """
    Contains feedback options for an AGTestCase.
    """
    show_individual_commands = models.BooleanField(default=True)

    SERIALIZABLE_FIELDS = ['show_individual_commands']
    EDITABLE_FIELDS = ['show_individual_commands']


def make_default_test_fdbk() -> AGTestCaseFeedbackConfig:
    return AGTestCaseFeedbackConfig.objects.validate_and_create()


class AGTestCase(AutograderModel):
    """
    An AGTestCase consists of a series of commands to be run together.
    An AGTestCase must belong to exactly one AGTestSuite.
    """

    class Meta:
        unique_together = ('name', 'ag_test_suite')
        order_with_respect_to = ('ag_test_suite',)

    name = ag_fields.ShortStringField(
        help_text="""The name used to identify this autograder test.
                     Must be non-empty and non-null.
                     Must be unique among autograder tests that belong to the same suite.
                     This field is REQUIRED.""")

    ag_test_suite = models.ForeignKey(
        'AGTestSuite',
        help_text="""The suite this autograder test belongs to.
                     This field is REQUIRED.""")

    normal_fdbk_config = models.OneToOneField(
        AGTestCaseFeedbackConfig, default=make_default_test_fdbk,
        help_text="""Feedback settings for a normal Submission.""")
    ultimate_submission_fdbk_config = models.OneToOneField(
        AGTestCaseFeedbackConfig, default=make_default_test_fdbk,
        help_text="""Feedback settings for an ultimate Submission.""")
    past_limit_submission_fdbk_config = models.OneToOneField(
        AGTestCaseFeedbackConfig, default=make_default_test_fdbk,
        help_text="""Feedback settings for a Submission that is past the daily limit.""")
    staff_viewer_fdbk_config = models.OneToOneField(
        AGTestCaseFeedbackConfig, default=make_default_test_fdbk,
        help_text="""Feedback settings for a staff member viewing a Submission from another
                     group.""")

    SERIALIZABLE_FIELDS = ['name', 'ag_test_suite']
    EDITABLE_FIELDS = ['name', 'ag_test_suite']
