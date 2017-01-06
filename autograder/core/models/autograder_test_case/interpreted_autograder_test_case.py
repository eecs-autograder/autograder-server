from django.core import exceptions

from .autograder_test_case_base import AutograderTestCaseBase
from .autograder_test_case_result import AutograderTestCaseResult


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

    def run(self, submission, autograder_sandbox):
        print('running test: ' + self.name)
        result = AutograderTestCaseResult.objects.get(
            test_case=self, submission=submission)
        run_program_cmd = (
            [self.interpreter] + self.interpreter_flags +
            [self.entry_point_filename] + self.command_line_arguments)

        self.add_needed_files_to_sandbox(submission, autograder_sandbox)

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

        return result
