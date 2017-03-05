import subprocess
from typing import Union

from .compiled_autograder_test_case import CompiledAutograderTestCase

from ..autograder_test_case_result import AutograderTestCaseResult

from autograder_sandbox import AutograderSandbox


class CompiledAndRunAutograderTestCase(CompiledAutograderTestCase):
    """
    This class evaluates a program by compiling it from source code and
    then running it.

    Overridden methods:
        run()
    """
    class Meta:
        proxy = True

    @property
    def type_str(self):
        return 'compiled_and_run_test_case'

    def run(self, submission, autograder_sandbox: AutograderSandbox):
        print('running test: ' + self.name)

        self.add_needed_files_to_sandbox(submission, autograder_sandbox)

        result = AutograderTestCaseResult.objects.get(
            test_case=self, submission=submission)

        # result is modified by reference in this function call
        self._compile_program(submission, result, autograder_sandbox)

        if result.compilation_return_code != 0 or result.timed_out:
            return result

        run_program_cmd = (
            ['./' + self.executable_name] + self.command_line_arguments
        )

        try:
            run_result = autograder_sandbox.run_command(
                run_program_cmd,
                timeout=self.time_limit,
                max_num_processes=self.process_spawn_limit,
                max_stack_size=self.stack_size_limit,
                max_virtual_memory=self.virtual_memory_limit,
                input=self.standard_input)

            result.return_code = run_result.returncode
            result.standard_output = run_result.stdout
            result.standard_error_output = run_result.stderr
        except subprocess.TimeoutExpired as run_result:
            result.timed_out = True
            result.standard_output = run_result.stdout
            result.standard_error_output = run_result.stderr

        if not self.use_valgrind:
            return result

        valgrind_run_cmd = ['valgrind'] + self.valgrind_flags + run_program_cmd

        try:
            run_result = autograder_sandbox.run_command(
                valgrind_run_cmd,
                timeout=self.time_limit,
                max_num_processes=self.process_spawn_limit,
                max_stack_size=self.stack_size_limit,
                max_virtual_memory=self.virtual_memory_limit,
                input=self.standard_input)

            result.valgrind_return_code = run_result.returncode
            result.valgrind_output = run_result.stderr
        except subprocess.TimeoutExpired as run_result:
            result.valgrind_output = run_result.stderr

        return result
