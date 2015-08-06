"""
Classes:
    AutograderTestCaseBase -- A fat interface for autograder test cases.
    CompiledAutograderTestCase -- Defines a structure for testing compiled
        programs.
"""

import subprocess

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

from autograder.models.utils import (
    PolymorphicModelValidatableOnSave, PolymorphicManagerWithValidateOnCreate)

from autograder.models import Project, CompiledAutograderTestCaseResult

import autograder.shared.global_constants as gc
import autograder.shared.utilities as ut


# A list of compilers that may be used in autograder test cases that
# require compilation.
SUPPORTED_COMPILERS = ["g++"]


def _validate_cmd_line_arg(arg):
    if not arg:
        raise ValidationError("This value can't be empty")

    ut.check_values_against_whitelist(
        [arg], gc.COMMAND_LINE_ARG_WHITELIST_REGEX)


class AutograderTestCaseBase(PolymorphicModelValidatableOnSave):
    """
    This base class provides a fat interface for
    test cases used to evaluate student-submitted code.

    Fields:
        name -- The name used to identify this test case.
                Must be non-empty and non-null.
                Must be unique among test cases associated with a given
                project.
                This field is REQUIRED.

        project -- The Project this test case is associated with.
                   This field is REQUIRED.

        hide_from_students -- When this field is True, students should not
            receive feedback about this test case.
            Note: Staff members will still receive feedback on this
                test case for their own submissions, but when viewing
                a student submission, this test case will still be hidden.
            Default value: True

        command_line_arguments -- A list of arguments to be passed
            to the program being tested.
            This list is allowed to be empty.
            This value may NOT be None.
            Individual arguments may contain alphanumeric characters,
                hyphen, underscore, period, and the equals sign.

            Default value: empty list

            When ValidationError is raised for this field, the error message
            will be a list containing strings corresponding (in order) to
            each argument in this field. The strings will contain an error
            message for their corresponding argument or be empty if their
            corresponding argument did not cause an error.

        standard_input -- A string whose contents
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
            Default value: 10 seconds

        expected_return_code -- The return code that the
            program being tested should exit with in order to pass
            this test case.
            When expect_any_nonzero_return_code is False, a value of
                None indicates that this test case should not
                check the program's return code.
            Default value: None

        expect_any_nonzero_return_code -- Indicates that rather than
            checking for a specific return code, this test case should
            evaluate whether the program being tested exited with
            any return code other than zero.
            If this field is True, the value of expected_return_code
                is ignored
            Default value: False

        expected_standard_output -- A string
            whose contents should be compared to the standard output
            of the program being tested.
            A value of the empty string indicates that this
                test case should not check the standard output of the
                program being tested.
            Default value: empty string

        expected_standard_error_output -- A string
            whose contents should be compared to the standard error
            output of the program being tested.
            A value of the empty string indicates that this
                test case should not check the standard error output
                of the program being tested.
            Default value: empty string

        ignore_whitespace_in_output -- TODO
            Whether this test case should
            ignore whitespace when checking the output (standard output
            and standard error) of the program being tested.
            THIS FIELD HAS NOT YET BEEN IMPLEMENTED

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

            When ValidationError is raised for this field, the error message
            will be a list containing strings corresponding (in order) to
            each flag in this field. The strings will contain an error
            message for their corresponding flag or be empty if their
            corresponding flag did not cause an error.

        points_for_correct_return_code -- The number of points to be awarded
            for the program being tested exiting with the correct return_code.
            Default value: 0

        points_for_correct_output -- The number of points to be awarded
            for the program being tested producing the correct output
            (standard out and standard error).
            Default value: 0

        points_for_no_valgrind_errors -- The number of points to be awarded
            for the program being tested not triggering any valgrind errors.
            Default value: 0

        points_for_compilation_success -- The number of points to be
            awarded for the program being tested compiling successfully.
            Default value: 0


    Fat interface fields:
        NOTE: These fields all default to a "Falsy" value and should be
            used by derived classes to specifically define how types of
            autograder tests should run, i.e. A compiled program, an
            interpreted program, a compilation-only program, a compiled
            and interpreted program, etc.

        compiler -- The program that will be used to compile the program.
            Currently supported values: g++
            Default value: empty string

        compiler_flags -- A list of option flags to be passed to the compiler.
            These flags are limited to the same character set as
            the command_line_arguments field.
            NOTE: This list should NOT include the names of files that
                need to be compiled and should not include flags that affect
                the name of the resulting executable program.

            Default value: empty list

            When ValidationError is raised for this field, the error message
            will be a list containing strings corresponding (in order) to
            each flag in this field. The strings will contain an error
            message for their corresponding flag or be empty if their
            corresponding flag did not cause an error.

        files_to_compile_together -- A list of files that need to be
            compiled together. These filenames are restricted to those
            in project.required_student_files and project.project files,
            and may also include patterns from
            project.expected_student_file_patterns.
            NOTE: When a pattern is part of this list, all student-submitted
                files matching the pattern will be compiled together.

            Default value: empty list

        executable_name -- The name of the executable program that should be
            produced by the compiler. This is the program that will be tested.
            This field is restricted to the same charset as uploaded
            project files.
            Default value: empty string

        interpreter -- TODO
        interpreter_flags -- TODO
        entry_point_file -- TODO

    Abstract methods:
        run()

    Overridden methods:
        __init__()
        clean()
    """
    class Meta:
        unique_together = ('name', 'project')

    objects = PolymorphicManagerWithValidateOnCreate()

    name = models.CharField(max_length=gc.MAX_CHAR_FIELD_LEN)
    project = models.ForeignKey(Project, related_name='autograder_test_cases')

    hide_from_students = models.BooleanField(default=True)

    command_line_arguments = ArrayField(
        models.CharField(
            max_length=gc.MAX_CHAR_FIELD_LEN,
            blank=True  # We are setting this here so that the clean method
                        # can check for emptiness and throw a more specific
                        # error. This lets us send ValidationErrors
                        # to the GUI side in a more convenient format.
                        # This comment also applies to valgrind_flags and
                        # compiler_flags.
            ),
        blank=True, default=list)

    standard_input = models.TextField(blank=True)

    test_resource_files = ArrayField(
        models.CharField(max_length=gc.MAX_CHAR_FIELD_LEN),
        default=list, blank=True)

    time_limit = models.IntegerField(
        default=gc.DEFAULT_SUBPROCESS_TIMEOUT,
        validators=[MinValueValidator(1)])

    expected_return_code = models.IntegerField(
        null=True, default=None, blank=True)
    expect_any_nonzero_return_code = models.BooleanField(default=False)

    expected_standard_output = models.TextField(blank=True)

    expected_standard_error_output = models.TextField(blank=True)

    @property
    def use_valgrind(self):
        return self._use_valgrind

    @use_valgrind.setter
    def use_valgrind(self, value):
        if value and self.valgrind_flags is None:
            self.valgrind_flags = gc.DEFAULT_VALGRIND_FLAGS_WHEN_USED

        self._use_valgrind = value

    _use_valgrind = models.BooleanField(default=False)

    valgrind_flags = ArrayField(
        models.CharField(
            max_length=gc.MAX_CHAR_FIELD_LEN,
            blank=True  # See comment for command_line_arguments
            ),
        null=True, default=None, blank=True)

    # Point distribution fields
    points_for_correct_return_code = models.IntegerField(
        default=0, validators=[MinValueValidator(0)])
    points_for_correct_output = models.IntegerField(
        default=0, validators=[MinValueValidator(0)])
    points_for_no_valgrind_errors = models.IntegerField(
        default=0, validators=[MinValueValidator(0)])
    points_for_compilation_success = models.IntegerField(
        default=0, validators=[MinValueValidator(0)])

    # Fat interface fields
    compiler = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN, blank=True)

    compiler_flags = ArrayField(
        models.CharField(
            max_length=gc.MAX_CHAR_FIELD_LEN,
            blank=True  # See comment for command_line_arguments
            ),
        default=list, blank=True)

    files_to_compile_together = ArrayField(
        models.CharField(max_length=gc.MAX_CHAR_FIELD_LEN),
        default=list, blank=True)

    executable_name = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN, blank=True)

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
            AutograderTestCaseResultBase object.
        Note that this method does NOT save the result object to the
            database.

        This method must be overridden by derived classes.
        """
        raise NotImplementedError("Derived classes must override this method.")

    # -------------------------------------------------------------------------

    def clean(self):
        super().clean()

        errors = {}

        if self.name:
            self.name = self.name.strip()

        if not self.name:
            errors['name'] = "This field can't be empty"

        cmd_arg_errors = self._clean_command_line_arguments()
        if cmd_arg_errors:
            errors['command_line_arguments'] = cmd_arg_errors

        valgrind_flag_errors = self._clean_valgrind_flags()
        if valgrind_flag_errors:
            errors['valgrind_flags'] = valgrind_flag_errors

        resource_file_errors = self._clean_test_resouce_files()
        if resource_file_errors:
            errors['test_resource_files'] = resource_file_errors

        if errors:
            raise ValidationError(errors)

    def _clean_command_line_arguments(self):
        if self.command_line_arguments is None:
            return ["This field can't be null"]

        self.command_line_arguments = [
            arg.strip() for arg in self.command_line_arguments]

        return self._clean_arg_list(self.command_line_arguments)

    def _clean_valgrind_flags(self):
        if not self.use_valgrind:
            return None

        if self.valgrind_flags is None:
            return ["When using valgrind, valgrind_flags cannot be None"]

        self.valgrind_flags = [
            arg.strip() for arg in self.valgrind_flags]

        return self._clean_arg_list(self.valgrind_flags)

    def _clean_test_resouce_files(self):
        if self.test_resource_files is None:
            return ["This field can't be null"]

        resource_file_errors = []
        for filename in self.test_resource_files:
            if not self.project.has_file(filename):
                resource_file_errors.append(
                    "File {0} does not exist in project {1}".format(
                        filename, self.project.name))

        return resource_file_errors

    def _clean_arg_list(self, arg_list):
        errors = []
        error_found = False
        for arg in arg_list:
            try:
                _validate_cmd_line_arg(arg)
                errors.append('')
            except ValidationError as e:
                error_found = True
                errors.append(e.message)

        if error_found:
            return errors

        return None


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class CompiledAutograderTestCase(AutograderTestCaseBase):
    """
    This class allows evaluating a program that will be compiled
    from student-submitted code.

    This class does not define any new fields.
    Instead, the following fields inherited from the base class
    are now REQUIRED:
        compiler
        compiler_flags (This field is allowed to be empty)
        files_to_compile_together
        executable_name

    Overridden methods:
        clean()
        run()
    """
    objects = PolymorphicManagerWithValidateOnCreate()

    def clean(self):
        errors = {}

        try:
            super().clean()
        except ValidationError as e:
            errors = e.message_dict

        if self.compiler not in SUPPORTED_COMPILERS:
            errors['compiler'] = 'Unsupported compiler'

        compiler_flag_errors = self._clean_compiler_flags()
        if compiler_flag_errors:
            errors['compiler_flags'] = compiler_flag_errors

        files_to_compile_errors = self._clean_files_to_compile_together()
        if files_to_compile_errors:
            errors['files_to_compile_together'] = files_to_compile_errors

        try:
            if self.executable_name:
                self.executable_name = self.executable_name.strip()

            ut.check_user_provided_filename(self.executable_name)
        except ValidationError as e:
            errors['executable_name'] = e.message

        if errors:
            raise ValidationError(errors)

    def _clean_compiler_flags(self):
        if self.compiler_flags is None:
            return ['This value cannot be null']

        self.compiler_flags = [arg.strip() for arg in self.compiler_flags]

        return self._clean_arg_list(self.compiler_flags)

    def _clean_files_to_compile_together(self):
        if not self.files_to_compile_together:
            return ['At least one file must be specified for compilation']

        errors = []
        patterns = [pattern_obj.pattern for pattern_obj in
                    self.project.expected_student_file_patterns]
        for filename in self.files_to_compile_together:
            valid_filename = (
                filename in self.project.get_project_file_basenames() or
                filename in self.project.required_student_files or
                filename in patterns
            )

            if not valid_filename:
                errors.append('File {0} not found for project {1}'.format(
                    filename, self.project.name))

        return errors

    # -------------------------------------------------------------------------

    def run(self):
        result = CompiledAutograderTestCaseResult(test_case=self)

        compilation_command = (
            [self.compiler] + self.compiler_flags +
            self.files_to_compile_together + ['-o', self.executable_name]
        )

        runner = _SubprocessRunner(compilation_command)
        result._compilation_standard_output = runner.stdout
        result._compilation_standard_error_output = runner.stderr
        result._compilation_return_code = runner.return_code

        if result._compilation_return_code != 0 or result.timed_out:
            # print(result._compilation_return_code)
            # print(runner.stderr)
            return result

        run_program_cmd = (
            ['./' + self.executable_name] + self.command_line_arguments
        )

        runner = _SubprocessRunner(
            run_program_cmd, timeout=self.time_limit,
            stdin_content=self.standard_input)

        result._return_code = runner.return_code
        result._standard_output = runner.stdout
        result._standard_error_output = runner.stderr
        result._timed_out = runner.timed_out

        if not self.use_valgrind:
            return result

        valgrind_run_cmd = ['valgrind'] + self.valgrind_flags + run_program_cmd

        # Note the increased time limit. This is because using valgrind
        # causes the program to run drastically slower.
        runner = _SubprocessRunner(
            valgrind_run_cmd, timeout=self.time_limit * 2,
            stdin_content=self.standard_input, merge_stdout_and_stderr=True)

        result._valgrind_return_code = runner.return_code
        result._valgrind_output = runner.stdout

        return result


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

# TODO: Once upgraded to Python 3.5 and Django 1.9, replace Popen with the
# new subprocess.run() method.
class _SubprocessRunner(object):
    """
    Convenience wrapper for calling Popen and retrieving the data
    we usually need.
    """
    def __init__(self, program_args, **kwargs):
        self._args = program_args
        self._timeout = kwargs.get('timeout', gc.DEFAULT_SUBPROCESS_TIMEOUT)
        self._stdin_content = kwargs.get('stdin_content', '')
        self._merge_stdout_and_stderr = kwargs.get(
            'merge_stdout_and_stderr', False)

        self._timed_out = False
        self._return_code = None
        self._stdout = None
        self._stderr = None

        self._process = None

        self._run()

    @property
    def timed_out(self):
        return self._timed_out

    @property
    def return_code(self):
        return self._return_code

    @property
    def stdout(self):
        return self._stdout

    @property
    def stderr(self):
        return self._stderr

    @property
    def process(self):
        return self._process

    def _run(self):
        # Note: It is not possible to use string streams
        # (io.StringIO) with subprocess.call() because they do not
        # have a fileno attribute. This is not a huge issue, as using
        # Popen and subprocess.PIPE is the preferred approach to
        # redirecting input and output from strings.
        self._process = subprocess.Popen(
            self._args,
            universal_newlines=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=(subprocess.STDOUT if self._merge_stdout_and_stderr
                    else subprocess.PIPE)
        )

        try:
            self._stdout, self._stderr = self._process.communicate(
                input=self._stdin_content,
                timeout=self._timeout)

            self._process.stdin.close()

            self._return_code = self._process.returncode
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._stdout, self._stderr = self._process.communicate()
            self._return_code = self._process.returncode
            self._timed_out = True
