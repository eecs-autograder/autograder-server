import difflib

from django.utils import timezone
from django.db import models

import autograder.core.shared.feedback_configuration as fbc


# TODO: "feedback" classes (i.e. CompilationFeedback, ReturnCodeFeedback, OutputFeedback)
# TODO: "feedback generator" class, ctor takes in feedback level override, pulls from
#       test case by default
# TODO: refactor into class hierarchy that mirrors that of autograder test case?
# TODO: test cases that involve interpreted test cases


class AutograderTestCaseResult(models.Model):
    """
    This class stores the data from an autograder test case
    and provides an interface for serializing the data.

    Fields:
        test_case -- The test case whose results this object is storing.
            This field is REQUIRED.

        submission -- The submission the test case was run for.
            This field can be None.

        return_code -- The return code of the program that was tested.
            Default value: None

        standard_output -- The contents of the standard output stream
            of the program that was tested.
            Default value: empty string

        standard_error_output -- The contents of the standard error stream
            of the program that was tested.
            Default value: empty string

        time_elapsed -- TODO The amount of time it took to run the program
            being tested.

        timed_out -- Whether the program exceeded the time limit.

        valgrind_return_code -- The return code of the program valgrind
            when run against the program being tested.
            Default value: None

        valgrind_output -- The output (standard out and standard error)
            of the program valgrind when run against the program being
            tested.
            Default value: empty string

    Compilation-related fields:
        compilation_return_code -- The return code of the command used
            to compile the program being tested.
            Default value: None

        compilation_standard_output -- The contents of the standard output
            stream of the command used to compile the program being tested.
            Default value: empty string

        compilation_standard_error_output -- The contents of the standard error
            stream of the command used to compile the program being tested.
            Default value: empty string

    Properties:
        return_code_correct -- Whether the program
            exited with the correct return code.

        standard_output_correct -- Whether the program produced the
            correct standard output.

        standard_error_output_correct -- Whether the program produced the
            correct standard error output.

        output_correct -- Whether the program produced the correct
            standard and error output.

        valgrind_errors_present -- Whether valgrind exited with nonzero
            status.

        compilation_succeeded -- Whether the program was compiled successfully.

    Instance methods:
        TODO: getter functions that return points for various things,
                have them take in a feedback configuration

        to_json()
    """
    # Using a string here instead of class to get around circular dependency
    test_case = models.ForeignKey("AutograderTestCaseBase")

    submission = models.ForeignKey(
        'Submission', related_name='results',
        null=True, blank=True, default=None)

    @property
    def return_code_correct(self):
        if self.test_case.expect_any_nonzero_return_code:
            return self.return_code != 0

        return self.return_code == self.test_case.expected_return_code

    @property
    def standard_output_correct(self):
        return (
            not self.test_case.expected_standard_output or
            self.standard_output == self.test_case.expected_standard_output)

    @property
    def standard_error_output_correct(self):
        return (
            not self.test_case.expected_standard_error_output or
            (self.standard_error_output ==
                self.test_case.expected_standard_error_output))

    @property
    def output_correct(self):
        return (self.standard_output_correct and
                self.standard_error_output_correct)

    @property
    def valgrind_errors_present(self):
        return self.valgrind_return_code != 0

    @property
    def compilation_succeeded(self):
        return self.compilation_return_code == 0

    return_code = models.IntegerField(null=True, default=None)
    standard_output = models.TextField()
    standard_error_output = models.TextField()
    timed_out = models.BooleanField(default=False)
    # _time_elapsed = models.IntegerField(null=True, default=None)
    valgrind_return_code = models.IntegerField(null=True, default=None)
    valgrind_output = models.TextField()

    compilation_return_code = models.IntegerField(null=True, default=None)
    compilation_standard_output = models.TextField()
    compilation_standard_error_output = models.TextField()

    def total_points_as_dict(self, feedback_config_override=None,
                             max_feedback=False):
        if max_feedback:
            fb = fbc.AutograderTestCaseFeedbackConfiguration.get_max_feedback()
        else:
            fb = self._determine_feedback_config(feedback_config_override)

        data = self.to_json(override_feedback=fb)
        result = {}

        if 'total_points_possible' in data and 'total_points_awarded' in data:
            result['points_possible'] = data['total_points_possible']
            result['points_awarded'] = data['total_points_awarded']
        return result

    def to_json(self, override_feedback=None):
        """
        Returns a JSON representation of this autograder test case result
        of the following form:
        {
            'test_name': <name>,

            //** NOTE: Some or all of the following may be ommitted **//
            //** depending on the feedback level.                   **//

            'return_code_correct': <True | False>,
            'expected_return_code': <value>,
            'actual_return_code': <value>,


            'output_correct': <True | False>,
            # At most one of stdout_diff or standard_output will be present
            # depending on the feedback level and how the test case
            # evaluates correctness.
            # Similarly for stderr_diff and standard_error_output
            'stdout_diff': <diff>, | 'standard_output': <output>,
            'stderr_diff': <diff>, | 'standard_error_output': <output>,


            'valgrind_errors_present': <True | False>,
            'valgrind_output': <output>,


            'compilation_succeeded': <True | False>,
            'compilation_stdout': <value>,
            'compilation_stderr': <value>,


            'return_code_points_awarded': <points awarded>,
            'return_code_points_possible': <points possible>,

            'output_points_awarded': <points awarded>,
            'output_points_possible': <points possible>,

            'valgrind_points_awarded': <points awarded>,
            'valgrind_points_possible': <points possible>,

            'compilation_points_awarded': <points awarded>,
            'compilation_points_possible': <points possible>,

            'total_points_awarded': <total points awarded>,
            'total_points_possible': <points possible>,


            'timed_out': <True | False>
        }
        """
        feedback_configuration = self._determine_feedback_config(
            override_feedback)

        show_points_breakdown = (
            (feedback_configuration.points_feedback_level ==
                fbc.PointsFeedbackLevel.show_breakdown))
        result = {'test_name': self.test_case.name}

        pts_data = {}

        feedback, pts_awarded = self._get_compilation_feedback(
            feedback_configuration, show_points_breakdown)
        result.update(feedback)
        pts_data['compilation_points_awarded'] = pts_awarded

        if self.test_case.test_checks_compilation():
            if self.compilation_succeeded:
                result['timed_out'] = self.timed_out
        else:
            result['timed_out'] = self.timed_out

        if ((self.test_case.test_checks_compilation() and
                not self.compilation_succeeded) or self.timed_out):
            # print('compilation_succeeded: ', self.compilation_succeeded)
            # print('timed_out')
            result.update(self._get_points_feedback(
                feedback_configuration, show_points_breakdown,
                **pts_data))
            return result

        feedback, pts_awarded = self._get_return_code_feedback(
            feedback_configuration, show_points_breakdown)
        result.update(feedback)
        pts_data['return_code_points_awarded'] = pts_awarded

        feedback, pts_awarded = self._get_output_feedback(
            feedback_configuration, show_points_breakdown)
        result.update(feedback)
        pts_data['output_points_awarded'] = pts_awarded

        feedback, pts_deducted = self._get_valgrind_feedback(
            feedback_configuration, show_points_breakdown)
        result.update(feedback)
        pts_data['valgrind_points_deducted'] = pts_deducted

        points_feedback = self._get_points_feedback(
            feedback_configuration, show_points_breakdown, **pts_data)
        result.update(points_feedback)

        return result

    def _determine_feedback_config(self, feedback_config_override):
        if feedback_config_override is not None:
            return feedback_config_override

        if (self.test_case.
                post_deadline_final_submission_feedback_configuration) is None:
            return self.test_case.feedback_configuration

        if self.submission is None:
            return self.test_case.feedback_configuration

        if self.test_case.project.closing_time is None:
            return self.test_case.feedback_configuration

        is_final_submission = (
            self.submission ==
            self.submission.submission_group.submissions.first())

        if not is_final_submission:
            return self.test_case.feedback_configuration

        deadline_extension = self.submission.submission_group.extended_due_date
        project_deadline = (
            deadline_extension if deadline_extension is not None else
            self.test_case.project.closing_time)

        if timezone.now() > project_deadline:
            return (self.test_case.
                    post_deadline_final_submission_feedback_configuration)

        return self.test_case.feedback_configuration

    def _get_compilation_feedback(self, feedback_config,
                                  show_points_breakdown):
        result = {}
        if not self._give_compilation_feedback(feedback_config):
            return result, 0

        result['compilation_succeeded'] = self.compilation_succeeded

        show_compiler_output = (
            (feedback_config.compilation_feedback_level ==
                fbc.CompilationFeedbackLevel.show_compiler_output))
        if show_compiler_output:
            result['compilation_stdout'] = self.compilation_standard_output
            result['compilation_stderr'] = (
                self.compilation_standard_error_output)

        points_possible = self.test_case.points_for_compilation_success
        points_awarded = points_possible if self.compilation_succeeded else 0

        return result, points_awarded

    def _get_return_code_feedback(self, feedback_config,
                                  show_points_breakdown):
        result = {}
        if not self._give_return_code_feedback(feedback_config):
            return result, 0

        result['return_code_correct'] = self.return_code_correct

        show_return_code_diff = (
            (feedback_config.return_code_feedback_level ==
                fbc.ReturnCodeFeedbackLevel.show_expected_and_actual_values))

        if show_return_code_diff:
            result['expected_return_code'] = (
                self.test_case.expected_return_code)
            result['actual_return_code'] = self.return_code

        points_possible = self.test_case.points_for_correct_return_code
        points_awarded = points_possible if self.return_code_correct else 0

        return result, points_awarded

    def _get_output_feedback(self, feedback_config, show_points_breakdown):
        result = {}

        show_program_output = (
            (feedback_config.output_feedback_level ==
                fbc.OutputFeedbackLevel.show_program_output) or
            (feedback_config.output_feedback_level ==
                fbc.OutputFeedbackLevel.show_expected_and_actual_values and
                not self.test_case.test_checks_output()))

        if show_program_output:
            result['standard_output'] = self.standard_output
            result['standard_error_output'] = self.standard_error_output

        if not self._give_output_correctness_feedback(feedback_config):
            return result, 0

        result['output_correct'] = self.output_correct

        show_output_diff = (
            (feedback_config.output_feedback_level ==
                fbc.OutputFeedbackLevel.show_expected_and_actual_values))
        # print("show output diff?: ", show_output_diff)
        if show_output_diff:
            result['stdout_diff'] = _get_diff(
                self.test_case.expected_standard_output,
                self.standard_output)
            result['stderr_diff'] = _get_diff(
                self.test_case.expected_standard_error_output,
                self.standard_error_output)

        points_possible = self.test_case.points_for_correct_output
        points_awarded = points_possible if self.output_correct else 0

        return result, points_awarded

    def _get_valgrind_feedback(self, feedback_config, show_points_breakdown):
        result = {}
        if not self._give_valgrind_feedback(feedback_config):
            return result, 0

        result['valgrind_errors_present'] = self.valgrind_errors_present

        if (feedback_config.valgrind_feedback_level ==
                fbc.ValgrindFeedbackLevel.show_valgrind_output):
            result['valgrind_output'] = self.valgrind_output

        points_deducted = self.test_case.deduction_for_valgrind_errors
        points_deducted = (
            points_deducted if self.valgrind_errors_present else 0)

        return result, points_deducted

    def _get_points_feedback(self, feedback_config, show_points_breakdown,
                             compilation_points_awarded=0,
                             return_code_points_awarded=0,
                             output_points_awarded=0,
                             valgrind_points_deducted=0):
        result = {}
        if (feedback_config.points_feedback_level ==
                fbc.PointsFeedbackLevel.hide):
            return result

        compilation_points_possible = (
            self.test_case.points_for_compilation_success)
        return_code_points_possible = (
            self.test_case.points_for_correct_return_code)
        output_points_possible = self.test_case.points_for_correct_output
        valgrind_possible_deduction = (
            self.test_case.deduction_for_valgrind_errors)

        total_possible = 0
        total_awarded = (
            compilation_points_awarded +
            max(return_code_points_awarded +
                output_points_awarded -
                valgrind_points_deducted, 0))

        breakdown = {}
        if (self._give_compilation_feedback(feedback_config) and
                compilation_points_possible):
            breakdown['compilation_points_awarded'] = (
                compilation_points_awarded)
            breakdown['compilation_points_possible'] = (
                compilation_points_possible)
            total_possible += compilation_points_possible

        if (self._give_return_code_feedback(feedback_config) and
                return_code_points_possible):
            breakdown['return_code_points_awarded'] = (
                return_code_points_awarded)
            breakdown['return_code_points_possible'] = (
                return_code_points_possible)
            total_possible += return_code_points_possible

        if (self._give_output_correctness_feedback(feedback_config) and
                output_points_possible):
            breakdown['output_points_awarded'] = output_points_awarded
            breakdown['output_points_possible'] = output_points_possible
            total_possible += output_points_possible

        if (self._give_valgrind_feedback(feedback_config) and
                valgrind_possible_deduction):
            breakdown['valgrind_points_deducted'] = valgrind_points_deducted

        if show_points_breakdown:
            result.update(breakdown)

        result['total_points_possible'] = total_possible
        result['total_points_awarded'] = total_awarded

        return result

    def _give_compilation_feedback(self, feedback_config):
        return (
            (feedback_config.compilation_feedback_level !=
                fbc.CompilationFeedbackLevel.no_feedback) and
            self.test_case.test_checks_compilation())

    def _give_return_code_feedback(self, feedback_config):
        return (
            (feedback_config.return_code_feedback_level !=
                fbc.ReturnCodeFeedbackLevel.no_feedback) and
            self.test_case.test_checks_return_code())

    def _give_output_correctness_feedback(self, feedback_config):
        return (
            (feedback_config.output_feedback_level !=
                fbc.OutputFeedbackLevel.no_feedback) and
            self.test_case.test_checks_output())

    def _give_valgrind_feedback(self, feedback_config):
        return (
            self.test_case.use_valgrind and
            (feedback_config.valgrind_feedback_level !=
                fbc.ValgrindFeedbackLevel.no_feedback))

# -----------------------------------------------------------------------------

_DIFFER = difflib.Differ()


def _get_diff(first, second):
    return list(_DIFFER.compare(
        first.splitlines(keepends=True), second.splitlines(keepends=True)))
