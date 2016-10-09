import difflib
import uuid

from django.core.cache import cache
from django.db import models
from django.utils import timezone

from autograder.core.models.ag_model_base import ToDictMixin

from . import feedback_config as fdbk_conf


class AutograderTestCaseResult(models.Model):
    """
    This class stores the data from an autograder test case
    and provides an interface for serializing the data.
    """
    # Using a string here instead of class to get around circular dependency
    test_case = models.ForeignKey(
        "AutograderTestCaseBase", related_name='dependent_results',
        help_text='''The test case whose results this object is storing.''')

    submission = models.ForeignKey(
        'Submission',
        related_name='results',
        help_text='''The submission the test case was run for.''')

    return_code = models.IntegerField(
        null=True, default=None,
        help_text='''The return code of the program that was tested.''')

    standard_output = models.TextField(
        help_text='''The contents of the standard output stream of the
            program that was tested.''')
    standard_error_output = models.TextField(
        help_text='''The contents of the standard error stream of the
            program that was tested.''')

    timed_out = models.BooleanField(
        default=False,
        help_text='''Whether the program exceeded the time limit.''')

    valgrind_return_code = models.IntegerField(
        null=True, default=None,
        help_text='''The return code of the program valgrind when run
            against the program being tested.''')
    valgrind_output = models.TextField(
        help_text='''The stderr contents of the program valgrind when
            run against the program being tested.''')

    # COMPILED TEST CASES ONLY

    compilation_return_code = models.IntegerField(
        null=True, default=None,
        help_text='''The return code of the command used to compile the
            program being tested.''')
    compilation_standard_output = models.TextField(
        help_text='''The contents of the standard output stream of the
            command used to compile the program being tested.''')
    compilation_standard_error_output = models.TextField(
        help_text='''The contents of the standard error stream of the
            command used to compile the program being tested.''')

    # -------------------------------------------------------------------------

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(self.submission.basic_score_cache_key)

    @property
    def basic_score(self):
        '''
        The number of points awarded for the related test case using the
        primary feedback configuration, self.test_result.feedback_config
        '''
        key = self.basic_score_cache_key
        score = cache.get(key)
        if score is not None:
            return score

        fdbk = self.get_normal_feedback()
        try:
            valgrind_val = -fdbk.valgrind_points_deducted
        except Exception:
            valgrind_val = None

        values = (fdbk.return_code_points, fdbk.stdout_points,
                  fdbk.stderr_points, fdbk.compilation_points,
                  valgrind_val)

        score = sum((val for val in values if val is not None))
        cache.set(key, score, timeout=None)
        return score

    @property
    def basic_score_cache_key(self):
        return 'result_basic_score{}'.format(self.pk)

    def get_normal_feedback(self):
        '''
        Returns a FeedbackCalculator object for this result initialized
        with self.test_case.feedback_configuration as its feedback
        config.
        '''
        return AutograderTestCaseResult.FeedbackCalculator(
            self, self.test_case.feedback_configuration)

    def get_ultimate_submission_feedback(self):
        '''
        Returns a FeedbackCalculator object for this result initialized
        with self.test_case.ultimate_submission_fdbk_conf as its
        feedback config.
        '''
        return AutograderTestCaseResult.FeedbackCalculator(
            self, self.test_case.ultimate_submission_fdbk_conf)

    def get_staff_viewer_feedback(self):
        '''
        Returns a FeedbackCalculator object for this result initialized
        with self.test_case.staff_viewer_fdbk_conf as its feedback
        config.
        '''
        return AutograderTestCaseResult.FeedbackCalculator(
            self, self.test_case.staff_viewer_fdbk_conf)

    def get_past_submission_limit_feedback(self):
        '''
        Returns a FeedbackCalculator object for this result initialized
        with self.test_case.past_submission_limit_fdbk_conf as its
        feedback config.
        '''
        return AutograderTestCaseResult.FeedbackCalculator(
            self, self.test_case.past_submission_limit_fdbk_conf)

    def get_max_feedback(self):
        '''
        Returns a FeedbackCalculator object for this result initialized
        with FeedbackConfig.create_with_max_fdbk() as its feedback
        config.
        '''
        return AutograderTestCaseResult.FeedbackCalculator(
            self, fdbk_conf.FeedbackConfig.create_with_max_fdbk())

    # TODO
    # def get_staff_viewer_ultimate_submission_feedback(self):
    #     pass

    def get_feedback(self, user_requesting_data=None, student_view=False):
        '''
        Deprecated alias for get_normal_feedback().

        Deprecated:
        Returns a FeedbackCalculator object attached to this result and
        with the given user specified to determine which feedback
        configuration to use.
        If user requesting data is None, the normal feedback
        configuration will be used.
        If student_view is True, then whether the given user is course
        staff will not be considered.

        In order for ultimate submission feedback to be given:
            - The closing time for the project must be None or have
              passed
            - The criteria described by the option selected here must
                be met for a given submission (the submission being
                viewed must actually be an ultimate submission).

        Prefer using this method over directly instantiating
        FeedbackCalculator instances.
        '''
        return AutograderTestCaseResult.FeedbackCalculator(
            self, user_requesting_data, student_view)

    class FeedbackCalculator(ToDictMixin):
        '''
        Instances of this class dynamically calculate the appropriate
        feedback data to give for an AG test result.
        '''

        def __init__(self, result, fdbk_conf):
            '''
            Initializes the object with the given result and optionally
            a FeedbackConfig object ot use.
            '''
            self._fdbk = fdbk_conf
            self._result = result

        _DEFAULT_TO_DICT_FIELDS = frozenset([
            'ag_test_name',

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
        ])

        @classmethod
        def get_default_to_dict_fields(class_):
            return class_._DEFAULT_TO_DICT_FIELDS

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
        def ag_test_name(self):
            random = fdbk_conf.AGTestNameFdbkLevel.randomly_obfuscate_name
            if self._fdbk.ag_test_name_fdbk == random:
                return 'test{}'.format(uuid.uuid4().hex)

            deterministic = (
                fdbk_conf.AGTestNameFdbkLevel.deterministically_obfuscate_name)
            if self._fdbk.ag_test_name_fdbk == deterministic:
                return 'test{}'.format(self._result.test_case.pk)

            return self._result.test_case.name

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

            return (self._result.standard_output ==
                    self._result.test_case.expected_standard_output)

        @property
        def stdout_content(self):
            if not self._fdbk.show_stdout_content:
                return None

            return self._result.standard_output

        @property
        def stdout_diff(self):
            if not self._show_stdout_diff() or not self._stdout_checked():
                return None

            if self.stdout_correct:
                return ''

            return _get_diff(self._result.test_case.expected_standard_output,
                             self._result.standard_output)

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

            return (self._result.standard_error_output ==
                    self._result.test_case.expected_standard_error_output)

        @property
        def stderr_content(self):
            if not self._fdbk.show_stderr_content:
                return None

            return self._result.standard_error_output

        @property
        def stderr_diff(self):
            if not self._stderr_checked() or not self._show_stderr_diff():
                return None

            if self.stderr_correct:
                return ''

            return _get_diff(
                self._result.test_case.expected_standard_error_output,
                self._result.standard_error_output)

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

        @property
        def compilation_succeeded(self):
            if (self._no_compiler_fdbk() or
                    not self._result.test_case.checks_compilation()):
                return None

            return self._result.compilation_return_code == 0

        @property
        def compilation_stdout(self):
            if (not self._show_compiler_output() or
                    not self._result.test_case.checks_compilation()):
                return None

            return self._result.compilation_standard_output

        @property
        def compilation_stderr(self):
            if (not self._show_compiler_output() or
                    not self._result.test_case.checks_compilation()):
                return None

            return self._result.compilation_standard_error_output

        @property
        def compilation_points(self):
            points_possible = self.compilation_points_possible
            if points_possible is None:
                return None

            return 0 if not self.compilation_succeeded else points_possible

        @property
        def compilation_points_possible(self):
            if (self._no_compiler_fdbk() or
                    self._no_pts_fdbk() or
                    not self._result.test_case.checks_compilation()):
                return None

            return self._result.test_case.points_for_compilation_success

        def _no_compiler_fdbk(self):
            return (self._fdbk.compilation_fdbk ==
                    fdbk_conf.CompilationFdbkLevel.no_feedback)

        def _show_compiler_output(self):
            return (self._fdbk.compilation_fdbk ==
                    fdbk_conf.CompilationFdbkLevel.show_compiler_output)

        # ---------------------------------------------------------------------

        @property
        def valgrind_errors_reported(self):
            if (self._no_valgrind_fdbk() or
                    not self._result.test_case.use_valgrind):
                return None

            return self._result.valgrind_return_code != 0

        @property
        def valgrind_output(self):
            if (not self._show_valgrind_output() or
                    not self._result.test_case.use_valgrind):
                return None

            return self._result.valgrind_output

        @property
        def valgrind_points_deducted(self):
            if (self._no_valgrind_fdbk() or
                    self._no_pts_fdbk() or
                    not self._result.test_case.use_valgrind):
                return None

            return (0 if not self.valgrind_errors_reported
                    else self._result.test_case.deduction_for_valgrind_errors)

        def _no_valgrind_fdbk(self):
            return (self._fdbk.valgrind_fdbk ==
                    fdbk_conf.ValgrindFdbkLevel.no_feedback)

        def _show_valgrind_output(self):
            return (self._fdbk.valgrind_fdbk ==
                    fdbk_conf.ValgrindFdbkLevel.show_valgrind_output)

        # ---------------------------------------------------------------------

        def _no_pts_fdbk(self):
            return self._fdbk.points_fdbk == fdbk_conf.PointsFdbkLevel.hide

# -----------------------------------------------------------------------------

_DIFFER = difflib.Differ()


def _get_diff(first, second):
    return list(_DIFFER.compare(
        first.splitlines(keepends=True), second.splitlines(keepends=True)))
