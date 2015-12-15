import os
import copy

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinValueValidator, MaxValueValidator, RegexValidator)

from autograder.core.models.utils import (
    PolymorphicModelValidatableOnSave, PolymorphicManagerWithValidateOnCreate)

import autograder.utilities.fields as ag_fields

import autograder.core.shared.global_constants as gc
import autograder.core.shared.utilities as ut
import autograder.core.shared.feedback_configuration as fbc


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

        hide_from_students -- When this field is True, students will not
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

        test_resource_files -- A list of project files that need to be
            in the same directory as the program being tested. This
            includes source code dependencies,
            files that the program will read from/write to, etc.
            This list is allowed to be empty.
            This value may NOT be None.
            IMPORTANT: Each of these files must have been uploaded to the
                Project associated with this test case. Including a filename
                in this list that does not exist for the Project will
                cause ValidationError to be raised.
            As such, these filenames are restricted to the same charset
                as uploaded project files.

            Default value: empty list

        student_resource_files -- A list of student files or pattern
            that need to be in the same directory when the test case is run,
            i.e. source code files, etc.
            This list is allowed to be empty.
            This value may NOT be None.
            IMPORTANT: Each of these files must either be listed in
            project.required_student_files or match one of the patterns in
            project.expected_student_file_patterns, otherwise ValidationError
            will be raised. As such, these filenames are restricted to the
            same charset as uploaded project files.

            Default value: empty list

        time_limit -- The time limit in seconds to be placed on the
            program being tested. This limit currently applies to each of:
            compilation, running the program, and running the program
            with Valgrind (the timeout is applied separately to each).
            Must be > 0
            Must be <= 60 TODO: add test and validation for this
            Default value: autograder.shared.global_constants
                                     .DEFAULT_SUBPROCESS_TIMEOUT seconds

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

        TODO: always use --error-exitcode=<something>, get rid of default values
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

        valgrind_time_limit -- TODO

        points_for_correct_return_code -- The number of points to be awarded
            for the program being tested exiting with the correct return_code.
            Default value: 0

        points_for_correct_output -- The number of points to be awarded
            for the program being tested producing the correct output
            (standard out and standard error).
            Default value: 0

        deduction_for_valgrind_errors -- The number of points to be deducted
            if the program being tested triggers any valgrind errors.
            Valgrind errors are indicated by a nonzero return code.
            This value is subtracted from
                points_for_correct_output + points_for_correct_return_code,
                and the result will NOT go below 0.
            Default value: 0

        points_for_compilation_success -- The number of points to be
            awarded for the program being tested compiling successfully.
            Default value: 0

        feedback_configuration -- Specifies how much information should be
            included in serialized run results.
            Default value: default-initialized
                AutograderTestCaseFeedbackConfiguration object

        interpreter -- TODO
        interpreter_flags -- TODO
        entry_point_file -- TODO

    Instance methods:
        test_checks_return_code()
        test_checks_output()
        test_checks_compilation()

    Abstract methods:
        run()
        get_type_str()

    Overridden methods:
        __init__()
        clean()
    """
    class Meta:
        unique_together = ('name', 'project')

    objects = PolymorphicManagerWithValidateOnCreate()

    name = ag_fields.ShortStringField()
    project = models.ForeignKey(
        'Project', related_name='autograder_test_cases')

    command_line_arguments = ag_fields.StringArrayField(
        strip_strings=True, allow_empty_strings=False,
        string_validators=[
            RegexValidator(gc.COMMAND_LINE_ARG_WHITELIST_REGEX)],
        default=list, blank=True)

    standard_input = models.TextField(blank=True)

    test_resource_files = ag_fields.StringArrayField(
        default=[], blank=True, strip_strings=False)
    student_resource_files = ag_fields.StringArrayField(
        default=[], blank=True, strip_strings=False)

    time_limit = models.IntegerField(
        default=gc.DEFAULT_SUBPROCESS_TIMEOUT,
        validators=[MinValueValidator(1),
                    MaxValueValidator(gc.MAX_SUBPROCESS_TIMEOUT)])

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

    valgrind_flags = ag_fields.StringArrayField(
        null=True,
        strip_strings=True, allow_empty_strings=False,
        string_validators=[
            RegexValidator(gc.COMMAND_LINE_ARG_WHITELIST_REGEX)],
        default=None, blank=True)

    # Point distribution fields
    points_for_correct_return_code = models.IntegerField(
        default=0, validators=[MinValueValidator(0)])
    points_for_correct_output = models.IntegerField(
        default=0, validators=[MinValueValidator(0)])
    deduction_for_valgrind_errors = models.IntegerField(
        default=0, validators=[MinValueValidator(0)])
    points_for_compilation_success = models.IntegerField(
        default=0, validators=[MinValueValidator(0)])

    feedback_configuration = ag_fields.JsonSerializableClassField(
        fbc.AutograderTestCaseFeedbackConfiguration,
        default=fbc.AutograderTestCaseFeedbackConfiguration)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.use_valgrind and self.valgrind_flags is None:
            self.valgrind_flags = gc.DEFAULT_VALGRIND_FLAGS_WHEN_USED

    # -------------------------------------------------------------------------

    def run(self, submission, autograder_sandbox):
        """
        Runs this autograder test case and returns an
        AutograderTestCaseResult object that is linked
        to the given submission. If submission is None,
        the result object will not be linked to any submission.
        The test case will be run inside the given AutograderSandbox.

        NOTE: This method does NOT save the result object to the
            database.

        This method must be overridden by derived classes.
        """
        raise NotImplementedError("Derived classes must override this method.")

    def _compile_program(self, submission, result_ref, autograder_sandbox):
        compilation_command = (
            [self.compiler] + self.compiler_flags +
            self.files_to_compile_together
        )

        if self.compiler == 'g++' and self.executable_name:
            compilation_command += ['-o', self.executable_name]

        compile_result = autograder_sandbox.run_cmd_with_redirected_io(
            compilation_command, timeout=self.time_limit)
        result_ref.submission = submission
        result_ref.compilation_standard_output = compile_result.stdout
        result_ref.compilation_standard_error_output = compile_result.stderr
        result_ref.compilation_return_code = compile_result.return_code

    # -------------------------------------------------------------------------

    def clean(self):
        super().clean()

        errors = {}

        test_resource_file_errors = self._clean_test_resouce_files()
        if test_resource_file_errors:
            errors['test_resource_files'] = test_resource_file_errors

        student_resource_file_errors = self._clean_student_resource_files()
        if student_resource_file_errors:
            errors['student_resource_files'] = student_resource_file_errors

        if errors:
            raise ValidationError(errors)

    def _clean_test_resouce_files(self):
        if self.test_resource_files is None:
            return ["This field can't be null"]

        resource_file_errors = []
        for filename in self.test_resource_files:
            if not self.project.has_file(filename):
                resource_file_errors.append(
                    "File {0} is not a project file project {1}".format(
                        filename, self.project.name))

        return resource_file_errors

    def _clean_student_resource_files(self):
        if self.student_resource_files is None:
            return ["This field can't be null"]

        resource_file_errors = []
        for filename in self.student_resource_files:
            is_required = filename in self.project.required_student_files
            is_expected_pattern = filename in (
                obj.pattern for obj in
                self.project.expected_student_file_patterns)
            # filename_matches_any_pattern(
            #     filename, self.project.expected_student_file_patterns)
            if not is_required and not is_expected_pattern:
                resource_file_errors.append(
                    "File {0} is not a student file for project {1}".format(
                        filename, self.project.name))

        return resource_file_errors

    # -------------------------------------------------------------------------

    # TODO: Remove "test_" prefix from these names

    def test_checks_return_code(self):
        return (
            self.expected_return_code is not None or
            self.expect_any_nonzero_return_code)

    def test_checks_output(self):
        return (self.expected_standard_output or
                self.expected_standard_error_output)

    def test_checks_compilation(self):
        raise NotImplementedError('Subclasses must override this method')

    def get_type_str(self):
        raise NotImplementedError('Subclasses must override this method')
