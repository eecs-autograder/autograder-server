from typing import Union

from django.core import exceptions
from django.db import models, transaction

import autograder.core.fields as ag_fields
from .ag_test_suite import AGTestSuite
from ..ag_model_base import AutograderModel


class AGTestCaseFeedbackConfig(AutograderModel):
    """
    Contains feedback options for an AGTestCase.
    """
    show_individual_commands = models.BooleanField(default=True)

    SERIALIZABLE_FIELDS = ('show_individual_commands',)
    EDITABLE_FIELDS = ('show_individual_commands',)


def make_default_test_fdbk() -> int:
    """
    Creates a new default AGTestCaseFeedbackConfig and returns its pk.
    """
    return AGTestCaseFeedbackConfig.objects.validate_and_create().pk


class AGTestCase(AutograderModel):
    """
    An AGTestCase consists of a series of commands to be run together.
    An AGTestCase must belong to exactly one AGTestSuite.
    """

    class Meta:
        unique_together = ('name', 'ag_test_suite')
        order_with_respect_to = 'ag_test_suite'

    name = ag_fields.ShortStringField(
        help_text='''The name used to identify this autograder test.
                     Must be non-empty and non-null.
                     Must be unique among autograder tests that belong to the same suite.
                     This field is REQUIRED.''')

    ag_test_suite = models.ForeignKey(
        AGTestSuite,
        related_name='ag_test_cases',
        help_text='''The suite this autograder test belongs to.
                     This field is REQUIRED.''')

    normal_fdbk_config = models.OneToOneField(
        AGTestCaseFeedbackConfig, default=make_default_test_fdbk,
        related_name='+',
        help_text='Feedback settings for a normal Submission.')
    ultimate_submission_fdbk_config = models.OneToOneField(
        AGTestCaseFeedbackConfig, default=make_default_test_fdbk,
        related_name='+',
        help_text='Feedback settings for an ultimate Submission.')
    past_limit_submission_fdbk_config = models.OneToOneField(
        AGTestCaseFeedbackConfig, default=make_default_test_fdbk,
        related_name='+',
        help_text='Feedback settings for a Submission that is past the daily limit.')
    staff_viewer_fdbk_config = models.OneToOneField(
        AGTestCaseFeedbackConfig, default=make_default_test_fdbk,
        related_name='+',
        help_text='Feedback settings for a staff member viewing a Submission from another group.')

    @transaction.atomic
    def validate_and_update(self, ag_test_suite: Union[int, AGTestSuite]=None, **kwargs):
        """
        :param ag_test_suite:
            An AGTestSuite (or its primary key) that this AGTestCase
            should be moved to.
            It is legal to assign an AGTestCase to a different
            AGTestSuite as long as the old and new suites belong to
            the same Project.
        """
        # If we're updating this test case's ag test suite, we need
        # to steal all the suite results from the current suite and
        # give them to the new one.
        if ag_test_suite is None:
            super().validate_and_update(**kwargs)
            return

        if isinstance(ag_test_suite, int):
            ag_test_suite = AGTestSuite.objects.get(pk=ag_test_suite)

        if ag_test_suite.project != self.ag_test_suite.project:
            raise exceptions.ValidationError(
                {'ag_test_suite':
                    'AGTestCases can only be moved to AGTestSuites within the same Project.'})

        self.ag_test_suite.agtestsuiteresult_set.update(ag_test_suite=ag_test_suite)
        self.ag_test_suite = ag_test_suite
        super().validate_and_update(**kwargs)

    SERIALIZABLE_FIELDS = (
        'name',
        'ag_test_suite',
        'ag_test_commands',
        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config',
    )

    SERIALIZE_RELATED = ('ag_test_commands',)

    EDITABLE_FIELDS = (
        'name',
        'ag_test_suite',

        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config',
    )

    TRANSPARENT_TO_ONE_FIELDS = (
        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config',
    )