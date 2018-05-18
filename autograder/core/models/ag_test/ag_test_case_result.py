from typing import List, Iterable

from django.db import models

from ..ag_model_base import AutograderModel, ToDictMixin
from .ag_test_case import AGTestCase, AGTestCaseFeedbackConfig
from .feedback_category import FeedbackCategory
from .ag_test_command_result import AGTestCommandResult


class AGTestCaseResult(AutograderModel):
    class Meta:
        unique_together = ('ag_test_case', 'ag_test_suite_result')
        ordering = ('ag_test_case___order',)

    ag_test_case = models.ForeignKey(
        AGTestCase, related_name='related_ag_test_case_results',
        on_delete=models.CASCADE,
        help_text='The AGTestCase that this result belongs to.')

    ag_test_suite_result = models.ForeignKey(
        'AGTestSuiteResult', related_name='ag_test_case_results',
        on_delete=models.CASCADE,
        help_text='The AGTestSuiteResult that this result belongs to.')

    # SERIALIZABLE_FIELDS = (
    #     'ag_test_case_id',
    #     'ag_test_suite_result_id',
    # )
