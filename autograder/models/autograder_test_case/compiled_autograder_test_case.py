"""
Classes:
    CompiledAutograderTestCase -- A test case that tests a program that must
        be compiled first and then run.
"""

import os
# from django.db import models
# from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
# from django.core.validators import MinValueValidator

from autograder.models.utils import PolymorphicManagerWithValidateOnCreate

from autograder.models import AutograderTestCaseResultBase

# import autograder.shared.global_constants as gc
import autograder.shared.utilities as ut

from .autograder_test_case_base import AutograderTestCaseBase
from .utils import SubprocessRunner


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
        test_checks_compilation()
        get_type_str()
    """
    objects = PolymorphicManagerWithValidateOnCreate()

    def clean(self):
        errors = {}

        try:
            super().clean()
        except ValidationError as e:
            errors = e.message_dict

        if self.compiler not in AutograderTestCaseBase.SUPPORTED_COMPILERS:
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

    def run(self, submission):
        result = AutograderTestCaseResultBase(test_case=self)

        compilation_command = (
            [self.compiler] + self.compiler_flags +
            self.files_to_compile_together + ['-o', self.executable_name]
        )

        runner = SubprocessRunner(compilation_command)
        result.submission = submission
        result.compilation_standard_output = runner.stdout
        result.compilation_standard_error_output = runner.stderr
        result.compilation_return_code = runner.return_code

        if result.compilation_return_code != 0 or result.timed_out:
            # print(result._compilation_return_code)
            # print(runner.stderr)
            return result

        run_program_cmd = (
            ['./' + self.executable_name] + self.command_line_arguments
        )

        runner = SubprocessRunner(
            run_program_cmd, timeout=self.time_limit,
            stdin_content=self.standard_input)

        result.return_code = runner.return_code
        result.standard_output = runner.stdout
        result.standard_error_output = runner.stderr
        result.timed_out = runner.timed_out

        if not self.use_valgrind:
            return result

        valgrind_run_cmd = ['valgrind'] + self.valgrind_flags + run_program_cmd

        runner = SubprocessRunner(
            valgrind_run_cmd, timeout=self.time_limit,
            stdin_content=self.standard_input)

        result.valgrind_return_code = runner.return_code
        result.valgrind_output = runner.stderr

        return result

    # -------------------------------------------------------------------------

    def test_checks_compilation(self):
        return True

    def get_type_str(self):
        return 'compiled_test_case'
