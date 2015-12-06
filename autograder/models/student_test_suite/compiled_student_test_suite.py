import os
import fnmatch

from .student_test_suite_base import StudentTestSuiteBase

from autograder.models.utils import (
    PolymorphicModelValidatableOnSave, PolymorphicManagerWithValidateOnCreate)

from .student_test_suite_result import (
    StudentTestSuiteResult, StudentTestCaseEvaluationResult)

import autograder.shared.utilities as ut


class CompiledStudentTestSuite(StudentTestSuiteBase):
    """
    This class enables evaluating a suite of student test cases that
    are compiled and then run.

    This class does not define any new fields.

    Overridden methods:
        evaluate()
    """
    objects = PolymorphicManagerWithValidateOnCreate()

    def evaluate(self, submission, autograder_sandbox):
        submission_dir = ut.get_submission_dir(submission)
        test_files = fnmatch.filter(
            os.listdir(submission_dir),
            self.student_test_case_filename_pattern)

        results = StudentTestSuiteResult(
            test_suite=self, submission=submission)

        for test_file in test_files:
            test_result = self._evaluate_test_case(
                submission_dir, test_file, autograder_sandbox)
            results.detailed_results.append(test_result)
            results.buggy_implementations_exposed.update(
                test_result.buggy_implementations_exposed)

        return results

    def _evaluate_test_case(self, submission_dir, test_file,
                            autograder_sandbox):
        print('evaluating test: ', test_file)
        project_dir = ut.get_project_files_dir(self.project)
        resource_file_abspaths = [
            os.path.join(project_dir, filename)
            for filename in self.suite_resource_filenames
        ]

        impl_abspath = os.path.join(
            project_dir, self.correct_implementation_filename)
        test_file_abspath = os.path.join(submission_dir, test_file)

        autograder_sandbox.copy_into_sandbox(
            test_file_abspath, *resource_file_abspaths)

        impl_name = (
            self.implementation_file_alias if self.implementation_file_alias
            else self.correct_implementation_filename)
        autograder_sandbox.copy_and_rename_into_sandbox(
            impl_abspath, impl_name)

        exe_name = 'prog'
        files_to_compile = self.suite_resource_filenames + [test_file]
        if self.compile_implementation_files:
            files_to_compile.append(impl_name)
        validity_compilation_result = autograder_sandbox.run_cmd_with_redirected_io(
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

        validity_run_result = autograder_sandbox.run_cmd_with_redirected_io(
            ['./' + exe_name], timeout=self.time_limit)

        eval_result.valid = (
            validity_run_result.return_code == 0 and
            not validity_run_result.timed_out)
        eval_result.validity_check_standard_output = validity_run_result.stdout
        eval_result.validity_check_standard_error_output = validity_run_result.stderr
        eval_result.timed_out = validity_run_result.timed_out

        autograder_sandbox.clear_working_dir()

        if not eval_result.valid:
            return eval_result

        for buggy_impl in self.buggy_implementation_filenames:
            print('evaluating buggy impl:', buggy_impl)
            buggy_impl_abspath = os.path.join(project_dir, buggy_impl)
            autograder_sandbox.copy_into_sandbox(
                test_file_abspath, *resource_file_abspaths)
            impl_name = (
                self.implementation_file_alias if
                self.implementation_file_alias else buggy_impl)
            autograder_sandbox.copy_and_rename_into_sandbox(
                buggy_impl_abspath, impl_name)

            files_to_compile = self.suite_resource_filenames + [test_file]
            if self.compile_implementation_files:
                files_to_compile.append(impl_name)
            compile_result = autograder_sandbox.run_cmd_with_redirected_io(
                [self.compiler] + self.compiler_flags +
                files_to_compile + ['-o', exe_name],
                timeout=self.time_limit)

            if compile_result.return_code != 0:
                continue

            run_result = autograder_sandbox.run_cmd_with_redirected_io(
                ['./' + exe_name], timeout=self.time_limit)

            if run_result.return_code != 0:
                eval_result.buggy_implementations_exposed.append(buggy_impl)

            autograder_sandbox.clear_working_dir()

        return eval_result
