import os


from django.db import models, transaction, connection

import autograder.core.utils as core_ut

from ..ag_command import AGCommandResultBase
from .ag_test_command import AGTestCommand


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

    # Serializing AGTestCommandResults should be used for DENORMALIZATION
    # ONLY.
    SERIALIZABLE_FIELDS = (
        'pk',

        'ag_test_command_id',
        'ag_test_case_result_id',

        'return_code',
        'return_code_correct',

        'timed_out',

        'stdout_correct',
        'stderr_correct',

        'stdout_truncated',
        'stderr_truncated',
    )
