import uuid

from django.core.exceptions import ValidationError

from django.core.validators import (
    MinValueValidator, MaxValueValidator, RegexValidator)

from autograder.core.models.utils import PolymorphicManagerWithValidateOnCreate

from .autograder_test_case_base import AutograderTestCaseBase

import autograder.utilities.fields as ag_fields
import autograder.core.shared.global_constants as gc
import autograder.core.shared.utilities as ut
# import autograder.core.shared.feedback_configuration as fbc

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)


class CompiledAutograderTestCase(AutograderTestCaseBase):
    """
    This class allows evaluating a program that will be compiled
    and then run.

    Fields:
        compiler -- The program that will be used to compile the test case
            executable.
            Currently supported values listed in
                autograder.shared.global_constants.SUPPORTED_COMPILERS
            This field is REQUIRED

        compiler_flags -- A list of option flags to be passed to the compiler.
            These flags are limited to the same character set as
            the command_line_arguments field.
            NOTE: This list should NOT include the names of files that
                need to be compiled and should not include flags that affect
                the name of the resulting executable program.

            This field is allowed to be empty.
            This field may not be None.
            Default value: empty list

        TODO
        project_files_to_compile_together -- A list of uploaded project
            filenames that need to be compiled together.
            These filenames are restricted to those in test_resource_files.
            Default value: empty list

        TODO
        student_files_to_compile_together -- A list of student-submitted
            filenames that need to be compiled together.
            These filenames are restricted to those in student_resource_files
            as well as patterns in expected_student_file_patterns.
            NOTE: When a pattern is part of this list, all student-submitted
                files matching the pattern will be compiled together.
            Default value: empty list

        REMOVE
        files_to_compile_together -- A list of files that need to be
            compiled together. These filenames are restricted to those
            in test_resource_files and student_resource_files.
            NOTE: When a pattern is part of this list, all student-submitted
                files matching the pattern will be compiled together.

            This field is REQUIRED and may not be empty.

        executable_name -- The name of the executable program that should be
            produced by the compiler. This is the program that will be tested.
            This field is restricted to the same charset as uploaded
            project files.

            Default value: "compiled_program"


        compilation_time_limit -- TODO

    Overridden methods:
        run()
        clean()
        test_checks_compilation()
        get_type_str()
    """
    class Meta:
        abstract = True

    objects = PolymorphicManagerWithValidateOnCreate()

    # Fat interface fields
    compiler = ag_fields.ShortStringField(
        choices=zip(gc.SUPPORTED_COMPILERS, gc.SUPPORTED_COMPILERS))

    compiler_flags = ag_fields.StringArrayField(
        default=list, blank=True, string_validators=[
            RegexValidator(gc.COMMAND_LINE_ARG_WHITELIST_REGEX)],
        )

    project_files_to_compile_together = ag_fields.StringArrayField(
        default=list, blank=True, strip_strings=False)

    student_files_to_compile_together = ag_fields.StringArrayField(
        default=list, blank=True, strip_strings=False)

    executable_name = ag_fields.ShortStringField(
        validators=[ut.check_user_provided_filename],
        default="compiled_program")

    def test_checks_compilation(self):
        return True

    def clean(self):
        errors = {}

        try:
            super().clean()
        except ValidationError as e:
            errors = e.message_dict

        errors.update(self._clean_project_files_to_compile_together())
        errors.update(self._clean_student_files_to_compile_together())

        if errors:
            raise ValidationError(errors)

    def _clean_project_files_to_compile_together(self):
        errors = []
        for filename in self.project_files_to_compile_together:
            if filename not in self.test_resource_files:
                errors.append(
                    'File {0} not a resource file for this test'.format(
                        filename))

        if errors:
            return {'project_files_to_compile_together': errors}

        return {}

    def _clean_student_files_to_compile_together(self):
        errors = []
        for filename in self.student_files_to_compile_together:
            if filename not in self.student_resource_files:
                errors.append(
                    'File {0} not a resource file for this test'.format(
                        filename))

        if errors:
            return {'student_files_to_compile_together': errors}

        return {}

    # -------------------------------------------------------------------------

    def _compile_program(self, submission, result_ref, autograder_sandbox):
        compilation_command = (
            [self.compiler] + self.compiler_flags +
            self.project_files_to_compile_together +
            self.student_files_to_compile_together
        )

        if self.compiler == 'g++' and self.executable_name:
            compilation_command += ['-o', self.executable_name]

        compile_result = autograder_sandbox.run_cmd_with_redirected_io(
            compilation_command, timeout=self.time_limit)
        result_ref.submission = submission
        result_ref.compilation_standard_output = compile_result.stdout
        result_ref.compilation_standard_error_output = compile_result.stderr
        result_ref.compilation_return_code = compile_result.return_code
