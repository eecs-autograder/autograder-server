from ..autograder_test_case_result import AutograderTestCaseResult

from .compiled_autograder_test_case import CompiledAutograderTestCase

from autograder_sandbox import AutograderSandbox


class CompilationOnlyAutograderTestCase(CompiledAutograderTestCase):
    """
    This class evaulates a program by trying to compile it from source code.

    Overridden methods:
        clean()
        checks_compilation()
        get_type_str()
        run()
    """
    class Meta:
        proxy = True

    @property
    def type_str(self):
        return 'compilation_only_test_case'

    def run(self, submission, autograder_sandbox: AutograderSandbox):
        print('running test: ' + self.name)
        result = AutograderTestCaseResult.objects.get(
            test_case=self, submission=submission)
        self.add_needed_files_to_sandbox(submission, autograder_sandbox)
        self._compile_program(submission, result, autograder_sandbox)

        return result
