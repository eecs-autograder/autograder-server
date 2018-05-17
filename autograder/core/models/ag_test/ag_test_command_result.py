import os
import tempfile
from typing import Optional, BinaryIO

from django.db import models

import autograder.core.utils as core_ut

from ..ag_model_base import ToDictMixin
from ..ag_command import AGCommandResultBase
from .ag_test_command import (
    AGTestCommand, AGTestCommandFeedbackConfig, ExpectedReturnCode, ValueFeedbackLevel,
    ExpectedOutputSource, MAX_AG_TEST_COMMAND_FDBK_SETTINGS)
from .feedback_category import FeedbackCategory


class AGTestCommandResult(AGCommandResultBase):
    """
    This class stores the data from an AGTestCommand
    and provides an interface for serializing the data with different
    feedback levels.
    """
    class Meta:
        unique_together = ('ag_test_command', 'ag_test_case_result')
        ordering = ('ag_test_command___order',)

    ag_test_command = models.ForeignKey(
        AGTestCommand, on_delete=models.CASCADE,
        help_text='The AGTestCommand this result belongs to.')

    ag_test_case_result = models.ForeignKey(
        'AGTestCaseResult', related_name='ag_test_command_results',
        on_delete=models.CASCADE,
        help_text='''The AGTestCaseResult that this result belongs to.
                     A value of None indicates that this AGTestCommandResult
                     is the result of an AGTestSuite's setup command.''')

    return_code_correct = models.NullBooleanField(null=True, default=None)
    stdout_correct = models.NullBooleanField(null=True, default=None)
    stderr_correct = models.NullBooleanField(null=True, default=None)

    @property
    def stdout_filename(self):
        result_output_dir = core_ut.get_result_output_dir(
            self.ag_test_case_result.ag_test_suite_result.submission)
        return os.path.join(result_output_dir, 'cmd_result_{}_stdout'.format(self.pk))

    @property
    def stderr_filename(self):
        result_output_dir = core_ut.get_result_output_dir(
            self.ag_test_case_result.ag_test_suite_result.submission)
        return os.path.join(result_output_dir, 'cmd_result_{}_stderr'.format(self.pk))
