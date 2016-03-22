import os
import fnmatch

from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

from .student_test_suite_base import StudentTestSuiteBase

from autograder.core.models.utils import (
    PolymorphicModelValidatableOnSave, PolymorphicManagerWithValidateOnCreate)

from .student_test_suite_result import (
    StudentTestSuiteResult, StudentTestCaseEvaluationResult)

import autograder.utilities.fields as ag_fields

import autograder.core.shared.utilities as ut
import autograder.core.shared.global_constants as gc


class CompiledStudentTestSuite(StudentTestSuiteBase):
    """
    This class enables evaluating a suite of student test cases that
    are compiled and then run.

    Fields:
        compiler -- The program that will be used to compile the test case
            executables.
            See autograder.shared.global_constants.SUPPORTED_COMPILERS
            for a list of allowed values for this field.
            This field is REQUIRED.

        compiler_flags -- A list of option flags to be passed to the compiler.
            These flags are limited to the character set specified by
            autograder.shared.global_constants.COMMAND_LINE_ARG_WHITELIST_REGEX
            NOTE: This list should NOT include the names of files that
                need to be compiled and should not include flags that affect
                the name of the resulting executable program.
            This field is allowed to be empty.
            This field may not be None.
            Default value: empty list

        suite_resource_files_to_compile_together -- A list of filenames
            that will be compiled together with
            each student test case, implementation file pair.
            These filenames must be contained in suite_resource_filenames.
            This field is allowed to be empty.
            This field may not be None.
            Default value: empty list

        compile_implementation_files -- When this flag is True, the current
            correct of buggy implementation file will be compiled together
            with the current test case and specified resource files.
            When this value is False, the implementation files are NOT
            compiled together.
            Note that this field is only considered by types of test suite
            that use a compiler.
            Default value: True

    Overridden methods:
        evaluate()
        to_dict()
    """
    objects = PolymorphicManagerWithValidateOnCreate()

    # -------------------------------------------------------------------------

    compiler = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN,
        choices=zip(gc.SUPPORTED_COMPILERS, gc.SUPPORTED_COMPILERS))

    compiler_flags = ag_fields.StringArrayField(
        default=list, blank=True, string_validators=[
            RegexValidator(gc.COMMAND_LINE_ARG_WHITELIST_REGEX)])

    suite_resource_files_to_compile_together = ag_fields.StringArrayField(
        default=list, blank=True)

    compile_implementation_files = models.BooleanField(default=True)

    # -------------------------------------------------------------------------

    def get_type_str(self):
        return 'compiled_student_test_suite'

    def evaluate(self, submission, autograder_sandbox):
        submission_dir = ut.get_submission_dir(submission)
        test_files = fnmatch.filter(
            os.listdir(submission_dir),
            self.student_test_case_filename_pattern)

        results = StudentTestSuiteResult(
            test_suite=self, submission=submission)

        for test_file in test_files:
            test_result = self._evaluate_test_case(
                submission_dir, test_file, autograder_sandbox,
                results.buggy_implementations_exposed)
            results.detailed_results.append(test_result)
            results.buggy_implementations_exposed.update(
                test_result.buggy_implementations_exposed)

        return results

    def _evaluate_test_case(self, submission_dir, test_file,
                            autograder_sandbox, impls_exposed_so_far):
        print('evaluating test: ', test_file)
        project_dir = ut.get_project_files_dir(self.project)
        resource_file_abspaths = [
            os.path.join(project_dir, filename)
            for filename in self.suite_resource_filenames
        ]

        impl_abspath = os.path.join(
            project_dir, self.correct_implementation_filename)
        test_file_abspath = os.path.join(submission_dir, test_file)

        autograder_sandbox.add_files(
            test_file_abspath, *resource_file_abspaths)

        impl_name = (
            self.implementation_file_alias if self.implementation_file_alias
            else self.correct_implementation_filename)
        autograder_sandbox.add_and_rename_file(
            impl_abspath, impl_name)

        exe_name = 'prog'
        files_to_compile = self.suite_resource_filenames + [test_file]
        if self.compile_implementation_files:
            files_to_compile.append(impl_name)
        validity_compilation_result = autograder_sandbox.run_command(
            [self.compiler] + self.compiler_flags + files_to_compile +
            ['-o', exe_name],
            timeout=self.time_limit)

        eval_result = StudentTestCaseEvaluationResult(
            test_file,
            compilation_return_code=validity_compilation_result.return_code,
            compilation_standard_output=validity_compilation_result.stdout,
            compilation_standard_error_output=validity_compilation_result.stderr)

        if validity_compilation_result.return_code != 0:
            return eval_result

        validity_run_result = autograder_sandbox.run_command(
            ['./' + exe_name],
            timeout=self.time_limit,
            max_num_processes=gc.DEFAULT_PROCESS_LIMIT,
            max_stack_size=gc.DEFAULT_STACK_SIZE_LIMIT,
            max_virtual_memory=gc.DEFAULT_VIRTUAL_MEM_LIMIT
        )

        eval_result.valid = (
            validity_run_result.return_code == 0 and
            not validity_run_result.timed_out)
        eval_result.validity_check_standard_output = validity_run_result.stdout
        eval_result.validity_check_standard_error_output = validity_run_result.stderr
        eval_result.timed_out = validity_run_result.timed_out

        autograder_sandbox.reset()

        if not eval_result.valid:
            return eval_result

        for buggy_impl in self.buggy_implementation_filenames:
            if buggy_impl in impls_exposed_so_far:
                continue

            print('evaluating buggy impl:', buggy_impl)
            buggy_impl_abspath = os.path.join(project_dir, buggy_impl)
            autograder_sandbox.add_files(
                test_file_abspath, *resource_file_abspaths)
            impl_name = (
                self.implementation_file_alias if
                self.implementation_file_alias else buggy_impl)
            autograder_sandbox.add_and_rename_file(
                buggy_impl_abspath, impl_name)

            files_to_compile = self.suite_resource_filenames + [test_file]
            if self.compile_implementation_files:
                files_to_compile.append(impl_name)
            compile_result = autograder_sandbox.run_command(
                [self.compiler] + self.compiler_flags +
                files_to_compile + ['-o', exe_name],
                timeout=self.time_limit)

            if compile_result.return_code != 0:
                continue

            run_result = autograder_sandbox.run_command(
                ['./' + exe_name],
                timeout=self.time_limit,
                max_num_processes=gc.DEFAULT_PROCESS_LIMIT,
                max_stack_size=gc.DEFAULT_STACK_SIZE_LIMIT,
                max_virtual_memory=gc.DEFAULT_VIRTUAL_MEM_LIMIT)

            if run_result.return_code != 0:
                eval_result.buggy_implementations_exposed.append(buggy_impl)

            autograder_sandbox.reset()

        return eval_result

    # -------------------------------------------------------------------------

    def clean(self):
        errors = {}
        try:
            super().clean()
        except ValidationError as e:
            errors = e.message_dict

        errors.update(self._clean_suite_resource_files_to_compile_together())

        if errors:
            raise ValidationError(errors)

    def _clean_suite_resource_files_to_compile_together(self):
        errors = []

        for filename in self.suite_resource_files_to_compile_together:
            if filename in self.suite_resource_filenames:
                continue

            errors.append(
                '{} is not a suite resource file for test suite {}'.format(
                    filename, self.name))

        if errors:
            return {'suite_resource_files_to_compile_together': errors}

        return {}

    # -------------------------------------------------------------------------

    def to_dict(self):
        value = super().to_dict()
        value.update({
            "compiler": self.compiler,
            "compiler_flags": self.compiler_flags,
            "suite_resource_files_to_compile_together": self.suite_resource_files_to_compile_together,
        })

        return value
