import os
import tempfile
from typing import Optional, BinaryIO

from django.db import models

from autograder.core.models.ag_model_base import ToDictMixin
import autograder.core.utils as core_ut

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
        return _get_cmd_result_stdout_filename(self)

    @property
    def stderr_filename(self):
        return _get_cmd_result_stderr_filename(self)

    def get_fdbk(self,
                 fdbk_category: FeedbackCategory) -> 'AGTestCommandResult.FeedbackCalculator':
        return AGTestCommandResult.FeedbackCalculator(self, fdbk_category)

    class FeedbackCalculator(ToDictMixin):
        """
        Instances of this class dynamically calculate the appropriate
        feedback data to give for an AGTestCommandResult.
        """

        def __init__(self, ag_test_command_result: 'AGTestCommandResult',
                     fdbk_category: FeedbackCategory):
            self._ag_test_command_result = ag_test_command_result
            self._cmd = self._ag_test_command_result.ag_test_command

            if fdbk_category == FeedbackCategory.normal:
                self._fdbk = self._cmd.normal_fdbk_config
            elif fdbk_category == FeedbackCategory.ultimate_submission:
                self._fdbk = self._cmd.ultimate_submission_fdbk_config
            elif fdbk_category == FeedbackCategory.past_limit_submission:
                self._fdbk = self._cmd.past_limit_submission_fdbk_config
            elif fdbk_category == FeedbackCategory.staff_viewer:
                self._fdbk = self._cmd.staff_viewer_fdbk_config
            elif fdbk_category == FeedbackCategory.max:
                self._fdbk = AGTestCommandFeedbackConfig(**MAX_AG_TEST_COMMAND_FDBK_SETTINGS)

        @property
        def pk(self):
            return self._ag_test_command_result.pk

        @property
        def ag_test_command_name(self) -> str:
            return self._cmd.name

        @property
        def ag_test_command_pk(self) -> pk:
            return self._cmd.pk

        @property
        def fdbk_conf(self) -> AGTestCommandFeedbackConfig:
            """
            :return: The FeedbackConfig object that this object was
            initialized with.
            """
            return self._fdbk

        @property
        def fdbk_settings(self) -> dict:
            return self.fdbk_conf.to_dict()

        @property
        def timed_out(self) -> Optional[bool]:
            if self._fdbk.show_whether_timed_out:
                return self._ag_test_command_result.timed_out

            return None

        @property
        def return_code_correct(self) -> Optional[bool]:
            if (self._cmd.expected_return_code == ExpectedReturnCode.none or
                    self._fdbk.return_code_fdbk_level == ValueFeedbackLevel.no_feedback):
                return None

            return self._ag_test_command_result.return_code_correct

        @property
        def expected_return_code(self) -> Optional[ValueFeedbackLevel]:
            if self._fdbk.return_code_fdbk_level != ValueFeedbackLevel.expected_and_actual:
                return None

            return self._cmd.expected_return_code

        @property
        def actual_return_code(self) -> Optional[int]:
            if (self._fdbk.show_actual_return_code or
                    self._fdbk.return_code_fdbk_level == ValueFeedbackLevel.expected_and_actual):
                return self._ag_test_command_result.return_code

            return None

        @property
        def return_code_points(self) -> int:
            if self.return_code_correct is None:
                return 0

            if self._ag_test_command_result.return_code_correct:
                return self._cmd.points_for_correct_return_code
            return self._cmd.deduction_for_wrong_return_code

        @property
        def return_code_points_possible(self) -> int:
            if self.return_code_correct is None:
                return 0

            return self._cmd.points_for_correct_return_code

        @property
        def stdout_correct(self) -> Optional[bool]:
            if (self._cmd.expected_stdout_source == ExpectedOutputSource.none or
                    self._fdbk.stdout_fdbk_level == ValueFeedbackLevel.no_feedback):
                return None

            return self._ag_test_command_result.stdout_correct

        @property
        def stdout(self) -> Optional[BinaryIO]:
            if (self._fdbk.show_actual_stdout or
                    self._fdbk.stdout_fdbk_level == ValueFeedbackLevel.expected_and_actual):
                return open(self._ag_test_command_result.stdout_filename, 'rb')

            return None

        @property
        def stdout_diff(self) -> Optional[core_ut.DiffResult]:
            if (self._cmd.expected_stdout_source == ExpectedOutputSource.none or
                    self._fdbk.stdout_fdbk_level != ValueFeedbackLevel.expected_and_actual):
                return None

            stdout_filename = _get_cmd_result_stdout_filename(self._ag_test_command_result)
            diff_whitespace_kwargs = {
                'ignore_blank_lines': self._cmd.ignore_blank_lines,
                'ignore_case': self._cmd.ignore_case,
                'ignore_whitespace': self._cmd.ignore_whitespace,
                'ignore_whitespace_changes': self._cmd.ignore_whitespace_changes
            }

            # check source and return diff
            if self._cmd.expected_stdout_source == ExpectedOutputSource.text:
                with tempfile.NamedTemporaryFile('w') as expected_stdout:
                    expected_stdout.write(self._cmd.expected_stdout_text)
                    expected_stdout.flush()
                    return core_ut.get_diff(expected_stdout.name, stdout_filename,
                                            **diff_whitespace_kwargs)
            elif self._cmd.expected_stdout_source == ExpectedOutputSource.instructor_file:
                return core_ut.get_diff(self._cmd.expected_stdout_instructor_file.abspath,
                                        stdout_filename,
                                        **diff_whitespace_kwargs)
            else:
                raise ValueError(
                    'Invalid expected stdout source: {}'.format(self._cmd.expected_stdout_source))

        @property
        def stdout_points(self) -> int:
            if self.stdout_correct is None:
                return 0

            if self._ag_test_command_result.stdout_correct:
                return self._cmd.points_for_correct_stdout

            return self._cmd.deduction_for_wrong_stdout

        @property
        def stdout_points_possible(self) -> int:
            if self.stdout_correct is None:
                return 0

            return self._cmd.points_for_correct_stdout

        @property
        def stderr_correct(self) -> Optional[bool]:
            if (self._cmd.expected_stderr_source == ExpectedOutputSource.none or
                    self._fdbk.stderr_fdbk_level == ValueFeedbackLevel.no_feedback):
                return None

            return self._ag_test_command_result.stderr_correct

        @property
        def stderr(self) -> Optional[BinaryIO]:
            if (self._fdbk.show_actual_stderr or
                    self._fdbk.stderr_fdbk_level == ValueFeedbackLevel.expected_and_actual):
                return open(self._ag_test_command_result.stderr_filename, 'rb')

            return None

        @property
        def stderr_diff(self) -> Optional[core_ut.DiffResult]:
            if (self._cmd.expected_stderr_source == ExpectedOutputSource.none or
                    self._fdbk.stderr_fdbk_level != ValueFeedbackLevel.expected_and_actual):
                return None

            stderr_filename = _get_cmd_result_stderr_filename(self._ag_test_command_result)
            diff_whitespace_kwargs = {
                'ignore_blank_lines': self._cmd.ignore_blank_lines,
                'ignore_case': self._cmd.ignore_case,
                'ignore_whitespace': self._cmd.ignore_whitespace,
                'ignore_whitespace_changes': self._cmd.ignore_whitespace_changes
            }

            if self._cmd.expected_stderr_source == ExpectedOutputSource.text:
                with tempfile.NamedTemporaryFile('w') as expected_stderr:
                    expected_stderr.write(self._cmd.expected_stderr_text)
                    expected_stderr.flush()
                    return core_ut.get_diff(expected_stderr.name, stderr_filename,
                                            **diff_whitespace_kwargs)
            elif self._cmd.expected_stderr_source == ExpectedOutputSource.instructor_file:
                return core_ut.get_diff(self._cmd.expected_stderr_instructor_file.abspath,
                                        stderr_filename,
                                        **diff_whitespace_kwargs)
            else:
                raise ValueError(
                    'Invalid expected stderr source: {}'.format(self._cmd.expected_stdout_source))

        @property
        def stderr_points(self) -> int:
            if self.stderr_correct is None:
                return 0

            if self._ag_test_command_result.stderr_correct:
                return self._cmd.points_for_correct_stderr

            return self._cmd.deduction_for_wrong_stderr

        @property
        def stderr_points_possible(self) -> int:
            if self.stderr_correct is None:
                return 0

            return self._cmd.points_for_correct_stderr

        @property
        def total_points(self) -> int:
            if not self._fdbk.show_points:
                return 0

            return self.return_code_points + self.stdout_points + self.stderr_points

        @property
        def total_points_possible(self) -> int:
            if not self._fdbk.show_points:
                return 0

            return (self.return_code_points_possible + self.stdout_points_possible +
                    self.stderr_points_possible)

        SERIALIZABLE_FIELDS = (
            'pk',
            'ag_test_command_pk',
            'ag_test_command_name',
            'fdbk_settings',

            'timed_out',

            'return_code_correct',
            'expected_return_code',
            'actual_return_code',
            'return_code_points',
            'return_code_points_possible',

            'stdout_correct',
            'stdout_points',
            'stdout_points_possible',

            'stderr_correct',
            'stderr_points',
            'stderr_points_possible',

            'total_points',
            'total_points_possible'
        )


def _get_cmd_result_stdout_filename(cmd_result: AGTestCommandResult):
    result_output_dir = core_ut.get_result_output_dir(
        cmd_result.ag_test_case_result.ag_test_suite_result.submission)
    return os.path.join(result_output_dir, 'cmd_result_{}_stdout'.format(cmd_result.pk))


def _get_cmd_result_stderr_filename(cmd_result: AGTestCommandResult):
    result_output_dir = core_ut.get_result_output_dir(
        cmd_result.ag_test_case_result.ag_test_suite_result.submission)
    return os.path.join(result_output_dir, 'cmd_result_{}_stderr'.format(cmd_result.pk))
