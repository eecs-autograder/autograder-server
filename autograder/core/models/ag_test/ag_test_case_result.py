from typing import List, Iterable

from django.db import models

from ..ag_model_base import AutograderModel, ToDictMixin
from .ag_test_case import AGTestCase, AGTestCaseFeedbackConfig
from .ag_test_suite_result import AGTestSuiteResult
from .feedback_category import FeedbackCategory


class AGTestCaseResult(AutograderModel):
    ag_test_case = models.ForeignKey(
        AGTestCase, related_name='related_ag_test_case_results',
        help_text='The AGTestCase that this result belongs to.')

    ag_test_suite_result = models.ForeignKey(
        AGTestSuiteResult, related_name='ag_test_case_results',
        help_text='The AGTestSuiteResult that this result belongs to.')

    def get_fdbk(self, fdbk_category: FeedbackCategory) -> 'AGTestCaseResult.FeedbackCalculator':
        return AGTestCaseResult.FeedbackCalculator(self, fdbk_category)

    class FeedbackCalculator(ToDictMixin):
        def __init__(self, ag_test_case_result: 'AGTestCaseResult',
                     fdbk_category: FeedbackCategory):
            self._ag_test_case_result = ag_test_case_result
            self._fdbk_category = fdbk_category
            self._ag_test_case = self._ag_test_case_result.ag_test_case

            if fdbk_category == FeedbackCategory.normal:
                self._fdbk = self._ag_test_case.normal_fdbk_config
            elif fdbk_category == FeedbackCategory.ultimate_submission:
                self._fdbk = self._ag_test_case.ultimate_submission_fdbk_config
            elif fdbk_category == FeedbackCategory.past_limit_submission:
                self._fdbk = self._ag_test_case.past_limit_submission_fdbk_config
            elif fdbk_category == FeedbackCategory.staff_viewer:
                self._fdbk = self._ag_test_case.staff_viewer_fdbk_config
            elif fdbk_category == FeedbackCategory.max:
                self._fdbk = AGTestCaseFeedbackConfig(show_individual_commands=True)

        @property
        def fdbk_conf(self):
            return self._fdbk

        @property
        def pk(self):
            return self._ag_test_case_result.pk

        @property
        def ag_test_case_name(self):
            return self._ag_test_case.name

        @property
        def ag_test_case_pk(self):
            return self._ag_test_case.pk

        @property
        def fdbk_settings(self) -> dict:
            return self._fdbk.to_dict()

        @property
        def total_points(self):
            points = sum((cmd_res.get_fdbk(self._fdbk_category).total_points for cmd_res in
                          self._visible_cmd_results))
            return max(0, points)

        @property
        def total_points_possible(self):
            return sum((cmd_res.get_fdbk(self._fdbk_category).total_points_possible for cmd_res in
                        self._visible_cmd_results))

        @property
        def ag_test_command_results(self) -> List['AGTestCommandResult']:
            if not self._fdbk.show_individual_commands:
                return []

            cmd_order = list(self._ag_test_case.get_agtestcommand_order())
            results = sorted(self._visible_cmd_results,
                             key=lambda result: cmd_order.index(result.ag_test_command.pk))
            return list(results)

        @property
        def _visible_cmd_results(self) -> Iterable['AGTestCommandResult']:
            return filter(
                lambda result: result.get_fdbk(self._fdbk_category).fdbk_conf.visible,
                self._ag_test_case_result.ag_test_command_results.all())

        def to_dict(self):
            result = super().to_dict()
            result['ag_test_command_results'] = [
                result.get_fdbk(self._fdbk_category).to_dict()
                for result in self.ag_test_command_results
            ]
            return result

        SERIALIZABLE_FIELDS = (
            'pk',
            'ag_test_case_name',
            'ag_test_case_pk',
            'fdbk_settings',
            'total_points',
            'total_points_possible',
        )
