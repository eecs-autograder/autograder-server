from django.db import models

from jsonfield import JSONField

from autograder.models.model_validated_on_save import ModelValidatedOnSave
from autograder.models import Project

import autograder.shared.global_constants as gc
import autograder.shared.utilities as ut


class AutograderTestCaseBase(ModelValidatedOnSave):
    """
    This base class provides a fat interface for
    test cases used to evaluate student-submitted code.

    Primary key: Composite based on this test case's name and Project.

    Fields:
        name -- The name used to identify this test case.
                Must be non-empty and non-null.
                Must be unique among test cases associated with a given
                project.
                This field is REQUIRED.

        project -- The Project this test case is associated with.
                   This field is REQUIRED.

        command_line_arguments -- A list of arguments to be passed
            to the program being tested.
            This list is allowed to be empty.
            This value may NOT be None.
            Individual arguments may contain alphanumeric characters,
                hyphen, underscore, and the equals sign.
            Default value: empty list

        standard_input_stream_contents -- A string whose contents
            should be sent to the standard input stream of the program
            being tested.
            Default value: empty string

        test_resource_files -- A list of files that need to be
            in the same directory as the program being tested.
            This list is allowed to be empty.
            This value may NOT be None.
            Each of these files must have been uploaded to the Project
                associated with this test case. Including a filename
                in this list that does not exist for the Project will
                cause ValueError to be raised.
            As such, these filenames are restricted to the same charset
                as uploaded project files.
            Default value: empty list

        time_limit -- The time limit in seconds to be placed on the
            program being tested.
            This value must be positive (and nonzero).
            Default value: 30 seconds

        expected_program_return_code -- The return code that the
            program being tested should exit with in order to pass
            this test case.
            A value of None indicates that this test case should not
                check the program's return code.
            The string "NONZERO" indicates that any non-zero return
                code should be accepted by this test case.
            Default value: None

        expected_program_standard_output_stream_content -- A string
            whose contents should be compared to the standard output
            of the program being tested.
            A value of the empty string indicates that this
                test case should not check the standard output of the
                program being tested.
            Default value: empty string

        expected_program_standard_error_stream_content -- A string
            whose contents should be compared to the standard error
            output of the program being tested.
            A value of the empty string indicates that this
                test case should not check the standard error output
                of the program being tested.
            Default value: empty string

        ignore_whitespace_in_output -- Whether this test case should
            ignore whitespace when checking the output (standard output
            and standard error) of the program being tested.
            TODO: This field has not yet been implemented

        use_valgrind -- Whether this test case should perform a second
            run of the program being tested using the program Valgrind:
            http://valgrind.org/
            Default value: False

        valgrind_flags -- If use_valgrind is True, this field should
            contain a list of command line arguments to be passed to the
            valgrind program.
            NOTE: This list should NOT contain any details about the
                program being tested.
            For example: ['--leak-check=full', '--error-exitcode=42']
            This list can be empty.
            This list can only be None if use_valgrind is False.
            Default value: ['--leak-check=full', '--error-exitcode=1'] if
                use_valgrind is true, None if use_valgrind is False.

    Static methods:
        get_by_composite_key()

    Abstract methods:
        run()

    Overridden methods:
        __init__()
        validate_fields()
    """
    name = models.CharField(max_length=gc.MAX_CHAR_FIELD_LEN)
    project = models.ForeignKey(Project)

    command_line_arguments = JSONField(default=[])
    standard_input_stream_contents = models.TextField()
    test_resource_files = JSONField(default=[])
    time_limit = models.IntegerField(default=30)

    @property
    def expected_program_return_code(self):
        try:
            return int(self._expected_program_return_code)
        except ValueError:
            return (None if not self._expected_program_return_code
                    else self._expected_program_return_code)

    _expected_program_return_code = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN)

    @expected_program_return_code.setter
    def expected_program_return_code(self, value):
        self._expected_program_return_code = str(value)

    expected_program_standard_output_stream_content = models.TextField()

    expected_program_standard_error_stream_content = models.TextField()

    use_valgrind = models.BooleanField(default=False)

    valgrind_flags = JSONField(null=True, default=None)

    _composite_primary_key = models.TextField(primary_key=True)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    @staticmethod
    def get_by_composite_key(name, project):
        return AutograderTestCaseBase.objects.get(
            pk=AutograderTestCaseBase._compute_composite_primary_key(
                name, project))

    @staticmethod
    def _compute_composite_primary_key(test_name, project):
        return "{0}_{1}_{2}_{3}".format(
            project.semester.course.name, project.semester.name,
            project.name, test_name)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.use_valgrind and self.valgrind_flags is None:
            self.valgrind_flags = gc.DEFAULT_VALGRIND_FLAGS_WHEN_USED

    # -------------------------------------------------------------------------

    def run(self):
        """
        Runs this autograder test case and returns an
            AutograderTestCaseResult object.
        Note that this method does NOT save the result object to the
            database.

        This method must be overridden by derived classes.
        """
        raise NotImplementedError("Derived classes must override this method.")

    # -------------------------------------------------------------------------

    def validate_fields(self):
        if not self.pk:
            self._composite_primary_key = self._compute_composite_primary_key(
                self.name, self.project)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

