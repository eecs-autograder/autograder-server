from typing import List

from django.db import models

from autograder.core.models.ag_model_base import ToDictMixin
import autograder.core.constants as constants
import autograder.core.utils as core_ut

from ..ag_model_base import AutograderModel
from .ag_test_command import (
    AGTestCommand, AGTestCommandFeedbackConfig, ExpectedReturnCode, ValueFeedbackLevel,
    ExpectedOutputSource)
from .ag_test_case_result import AGTestCaseResult


class AGTestCommandResult(AutograderModel):
    """
    This class stores the data from an AGTestCommand
    and provides an interface for serializing the data with different
    feedback levels.
    """
    class Meta:
        unique_together = ('ag_test_command', 'ag_test_case_result')

    ag_test_command = models.ForeignKey(
        AGTestCommand, help_text='The AGTestCommand this result belongs to.')

    ag_test_case_result = models.ForeignKey(
        AGTestCaseResult, blank=True, null=True, default=None,
        help_text='''The AGTestCaseResult that this result belongs to.
                     A value of None indicates that this AGTestCommandResult
                     is the result of an AGTestSuite's setup command.''')

    return_code = models.IntegerField(help_text='The return code of the completed command.')

    stdout = models.TextField(
        blank=True, help_text='The stdout contents from running the command.')
    stderr = models.TextField(
        blank=True, help_text='The stderr contents from running the command.')

    timed_out = models.BooleanField(
        blank=True, default=False, help_text='Whether the program exceeded the time limit.')

    return_code_correct = models.NullBooleanField(null=True, default=None)
    stdout_correct = models.NullBooleanField(null=True, default=None)
    stderr_correct = models.NullBooleanField(null=True, default=None)

    def save(self, *args, **kwargs):
        self._check_len_and_truncate('stdout')
        self._check_len_and_truncate('stderr')

        super().save(*args, **kwargs)

    def _check_len_and_truncate(self, field_name):
        value = getattr(self, field_name)
        if len(value) > constants.MAX_OUTPUT_LENGTH:
            setattr(self, field_name,
                    value[:constants.MAX_OUTPUT_LENGTH] + '\nOutput truncated')

    def get_normal_feedback(self) -> 'AGTestCommandResult.FeedbackCalculator':
        """
        Returns a FeedbackCalculator object for this result initialized
        with self.ag_test_command.normal_fdbk_config as its feedback
        config.
        """
        return AGTestCommandResult.FeedbackCalculator(
            self, self.ag_test_command.normal_fdbk_config)

    def get_ultimate_submission_feedback(self) -> 'AGTestCommandResult.FeedbackCalculator':
        """
        Returns a FeedbackCalculator object for this result initialized
        with self.ag_test_command.ultimate_submission_fdbk_config as its
        feedback config.
        """
        return AGTestCommandResult.FeedbackCalculator(
            self, self.ag_test_command.ultimate_submission_fdbk_config)

    def get_staff_viewer_feedback(self) -> 'AGTestCommandResult.FeedbackCalculator':
        """
        Returns a FeedbackCalculator object for this result initialized
        with self.ag_test_command.staff_viewer_fdbk_config as its feedback
        config.
        """
        return AGTestCommandResult.FeedbackCalculator(
            self, self.ag_test_command.staff_viewer_fdbk_config)

    def get_past_submission_limit_feedback(self) -> 'AGTestCommandResult.FeedbackCalculator':
        """
        Returns a FeedbackCalculator object for this result initialized
        with self.ag_test_command.past_limit_submission_fdbk_config as its
        feedback config.
        """
        return AGTestCommandResult.FeedbackCalculator(
            self, self.ag_test_command.past_limit_submission_fdbk_config)

    def get_max_feedback(self) -> 'AGTestCommandResult.FeedbackCalculator':
        """
        Returns a FeedbackCalculator object for this result initialized
        with maximum feedback settings.
        """
        fdbk_settings = AGTestCommandFeedbackConfig(
            return_code_fdbk_level=ValueFeedbackLevel.get_max(),
            stdout_fdbk_level=ValueFeedbackLevel.get_max(),
            stderr_fdbk_level=ValueFeedbackLevel.get_max(),
            show_points=True,
            show_actual_return_code=True,
            show_actual_stdout=True,
            show_actual_stderr=True)

        return AGTestCommandResult.FeedbackCalculator(self, fdbk_settings)

    class FeedbackCalculator(ToDictMixin):
        """
        Instances of this class dynamically calculate the appropriate
        feedback data to give for an AGTestCommandResult.
        """

        def __init__(self, result: 'AGTestCommandResult',
                     fdbk_conf: 'AGTestCommandFeedbackConfig'):
            self._fdbk = fdbk_conf
            self._result = result
            self._cmd = self._result.ag_test_command

        @property
        def fdbk_conf(self):
            """
            Returns the FeedbackConfig object that this object was
            initialized with.
            """
            return self._fdbk

        @property
        def pk(self):
            return self._result.pk

        @property
        def ag_test_command_name(self):
            return self._cmd.name

        @property
        def ag_test_command_pk(self):
            return self._cmd.pk

        @property
        def fdbk_settings(self) -> dict:
            return self.fdbk_conf.to_dict()

        @property
        def timed_out(self):
            return self._result.timed_out if self._fdbk.show_whether_timed_out else None

        @property
        def return_code_correct(self):
            if (self._cmd.expected_return_code == ExpectedReturnCode.none or
                    self._fdbk.return_code_fdbk_level == ValueFeedbackLevel.no_feedback):
                return None

            return self._result.return_code_correct

        @property
        def expected_return_code(self):
            if self._fdbk.return_code_fdbk_level != ValueFeedbackLevel.expected_and_actual:
                return None

            return self._cmd.expected_return_code

        @property
        def actual_return_code(self):
            if (self._fdbk.show_actual_return_code or
                    self._fdbk.return_code_fdbk_level == ValueFeedbackLevel.expected_and_actual):
                return self._result.return_code

            return None

        @property
        def return_code_points(self):
            if self.return_code_correct is None:
                return 0

            return (self._cmd.points_for_correct_return_code if self._result.return_code_correct
                    else self._cmd.deduction_for_wrong_return_code)

        @property
        def return_code_points_possible(self):
            if self.return_code_correct is None:
                return 0

            return self._cmd.points_for_correct_return_code

        @property
        def stdout_correct(self):
            if (self._cmd.expected_stdout_source == ExpectedOutputSource.none or
                    self._fdbk.stdout_fdbk_level == ValueFeedbackLevel.no_feedback):
                return None

            return self._result.stdout_correct

        @property
        def stdout(self):
            if (self._fdbk.show_actual_stdout or
                    self._fdbk.stdout_fdbk_level == ValueFeedbackLevel.expected_and_actual):
                return self._result.stdout

            return None

        @property
        def stdout_diff(self):
            if (self._cmd.expected_stdout_source == ExpectedOutputSource.none or
                    self._fdbk.stdout_fdbk_level != ValueFeedbackLevel.expected_and_actual):
                return None

            # check source and return diff
            if self._cmd.expected_stdout_source == ExpectedOutputSource.text:
                expected_stdout = self._cmd.expected_stdout_text
            elif self._cmd.expected_stdout_source == ExpectedOutputSource.project_file:
                with self._cmd.expected_stdout_project_file.open() as f:
                    expected_stdout = f.read()
            else:
                raise ValueError(
                    'Invalid expected stdout source: {}'.format(self._cmd.expected_stdout_source))

            return core_ut.get_diff(expected_stdout, self._result.stdout,
                                    ignore_blank_lines=self._cmd.ignore_blank_lines,
                                    ignore_case=self._cmd.ignore_case,
                                    ignore_whitespace=self._cmd.ignore_whitespace,
                                    ignore_whitespace_changes=self._cmd.ignore_whitespace_changes)

        @property
        def stdout_points(self):
            if self.stdout_correct is None:
                return 0

            return (self._cmd.points_for_correct_stdout if self._result.stdout_correct
                    else self._cmd.deduction_for_wrong_stdout)

        @property
        def stdout_points_possible(self):
            if self.stdout_correct is None:
                return 0

            return self._cmd.points_for_correct_stdout

        @property
        def stderr_correct(self):
            if (self._cmd.expected_stderr_source == ExpectedOutputSource.none or
                    self._fdbk.stderr_fdbk_level == ValueFeedbackLevel.no_feedback):
                return None

            return self._result.stderr_correct

        @property
        def stderr(self):
            if (self._fdbk.show_actual_stderr or
                    self._fdbk.stderr_fdbk_level == ValueFeedbackLevel.expected_and_actual):
                return self._result.stderr

            return None

        @property
        def stderr_diff(self):
            if (self._cmd.expected_stderr_source == ExpectedOutputSource.none or
                    self._fdbk.stderr_fdbk_level != ValueFeedbackLevel.expected_and_actual):
                return None

            if self._cmd.expected_stderr_source == ExpectedOutputSource.text:
                expected_stderr = self._cmd.expected_stderr_text
            elif self._cmd.expected_stderr_source == ExpectedOutputSource.project_file:
                with self._cmd.expected_stderr_project_file.open() as f:
                    expected_stderr = f.read()
            else:
                raise ValueError(
                    'Invalid expected stderr source: {}'.format(self._cmd.expected_stdout_source))

            return core_ut.get_diff(expected_stderr, self._result.stderr,
                                    ignore_blank_lines=self._cmd.ignore_blank_lines,
                                    ignore_case=self._cmd.ignore_case,
                                    ignore_whitespace=self._cmd.ignore_whitespace,
                                    ignore_whitespace_changes=self._cmd.ignore_whitespace_changes)

        @property
        def stderr_points(self):
            if self.stderr_correct is None:
                return 0

            return (self._cmd.points_for_correct_stderr if self._result.stderr_correct
                    else self._cmd.deduction_for_wrong_stderr)

        @property
        def stderr_points_possible(self):
            if self.stderr_correct is None:
                return 0

            return self._cmd.points_for_correct_stderr

        @property
        def total_points(self):
            if not self._fdbk.show_points:
                return 0

            return self.return_code_points + self.stdout_points + self.stderr_points

        @property
        def total_points_possible(self):
            if not self._fdbk.show_points:
                return 0

            return (self.return_code_points_possible + self.stdout_points_possible +
                    self.stderr_points_possible)

        SERIALIZABLE_FIELDS = (
            'ag_test_case_command_pk',
            'ag_test_case_command_name',
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
