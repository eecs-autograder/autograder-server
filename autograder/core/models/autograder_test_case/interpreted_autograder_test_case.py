import subprocess

from django.core import exceptions

from .autograder_test_case_base import AutograderTestCaseBase
from .autograder_test_case_result import AutograderTestCaseResult

from autograder_sandbox import AutograderSandbox


class InterpretedAutograderTestCase(AutograderTestCaseBase):
    """
    This class evaluates a program run using an interpreter.
    """
    class Meta:
        proxy = True

    @property
    def type_str(self):
        return 'interpreted_test_case'

    def clean(self):
        if not self.interpreter:
            raise exceptions.ValidationError(
                {'interpreter': 'The "interpreter" field must be '
                                'specified for this AG test type'})

        if not self.entry_point_filename:
            raise exceptions.ValidationError(
                {'entry_point_filename': 'The "entry_point_filename" field '
                                         'cannot be empty for this AG test type.'})

    def run(self, submission, autograder_sandbox: AutograderSandbox):
        print('running test: ' + self.name)
        result = AutograderTestCaseResult.objects.get(
            test_case=self, submission=submission)
        run_program_cmd = (
            [self.interpreter] + self.interpreter_flags +
            [self.entry_point_filename] + self.command_line_arguments)

        self.add_needed_files_to_sandbox(submission, autograder_sandbox)

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

        return result
