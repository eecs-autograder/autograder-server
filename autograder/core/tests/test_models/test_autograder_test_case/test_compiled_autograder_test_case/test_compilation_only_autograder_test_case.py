from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from .utils import (
    SharedSetUpTearDownForRunTestsWithCompilation,
    CppProgramStrs)


class CompilationOnlyAutograderTestRunTestCase(
        SharedSetUpTearDownForRunTestsWithCompilation,
        TemporaryFilesystemTestCase):

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

        self.assertTrue(result.compilation_succeeded)

    def test_compilation_failure(self):
        with open(self.main_file.abspath, 'w') as f:
            f.write(CppProgramStrs.COMPILE_ERROR)

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)

        self.assertFalse(result.compilation_succeeded)
