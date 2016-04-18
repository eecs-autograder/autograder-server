from .compiled_autograder_test_case import CompiledAutograderTestCase

from ..autograder_test_case_result import AutograderTestCaseResult


class CompiledAndRunAutograderTestCase(CompiledAutograderTestCase):
    """
    This class evaluates a program by compiling it from source code and
    then running it.

    Overridden methods:
        run()
    """
    class Meta:
        proxy = True

    def run(self, submission, autograder_sandbox):
        print('running test: ' + self.name)
        result = AutograderTestCaseResult(
            test_case=self, submission=submission)

        # result is modified by reference in this function
        self._compile_program(submission, result, autograder_sandbox)

        if result.compilation_return_code != 0 or result.timed_out:
            # print(result._compilation_return_code)
            # print(runner.stderr)
            return result

        run_program_cmd = (
            ['./' + self.executable_name] + self.command_line_arguments
        )

        runner = autograder_sandbox.run_command(
            run_program_cmd,
            timeout=self.time_limit,
            max_num_processes=self.process_spawn_limit,
            max_stack_size=self.stack_size_limit,
            max_virtual_memory=self.virtual_memory_limit,
            input_content=self.standard_input)

        result.return_code = runner.return_code
        result.standard_output = runner.stdout
        result.standard_error_output = runner.stderr
        result.timed_out = runner.timed_out

        if not self.use_valgrind:
            return result

        valgrind_run_cmd = ['valgrind'] + self.valgrind_flags + run_program_cmd

        runner = autograder_sandbox.run_command(
            valgrind_run_cmd,
            timeout=self.time_limit,
            max_num_processes=self.process_spawn_limit,
            max_stack_size=self.stack_size_limit,
            max_virtual_memory=self.virtual_memory_limit,
            input_content=self.standard_input)

        result.valgrind_return_code = runner.return_code
        result.valgrind_output = runner.stderr

        return result

    # TODO: REMOVE, put the json api serializers in the model classes
    def get_type_str(self):
        return 'compiled_and_run_test_case'
