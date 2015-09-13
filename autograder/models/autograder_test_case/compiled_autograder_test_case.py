from django.core.exceptions import ValidationError

from autograder.models.utils import PolymorphicManagerWithValidateOnCreate

from ..autograder_test_case_result import AutograderTestCaseResultBase

from .autograder_test_case_base import AutograderTestCaseBase


class CompiledAutograderTestCase(AutograderTestCaseBase):
    """
    This class allows evaluating a program that will be compiled
    and then run.

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

        errors.update(self._clean_compiler())
        errors.update(self._clean_compiler_flags())
        errors.update(self._clean_files_to_compile_together())
        errors.update(self._clean_executable_name())

        if errors:
            raise ValidationError(errors)

    def test_checks_compilation(self):
        return True

    def get_type_str(self):
        return 'compiled_test_case'

    # -------------------------------------------------------------------------

    def run(self, submission, autograder_sandbox):
        print('running test: ' + self.name)
        result = AutograderTestCaseResultBase(test_case=self)

        # result is modified by reference in this function
        self._compile_program(submission, result, autograder_sandbox)

        if result.compilation_return_code != 0 or result.timed_out:
            # print(result._compilation_return_code)
            # print(runner.stderr)
            return result

        run_program_cmd = (
            ['./' + self.executable_name] + self.command_line_arguments
        )

        runner = autograder_sandbox.run_cmd(
            run_program_cmd, timeout=self.time_limit,
            stdin_content=self.standard_input)

        result.return_code = runner.return_code
        result.standard_output = runner.stdout
        result.standard_error_output = runner.stderr
        result.timed_out = runner.timed_out

        if not self.use_valgrind:
            return result

        valgrind_run_cmd = ['valgrind'] + self.valgrind_flags + run_program_cmd

        runner = autograder_sandbox.run_cmd(
            valgrind_run_cmd, timeout=self.time_limit,
            stdin_content=self.standard_input)

        result.valgrind_return_code = runner.return_code
        result.valgrind_output = runner.stderr

        return result
