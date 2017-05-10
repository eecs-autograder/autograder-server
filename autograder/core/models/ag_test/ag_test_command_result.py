from typing import List

from django.db import models

from autograder.core.models.ag_model_base import ToDictMixin
import autograder.core.constants as constants
import autograder.core.utils as core_ut

from ..ag_model_base import AutograderModel
from .ag_test_suite import AGTestSuite
from .ag_test_command import AGTestCommand, AGTestCommandFeedbackConfig, ExpectedReturnCode, ValueFeedbackLevel


class AGTestCommandResult(AutograderModel):
    """
    This class stores the data from an AGTestCommand
    and provides an interface for serializing the data with different
    feedback levels.
    """
    class Meta:
        unique_together = ('ag_test_command',)

    ag_test_command = models.ForeignKey(
        AGTestCommand, help_text='The AGTestCommand this result belongs to.')

    return_code = models.IntegerField(help_text='The return code of the completed command.')

    stdout = models.TextField(help_text='The stdout contents from running the command.')
    sterr = models.TextField(help_text='The stderr contents from running the command.')

    timed_out = models.BooleanField(help_text='Whether the program exceeded the time limit.')

    stdout_diff = models.TextField(
        help_text='''If the AGTestCommand this result belongs to checks stdout,
                     this field will store a diff of the expected and actual stdout contents.''')

    stderr_diff = models.TextField(
        help_text='''If the AGTestCommand this result belongs to checks stderr,
                     this field will store a diff of the expected and actual stderr contents.''')

    return_code_correct = models.BooleanField(null=True, default=None)
    stdout_correct = models.BooleanField(null=True, default=None)
    stderr_correct = models.BooleanField(null=True, default=None)

    def save(self, *args, **kwargs):
        self._check_len_and_truncate('standard_output')
        self._check_len_and_truncate('standard_error_output')
        self._check_len_and_truncate('valgrind_output')
        self._check_len_and_truncate('compilation_standard_output')
        self._check_len_and_truncate('compilation_standard_error_output')

        super().save(*args, **kwargs)

    def _check_len_and_truncate(self, field_name):
        value = getattr(self, field_name)
        if len(value) > constants.MAX_OUTPUT_LENGTH:
            setattr(self, field_name,
                    value[:constants.MAX_OUTPUT_LENGTH] + '\nOutput truncated')

    def get_normal_feedback(self):
        '''
        Returns a FeedbackCalculator object for this result initialized
        with self.ag_test_command.normal_fdbk_config as its feedback
        config.
        '''
        return AGTestCommandResult.FeedbackCalculator(
            self, self.ag_test_command.normal_fdbk_config)

    def get_ultimate_submission_feedback(self):
        '''
        Returns a FeedbackCalculator object for this result initialized
        with self.ag_test_command.ultimate_submission_fdbk_config as its
        feedback config.
        '''
        return AGTestCommandResult.FeedbackCalculator(
            self, self.ag_test_command.ultimate_submission_fdbk_config)

    def get_staff_viewer_feedback(self):
        '''
        Returns a FeedbackCalculator object for this result initialized
        with self.ag_test_command.staff_viewer_fdbk_config as its feedback
        config.
        '''
        return AGTestCommandResult.FeedbackCalculator(
            self, self.ag_test_command.staff_viewer_fdbk_config)

    def get_past_submission_limit_feedback(self):
        '''
        Returns a FeedbackCalculator object for this result initialized
        with self.ag_test_command.past_limit_submission_fdbk_config as its
        feedback config.
        '''
        return AGTestCommandResult.FeedbackCalculator(
            self, self.ag_test_command.past_limit_submission_fdbk_config)

    def get_max_feedback(self):
        '''
        Returns a FeedbackCalculator object for this result initialized
        with maximum feedback settings.
        '''
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

        def __init__(self, result, fdbk_conf):
            '''
            Initializes the object with the given result and feedback settings.
            '''
            self._fdbk = fdbk_conf
            self._result = result

            self._stdout_diff = None  # type: List
            self._stderr_diff = None  # type: List

        SERIALIZABLE_FIELDS = (
            'ag_test_name',
            'status',

            'timed_out',

            'return_code_correct',
            'expected_return_code',
            'actual_return_code',
            'return_code_points',
            'return_code_points_possible',

            'stdout_correct',
            'stdout_content',
            'stdout_diff',
            'stdout_points',
            'stdout_points_possible',

            'stderr_correct',
            'stderr_content',
            'stderr_diff',
            'stderr_points',
            'stderr_points_possible',

            'compilation_succeeded',
            'compilation_stdout',
            'compilation_stderr',
            'compilation_points',
            'compilation_points_possible',

            'valgrind_errors_reported',
            'valgrind_output',
            'valgrind_points_deducted',

            'total_points',
            'total_points_possible'
        )

        @property
        def fdbk_conf(self):
            '''
            Returns the FeedbackConfig object that this object was
            initialized with.
            '''
            return self._fdbk

        @property
        def pk(self):
            return self._result.pk

        @property
        def status(self):
            return self._result.status

        @property
        def ag_test_name(self):
            random = fdbk_conf.AGTestNameFdbkLevel.randomly_obfuscate_name
            if self._fdbk.ag_test_name_fdbk == random:
                return '{} {} (name randomly obfuscated)'.format(
                    self._result.test_case.randomly_obfuscated_name_prefix,
                    uuid.uuid4().hex)

            deterministic = (
                fdbk_conf.AGTestNameFdbkLevel.deterministically_obfuscate_name)
            if self._fdbk.ag_test_name_fdbk == deterministic:
                return 'test{}'.format(self._result.test_case.pk)

            return self._result.test_case.name

        @property
        def timed_out(self):
            '''
            Note: feedback on whether the test case timed out is given
            only if feedback would be given on return code correctness,
            stdout correctness, or stderr correctness.
            '''
            if (self.return_code_correct is not None or
                    self.stdout_correct is not None or
                    self.stderr_correct is not None):
                return self._result.timed_out

            return None

        @property
        def return_code_correct(self):
            if (not self._ret_code_checked() or
                    self._no_ret_code_correctness_fdbk()):
                return None

            if self._result.test_case.expect_any_nonzero_return_code:
                return self._result.return_code != 0

            return (self._result.return_code ==
                    self._result.test_case.expected_return_code)

        @property
        def expected_return_code(self):
            if not self._ret_code_checked() or not self._show_ret_code_diff():
                return None

            return self._result.test_case.expected_return_code

        @property
        def actual_return_code(self):
            if self._fdbk.show_return_code:
                return self._result.return_code

            if not self._ret_code_checked() or not self._show_ret_code_diff():
                return None

            return self._result.return_code

        def _show_ret_code_diff(self):
            return (
                self._fdbk.return_code_fdbk ==
                fdbk_conf.ReturnCodeFdbkLevel.show_expected_and_actual_values)

        @property
        def return_code_points(self):
            possible = self.return_code_points_possible
            if possible is None:
                return None

            return 0 if not self.return_code_correct else possible

        @property
        def return_code_points_possible(self):
            if (not self._ret_code_checked() or
                    self._no_ret_code_correctness_fdbk() or
                    self._no_pts_fdbk()):
                return None

            return self._result.test_case.points_for_correct_return_code

        def _no_ret_code_correctness_fdbk(self):
            return (self._fdbk.return_code_fdbk ==
                    fdbk_conf.ReturnCodeFdbkLevel.no_feedback)

        def _ret_code_checked(self):
            return (self._result.test_case.expected_return_code is not None or
                    self._result.test_case.expect_any_nonzero_return_code)

        # ---------------------------------------------------------------------

        @property
        def stdout_correct(self):
            if (self._no_stdout_correctness_fdbk() or
                    not self._stdout_checked()):
                return None

            return self._get_stdout_diff() == []

        @property
        def stdout_content(self):
            if not self._fdbk.show_stdout_content:
                return None

            return self._result.standard_output

        @property
        def stdout_diff(self):
            if not self._show_stdout_diff() or not self._stdout_checked():
                return None

            return self._get_stdout_diff()

        @property
        def stdout_points(self):
            possible = self.stdout_points_possible
            if possible is None:
                return None

            return 0 if not self.stdout_correct else possible

        @property
        def stdout_points_possible(self):
            if (not self._stdout_checked() or
                    self._no_stdout_correctness_fdbk() or
                    self._no_pts_fdbk()):
                return None

            return self._result.test_case.points_for_correct_stdout

        def _no_stdout_correctness_fdbk(self):
            return (self._fdbk.stdout_fdbk ==
                    fdbk_conf.StdoutFdbkLevel.no_feedback)

        def _show_stdout_diff(self):
            return (self._fdbk.stdout_fdbk ==
                    fdbk_conf.StdoutFdbkLevel.show_expected_and_actual_values)

        def _stdout_checked(self):
            return self._result.test_case.expected_standard_output

        # ---------------------------------------------------------------------

        @property
        def stderr_correct(self):
            if (self._no_stderr_correctness_fdbk() or
                    not self._stderr_checked()):
                return None

            return self._get_stderr_diff() == []

        @property
        def stderr_content(self):
            if not self._fdbk.show_stderr_content:
                return None

            return self._result.standard_error_output

        @property
        def stderr_diff(self):
            if not self._stderr_checked() or not self._show_stderr_diff():
                return None

            return self._get_stderr_diff()

        @property
        def stderr_points(self):
            possible = self.stderr_points_possible
            if possible is None:
                return None

            return 0 if not self.stderr_correct else possible

        @property
        def stderr_points_possible(self):
            if (not self._stderr_checked() or
                    self._no_stderr_correctness_fdbk() or
                    self._no_pts_fdbk()):
                return None

            return self._result.test_case.points_for_correct_stderr

        def _no_stderr_correctness_fdbk(self):
            return (self._fdbk.stderr_fdbk ==
                    fdbk_conf.StderrFdbkLevel.no_feedback)

        def _show_stderr_diff(self):
            return (self._fdbk.stderr_fdbk ==
                    fdbk_conf.StderrFdbkLevel.show_expected_and_actual_values)

        def _stderr_checked(self):
            return self._result.test_case.expected_standard_error_output

        # ---------------------------------------------------------------------

        def _no_pts_fdbk(self):
            return self._fdbk.points_fdbk == fdbk_conf.PointsFdbkLevel.hide

        # ---------------------------------------------------------------------

        @property
        def total_points(self):
            try:
                valgrind_val = -self.valgrind_points_deducted
            except Exception:
                valgrind_val = None

            values = (self.return_code_points, self.stdout_points,
                      self.stderr_points)

            return max(0, sum((val for val in values if val is not None)))

        @property
        def total_points_possible(self):
            values = (self.return_code_points_possible, self.stdout_points_possible,
                      self.stderr_points_possible)
            return sum((val for val in values if val is not None))
