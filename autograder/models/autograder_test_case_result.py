from django.db import models

from polymorphic import PolymorphicModel


class AutograderTestCaseResultBase(PolymorphicModel):
    """
    This read-only class stores the data from an autograder test case
    and provides an interface for summarizing the data in various
    formats (JSON, human-readable, etc.).

    Instance variables:
        test_case -- The test case whose results this object is storing.

        submission -- TODO The submission the test case was run for.

        return_code -- The return code of the program that was tested.
            Default value: None

        return_code_correct -- Whether the program
            exited with the correct return code.

        standard_output -- The contents of the standard output stream
            of the program that was tested.
            Default value: empty string

        standard_output_correct -- Whether the program produced the
            correct standard output.

        standard_error_output -- The contents of the standard error stream
            of the program that was tested.
            Default value: empty string

        standard_error_output_correct -- Whether the program produced the
            correct standard error output.

        time_elapsed -- The amount of time it took to run the program
            being tested. TODO

        timed_out -- Whether the program exceeded the time limit.

        valgrind_return_code -- The return code of the program valgrind
            when run against the program being tested.
            Default value: None

        valgrind_errors_present -- Whether valgrind exited with nonzero
            status.

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

    Instance methods:
        timed_out()
        json_summary() TODO
        human_readable_summary() TODO
    """
    # Using a string here instead of class to get around circular dependency
    test_case = models.ForeignKey("AutograderTestCaseBase")

    @property
    def return_code(self):
        return self._return_code

    @property
    def return_code_correct(self):
        if self.test_case.expect_any_nonzero_return_code:
            return self.return_code != 0

        return self.return_code == self.test_case.expected_return_code

    @property
    def standard_output(self):
        return self._standard_output

    @property
    def standard_output_correct(self):
        return self.standard_output == self.test_case.expected_standard_output

    @property
    def standard_error_output(self):
        return self._standard_error_output

    @property
    def standard_error_output_correct(self):
        return (self.standard_error_output ==
                self.test_case.expected_standard_error_output)

    @property
    def timed_out(self):
        return self._timed_out

    # @property
    # def time_elapsed(self):
    #     return self._time_elapsed

    @property
    def valgrind_return_code(self):
        return self._valgrind_return_code

    @property
    def valgrind_errors_present(self):
        return self.valgrind_return_code != 0

    @property
    def valgrind_output(self):
        return self._valgrind_output

    @property
    def compilation_return_code(self):
        return self._compilation_return_code

    @property
    def compilation_standard_output(self):
        return self._compilation_standard_output

    @property
    def compilation_standard_error_output(self):
        return self._compilation_standard_error_output

    # The run() method of AutograderTestCaseBase and its derived classes
    # is allowed to access these fields directly. Other users should treat
    # this class as read-only.
    _return_code = models.IntegerField(null=True, default=None)
    _standard_output = models.TextField()
    _standard_error_output = models.TextField()
    _timed_out = models.BooleanField(default=False)
    # _time_elapsed = models.IntegerField(null=True, default=None)
    _valgrind_return_code = models.IntegerField(null=True, default=None)
    _valgrind_output = models.TextField()

    _compilation_return_code = models.IntegerField(null=True, default=None)
    _compilation_standard_output = models.TextField()
    _compilation_standard_error_output = models.TextField()

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    # def timed_out(self):
    #     """
    #     Returns True if the program being tested was terminated for
    #     exceeding the time limit, False otherwise.

    #     Returns None if time_elapsed is None.
    #     """
    #     if self.time_elapsed is None:
    #         return None

    # -------------------------------------------------------------------------

    # def json_summary(self):
    #     """
    #     Returns summary of these test case results in JSON format.
    #     """
    #     pass

    # # -------------------------------------------------------------------------

    # def human_readable_summary(self):
    #     """
    #     Returns a human-readable summary of these
    #     test case results. Note that this method returns the same
    #     value as calling str() on this object.
    #     """
    #     pass


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class CompiledAutograderTestCaseResult(AutograderTestCaseResultBase):
    """
    Stores the results from a compiled autograder test case.

    Instance variables:
        compilation_succeeded

    Overidden methods:
        json_summary() TODO
        human_readable_summary() TODO
    """
    @property
    def compilation_succeeded(self):
        return self.compilation_return_code == 0
