from autograder.models import (
    AutograderTestCaseBase, AutograderTestCaseFactory)

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from .shared_tests_and_setup import (
    SharedTestsAndSetupForTestsWithCompilation,
    SharedSetUpTearDownForRunTestsWithCompilation,
    CppProgramStrs)


class CompilationOnlyAutograderTestCaseTestCase(
        SharedTestsAndSetupForTestsWithCompilation,
        TemporaryFilesystemTestCase):

    def get_ag_test_type_str_for_factory(self):
        return 'compilation_only_test_case'

    def test_valid_create_custom_values(self):
        self.compiled_test_kwargs.pop('executable_name')
        AutograderTestCaseFactory.validate_and_create(
            'compilation_only_test_case',
            name=self.test_name, project=self.project,
            **self.compiled_test_kwargs)

        loaded_test = AutograderTestCaseBase.objects.get(
            name=self.test_name, project=self.project)

        self.assertEqual(self.compiler, loaded_test.compiler)
        self.assertEqual(self.compiler_flags, loaded_test.compiler_flags)
        self.assertEqual(
            self.files_to_compile_together,
            loaded_test.files_to_compile_together)

    def test_test_checks_return_code(self):
        test = AutograderTestCaseFactory.validate_and_create(
            'compilation_only_test_case',
            name=self.test_name, project=self.project,
            **self.compiled_test_kwargs)

        self.assertFalse(test.test_checks_return_code())

    def test_test_checks_output(self):
        test = AutograderTestCaseFactory.validate_and_create(
            'compilation_only_test_case',
            name=self.test_name, project=self.project,
            **self.compiled_test_kwargs)

        self.assertFalse(test.test_checks_output())

# import unittest
# @unittest.skip('in flux')
class CompilationOnlyAutograderTestRunTestCase(
        SharedSetUpTearDownForRunTestsWithCompilation,
        TemporaryFilesystemTestCase):

    def get_ag_test_type_str_for_factory(self):
        return 'compilation_only_test_case'

    def test_compilation_success(self):
        cpp_file_content = CppProgramStrs.RETURN_ONLY_TEMPLATE.format(42)
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        self.sandbox.copy_into_sandbox(self.cpp_filename)

        self.test_case_starter.validate_and_save()
        result = self.test_case_starter.run(
            submission=None, autograder_sandbox=self.sandbox)

        self.assertTrue(result.compilation_succeeded)

    def test_compilation_failure(self):
        with open(self.cpp_filename, 'w') as f:
            f.write(CppProgramStrs.COMPILE_ERROR)

        self.sandbox.copy_into_sandbox(self.cpp_filename)

        self.test_case_starter.validate_and_save()
        result = self.test_case_starter.run(
            submission=None, autograder_sandbox=self.sandbox)

        self.assertFalse(result.compilation_succeeded)
