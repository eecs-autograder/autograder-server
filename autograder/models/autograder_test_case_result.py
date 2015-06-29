from django.db import models


class AutograderTestResultBase(models.Model):
    """
    This read-only class stores the data from an autograder test case
    and provides an interface for summarizing the data in various
    formats (JSON, human-readable, etc.).

    Fields:
        test_case -- The test case whose results this object is storing.

        return_code -- The return code of the program that was tested.
            Default value: None

        standard_output -- The contents of the standard output stream
            of the program that was tested.
            Default value: empty string

        standard_error_output -- The contents of the standard error stream
            of the program that was tested.
            Default value: empty string

        valgrind_return_code -- The return code of the program valgrind
            when run against the program being tested.
            Default value: None

        valgrind_output -- The output (standard out and standard error)
            of the program valgrind when run against the program being
            tested.
            Default value: empty string

    Fat interface fields:
        compiler_return_code -- The return code of the command used
            to compile the program being tested.
            Default value: None

        compiler_standard_output -- The contents of the standard output
            stream of the command used to compile the program being tested.
            Default value: empty string

        compiler_standard_error_output -- The contents of the standard error
            stream of the command used to compile the program being tested.
            Default value: empty string

    Instance methods:
        json_summary()
        human_readable_summary()
    """
    def json_summary(self):
        """
        Returns summary of these test case results in JSON format.
        """
        pass

    # -------------------------------------------------------------------------

    def human_readable_summary(self):
        """
        Returns a human-readable summary of these
        test case results. Note that this method returns the same
        value as calling str() on this object.
        """
        pass


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class CompiledAutograderTestResult(AutograderTestResultBase):
    """
    Stores the results from a compiled autograder test case.

    Overidden methods:
        json_summary()
        human_readable_summary()
    """
    pass

