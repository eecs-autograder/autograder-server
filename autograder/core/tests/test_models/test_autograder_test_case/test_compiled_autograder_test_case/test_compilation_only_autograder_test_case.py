from autograder.utils.testing import UnitTestBase

from .helpers import (
    SharedSetUpTearDownForRunTestsWithCompilation,
    CppProgramStrs)


class CompilationOnlyAutograderTestRunTestCase(
        SharedSetUpTearDownForRunTestsWithCompilation,
        UnitTestBase):

    def get_ag_test_type_str_for_factory(self):
        return 'compilation_only_test_case'

    def test_to_dict(self):
        self.assertTrue(self.test_case_starter.to_dict())

    def test_compilation_success(self):
        cpp_file_content = CppProgramStrs.RETURN_ONLY_TEMPLATE.format(42)
        with open(self.main_file.abspath, 'w') as f:
            f.write(cpp_file_content)

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)

        self.assertEqual(0, result.compilation_return_code)

    def test_compilation_failure(self):
        with open(self.main_file.abspath, 'w') as f:
            f.write(CppProgramStrs.COMPILE_ERROR)

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)

        self.assertNotEqual(0, result.compilation_return_code)

    def test_shell_injection_compiler_flags_does_not_work(self):
        with open(self.main_file.abspath, 'w') as f:
            f.write(CppProgramStrs.PRINT_CMD_ARGS)

        self.test_case_starter.validate_and_update(
            compiler_flags=['; echo "Hacked!"#'])

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)

        self.assertNotEqual(result.compilation_return_code, 0)
        self.assertNotEqual(result.compilation_standard_error_output, '')
