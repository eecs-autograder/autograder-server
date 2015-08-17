import difflib

from django.db import models

from polymorphic import PolymorphicModel

_DIFFER = difflib.Differ()


class AutograderTestCaseResultBase(PolymorphicModel):
    """
    This class stores the data from an autograder test case
    and provides an interface for serializing the data.

    Fields:
        test_case -- The test case whose results this object is storing.

        submission -- The submission the test case was run for.

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

    Fat interface fields:
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
        return self.standard_output == self.test_case.expected_standard_output

    @property
    def standard_error_output_correct(self):
        return (self.standard_error_output ==
                self.test_case.expected_standard_error_output)

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

    # TODO: clean up implementation of this method
    def to_json(self, override_feedback=None):
        """
        Returns a JSON representation of this autograder test case result
        of the following form:
        {
            // Note that some or all of the following may be ommitted
            // depending on the feedback level.

            'return_code_correct': <True | False>,
            'expected_return_code': <value>,
            'actual_return_code': <value>,


            'output_correct': <True | False>,
            'stdout_diff': <diff>,
            'stderr_diff': <diff>,


            'valgrind_errors_present': <True | False>,
            'valgrind_output': <output>,


            'compilation_succeeded': <True | False>,
            'compilation_stdout': <value>,
            'compilation_stderr': <value>,


            'return_code_points': <points awarded>,
            'output_points': <points awarded>,
            'valgrind_points': <points awarded>,
            'compilation_points': <points awarded>,

            'total_points': <points>,


            'timed_out': <True | False>
        }
        """
        feedback = (override_feedback if override_feedback is not None
                    else self._get_feedback_config())
        data = {'test_name': self.test_case.name}

        if feedback.compilation_feedback_level == 'success_or_failure_only':
            data['compilation_succeeded'] = self.compilation_succeeded
        elif feedback.compilation_feedback_level == 'show_compiler_output':
            data['compilation_succeeded'] = self.compilation_succeeded
            data['compilation_stdout'] = self.compilation_standard_output
            data['compilation_stderr'] = self.compilation_standard_error_output

        if self.compilation_succeeded:
            data['timed_out'] = self.timed_out

        if self.compilation_succeeded and not self.timed_out:
            if feedback.return_code_feedback_level == 'correct_or_incorrect_only':
                data['return_code_correct'] = self.return_code_correct
            elif feedback.return_code_feedback_level == 'show_expected_and_actual_values':
                data['return_code_correct'] = self.return_code_correct
                data['expected_return_code'] = self.test_case.expected_return_code
                data['actual_return_code'] = self.return_code

            if feedback.output_feedback_level == 'correct_or_incorrect_only':
                data['output_correct'] = self.output_correct
            elif feedback.output_feedback_level == 'show_expected_and_actual_values':
                data['output_correct'] = self.output_correct
                data['stdout_diff'] = list(_DIFFER.compare(
                    self.test_case.expected_standard_output.splitlines(keepends=True),
                    self.standard_output.splitlines(keepends=True)))
                data['stderr_diff'] = list(_DIFFER.compare(
                    self.test_case.expected_standard_error_output.splitlines(keepends=True),
                    self.standard_error_output.splitlines(keepends=True)))

            if feedback.valgrind_feedback_level == 'errors_or_no_errors_only':
                data['valgrind_errors_present'] = self.valgrind_errors_present
            elif feedback.valgrind_feedback_level == 'show_valgrind_output':
                data['valgrind_errors_present'] = self.valgrind_errors_present
                data['valgrind_output'] = self.valgrind_output

        if feedback.points_feedback_level == 'hide':
            return data

        total_points = 0
        show_breakdown = feedback.points_feedback_level == 'show_breakdown'

        if feedback.compilation_feedback_level != 'no_feedback':
            points = (self.test_case.points_for_compilation_success if
                      self.compilation_succeeded else 0)
            total_points += points
            if show_breakdown:
                data['compilation_points'] = points

        if not self.compilation_succeeded or self.timed_out:
            data['total_points'] = total_points
            return data

        if feedback.return_code_feedback_level != 'no_feedback':
            points = (self.test_case.points_for_correct_return_code if
                      self.return_code_correct else 0)
            total_points += points
            if show_breakdown:
                data['return_code_points'] = points

        if feedback.output_feedback_level != 'no_feedback':
            points = (self.test_case.points_for_correct_output if
                      self.output_correct else 0)
            total_points += points
            if show_breakdown:
                data['output_points'] = points

        if feedback.valgrind_feedback_level != 'no_feedback':
            points = (self.test_case.points_for_no_valgrind_errors if
                      not self.valgrind_errors_present else 0)
            total_points += points
            if show_breakdown:
                data['valgrind_points'] = points

        data['total_points'] = total_points
        return data

    def _get_feedback_config(self):
        override = (
            self.submission is not None and
            self.submission.test_case_feedback_config_override is not None)

        if override:
            return self.submission.test_case_feedback_config_override

        return self.test_case.project.test_case_feedback_configuration

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class CompiledAutograderTestCaseResult(AutograderTestCaseResultBase):
    """
    Stores the results from a compiled autograder test case.

    Instance variables:
        compilation_succeeded

    Overidden methods:
        to_json()
        human_readable_summary() TODO
    """
    pass
    # def to_json(self, override_feedback=None):
    #     """
    #     Returns a JSON representation of this compiled test case result.
    #     The following fields are added to the base data:

    #     {
    #         'compilation_succeeded': <True | False>,
    #         'compilation_stdout': <value>,
    #         'compilation_stderr': <value>,

    #         'compilation_points': <points awarded>,
    #     }
    #     """
    #     base = super().to_json(override_feedback=override_feedback)

    # @property
    # def compilation_succeeded(self):
    #     return self.compilation_return_code == 0
