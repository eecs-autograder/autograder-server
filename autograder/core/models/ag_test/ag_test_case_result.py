from typing import Sequence

from django.db import models

from ..ag_model_base import AutograderModel, ToDictMixin
from .ag_test_case import AGTestCase, AGTestCaseFeedbackConfig
from .ag_test_suite_result import AGTestSuiteResult
from .feedback_category import FeedbackCategory


class AGTestCaseResult(AutograderModel):
    ag_test_case = models.ForeignKey(
        AGTestCase, help_text='The AGTestCase that this result belongs to.')

    ag_test_suite_result = models.ForeignKey(
        AGTestSuiteResult, help_text='The AGTestSuiteResult that this result belongs to.')

    def get_fdbk(self, fdbk_category: FeedbackCategory) -> 'AGTestCaseResult.FeedbackCalculator':
        return AGTestCaseResult.FeedbackCalculator(self, fdbk_category)

    class FeedbackCalculator(ToDictMixin):
        def __init__(self, result: 'AGTestCaseResult',
                     fdbk_category: FeedbackCategory):
            self._result = result
            self._fdbk_category = fdbk_category
            self._ag_test = self._result.ag_test_case

            if fdbk_category == FeedbackCategory.normal:
                self._fdbk = self._ag_test.normal_fdbk_config
            elif fdbk_category == FeedbackCategory.ultimate_submission:
                self._fdbk = self._ag_test.ultimate_submission_fdbk_config
            elif fdbk_category == FeedbackCategory.past_limit_submission:
                self._fdbk = self._ag_test.past_limit_submission_fdbk_config
            elif fdbk_category == FeedbackCategory.staff_viewer:
                self._fdbk = self._ag_test.staff_viewer_fdbk_config
            elif fdbk_category == FeedbackCategory.max:
                self._fdbk = AGTestCaseFeedbackConfig(show_individual_commands=True)

        @property
        def fdbk_conf(self):
            return self._fdbk

        @property
        def pk(self):
            return self._result.pk

        @property
        def ag_test_case_name(self):
            return self._ag_test.name

        @property
        def ag_test_command_pk(self):
            return self._ag_test.pk

        @property
        def fdbk_settings(self) -> dict:
            return self._fdbk.to_dict()

        @property
        def total_points(self):
            points = sum((cmd_res.get_fdbk(self._fdbk_category).total_points for cmd_res in
                          self._result.ag_test_command_results.all()))
            return max(0, points)

        @property
        def total_points_possible(self):
            return sum((cmd_res.get_fdbk(self._fdbk_category).total_points_possible for cmd_res in
                        self._result.ag_test_command_results.all()))

        @property
        def ag_test_command_results(self) -> Sequence['AGTestCommandResult']:
            if not self._fdbk.show_individual_commands:
                return []

            return self._result.ag_test_command_results.all()

        SERIALIZABLE_FIELDS = (
            'pk',
            'ag_test_case_name',
            'ag_test_command_pk',
            'fdbk_settings',
            'total_points',
            'total_points_possible',
        )
