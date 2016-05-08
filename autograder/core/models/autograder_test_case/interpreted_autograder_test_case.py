# from django.core.validators import RegexValidator

# from autograder.core.models.utils import PolymorphicManagerWithValidateOnCreate
from django.core import exceptions

# from autograder.utilities import fields as ag_fields

# import autograder.core.shared.global_constants as gc
from .autograder_test_case_base import AutograderTestCaseBase
from .autograder_test_case_result import AutograderTestCaseResult


class InterpretedAutograderTestCase(AutograderTestCaseBase):
    """
    This class evaluates a program run using an interpreter.
    """
    class Meta:
        proxy = True
    # objects = PolymorphicManagerWithValidateOnCreate()

    # interpreter = ag_fields.ShortStringField(
    #     choices=zip(gc.SUPPORTED_INTERPRETERS, gc.SUPPORTED_INTERPRETERS))

    # interpreter_flags = ag_fields.StringArrayField(
    #     blank=True, default=list,
    #     string_validators=[
    #         RegexValidator(gc.COMMAND_LINE_ARG_WHITELIST_REGEX)])

    # entry_point_filename = ag_fields.ShortStringField()

    # -------------------------------------------------------------------------

    def run(self, submission, autograder_sandbox):
        print('running test: ' + self.name)
        result = AutograderTestCaseResult(
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

    def get_type_str(self):
        return 'interpreted_test_case'

    # def clean(self):
    #     super().clean()

    #     if (self.entry_point_filename not in self.student_resource_files and
    #             self.entry_point_filename not in self.test_resource_files):
    #         raise exceptions.ValidationError(
    #             {'entry_point_filename':
    #                 '{} is not a resource file for this test'.format(
    #                     self.entry_point_filename)})

    # def to_dict(self):
    #     result = super().to_dict()
    #     result.update({
    #         'interpreter': self.interpreter,
    #         'interpreter_flags': self.interpreter_flags,
    #         'entry_point_filename': self.entry_point_filename,
    #     })
    #     return result
