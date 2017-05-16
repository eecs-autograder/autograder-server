from django.db import models

from ..ag_model_base import AutograderModel, ToDictMixin
from .ag_test_case import AGTestCase
from .ag_test_suite_result import AGTestSuiteResult


class AGTestCaseResult(AutograderModel):
    ag_test_case = models.ForeignKey(
        AGTestCase, help_text='The AGTestCase that this result belongs to.')

    ag_test_suite_result = models.ForeignKey(
        AGTestSuiteResult, help_text='The AGTestSuiteResult that this result belongs to.')

    class FeedbackCalculator(ToDictMixin):
        pass
