from django.db import models

from ..ag_model_base import AutograderModel, ToDictMixin
from .ag_test_suite import AGTestSuite
from ..submission import Submission


class AGTestSuiteResult(AutograderModel):
    ag_test_suite = models.ForeignKey(
        AGTestSuite, help_text='The AGTestSuite that this result belongs to.')

    submission = models.ForeignKey(Submission, help_text='The Submission that this result is for.')

    class FeedbackCalculator(ToDictMixin):
        pass
