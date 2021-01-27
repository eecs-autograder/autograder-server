from typing import Any, Dict, Optional, Tuple, Union

from django.core import exceptions
from django.db import connection, models, transaction

import autograder.core.fields as ag_fields
from autograder.core.constants import MAX_CHAR_FIELD_LEN

from ..ag_model_base import AutograderModel, AutograderModelManager, DictSerializable
from .ag_test_suite import AGTestSuite


class AGTestCaseFeedbackConfig(DictSerializable):
    """
    Contains feedback options for an AGTestCase.
    """
    def __init__(self, visible: bool = True, show_individual_commands: bool = True):
        self.visible = visible
        self.show_individual_commands = show_individual_commands

    SERIALIZABLE_FIELDS = ('visible', 'show_individual_commands',)


class AGTestCase(AutograderModel):
    """
    An AGTestCase consists of a series of commands to be run together.
    An AGTestCase must belong to exactly one AGTestSuite.
    """
    objects = AutograderModelManager['AGTestCase']()

    class Meta:
        unique_together = ('name', 'ag_test_suite')
        order_with_respect_to = 'ag_test_suite'

    name = models.CharField(
        max_length=MAX_CHAR_FIELD_LEN,
        help_text='''The name used to identify this autograder test.
                     Must be non-empty and non-null.
                     Must be unique among autograder tests that belong to the same suite.
                     This field is REQUIRED.''')

    ag_test_suite = models.ForeignKey(
        AGTestSuite,
        related_name='ag_test_cases',
        on_delete=models.CASCADE,
        help_text='''The suite this autograder test belongs to.
                     This field is REQUIRED.''')

    normal_fdbk_config = ag_fields.ValidatedJSONField(
        AGTestCaseFeedbackConfig, default=AGTestCaseFeedbackConfig)
    ultimate_submission_fdbk_config = ag_fields.ValidatedJSONField(
        AGTestCaseFeedbackConfig, default=AGTestCaseFeedbackConfig)
    past_limit_submission_fdbk_config = ag_fields.ValidatedJSONField(
        AGTestCaseFeedbackConfig, default=AGTestCaseFeedbackConfig)
    staff_viewer_fdbk_config = ag_fields.ValidatedJSONField(
        AGTestCaseFeedbackConfig, default=AGTestCaseFeedbackConfig)

    @transaction.atomic
    def validate_and_update(  # type: ignore
        self,
        ag_test_suite: Optional[Union[int, AGTestSuite]] = None,
        **kwargs: Any
    ):
        """
        :param ag_test_suite:
            An AGTestSuite (or its primary key) that this AGTestCase
            should be moved to.
            It is legal to assign an AGTestCase to a different
            AGTestSuite as long as the old and new suites belong to
            the same Project.
        """
        move_suite = False
        if ag_test_suite is not None:
            if isinstance(ag_test_suite, int):
                move_suite = self.ag_test_suite.pk != ag_test_suite
            else:
                move_suite = self.ag_test_suite != ag_test_suite

        if not move_suite:
            super().validate_and_update(**kwargs)
            return

        if isinstance(ag_test_suite, int):
            ag_test_suite = AGTestSuite.objects.get(pk=ag_test_suite)

        assert ag_test_suite is not None
        if ag_test_suite.project != self.ag_test_suite.project:
            raise exceptions.ValidationError(
                {'ag_test_suite':
                    'AGTestCases can only be moved to AGTestSuites within the same Project.'})

        # Update all the AGTestCaseResult objects that belong to this
        # AGTestCase so that they belong to AGTestSuiteResults that
        # belong to the destination AGTestSuite.

        from .ag_test_suite_result import AGTestSuiteResult

        for ag_test_case_result in self.related_ag_test_case_results.select_related(
                'ag_test_suite_result__submission').all():
            dest_suite_result = AGTestSuiteResult.objects.get_or_create(
                ag_test_suite=ag_test_suite,
                submission=ag_test_case_result.ag_test_suite_result.submission)[0]
            ag_test_case_result.ag_test_suite_result = dest_suite_result
            ag_test_case_result.save()

        self.ag_test_suite = ag_test_suite

        super().validate_and_update(**kwargs)

    @transaction.atomic()
    def delete(self, *args: Any, **kwargs: Any) -> Tuple[int, Dict[str, int]]:
        with connection.cursor() as cursor:
            cursor.execute(
                '''UPDATE core_submission
                SET denormalized_ag_test_results =
                    denormalized_ag_test_results #- '{%s,ag_test_case_results,%s}'
                WHERE core_submission.project_id = %s
                ''',
                (self.ag_test_suite_id,
                 self.pk,
                 self.ag_test_suite.project_id)
            )

        return super().delete()

    SERIALIZABLE_FIELDS = (
        'pk',
        'name',
        'last_modified',
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
