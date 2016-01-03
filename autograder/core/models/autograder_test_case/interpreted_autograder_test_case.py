from django.core.validators import RegexValidator

from autograder.core.models.utils import PolymorphicManagerWithValidateOnCreate
from django.core import exceptions

from autograder.utilities import fields as ag_fields

import autograder.core.shared.global_constants as gc
from .autograder_test_case_base import AutograderTestCaseBase
from ..autograder_test_case_result import AutograderTestCaseResult


class InterpretedAutograderTestCase(AutograderTestCaseBase):
    """
    This class evaluates a program by using an interpreter to run it.

    Fields:
        interpreter -- The interpreter used to run the program. Currently
            supported values listed in
            autograder.shared.global_constants.SUPPORTED_INTERPRETERS
            This field is REQUIRED.

        interpreter_flags -- A list of objtion flags to be passed to the
            interpreter. These flags are limited to the same character set
            as the command_line_argument_field.
            Default value: empty list

        entry_point_filename -- The name of a file that should be given
            to the interpreter as the program to be run, i.e. the main
            source module.
            This field is restricted to filenames listed in
            self.test_resource_files and self.student_resource_files.
            This field is REQUIRED.

    Overridden methods:
        run()
        to_dict()
        get_type_str()
        clean()
    """
    objects = PolymorphicManagerWithValidateOnCreate()

    interpreter = ag_fields.ShortStringField(
        choices=zip(gc.SUPPORTED_INTERPRETERS, gc.SUPPORTED_INTERPRETERS))

    interpreter_flags = ag_fields.StringArrayField(
        blank=True, default=list,
        string_validators=[
            RegexValidator(gc.COMMAND_LINE_ARG_WHITELIST_REGEX)])

    entry_point_filename = ag_fields.ShortStringField()

    # -------------------------------------------------------------------------

    def run(self, submission, autograder_sandbox):
        print('running test: ' + self.name)
        result = AutograderTestCaseResult(
            test_case=self, submission=submission)
        run_program_cmd = (
            [self.interpreter] + self.interpreter_flags +
            [self.entry_point_filename])

        runner = autograder_sandbox.run_cmd_with_redirected_io(
            run_program_cmd, timeout=self.time_limit,
            stdin_content=self.standard_input)

        result.return_code = runner.return_code
        result.standard_output = runner.stdout
        result.standard_error_output = runner.stderr
        result.timed_out = runner.timed_out

        return result

    def get_type_str(self):
        return 'interpreted_test_case'

    def clean(self):
        super().clean()

        if (self.entry_point_filename not in self.student_resource_files and
                self.entry_point_filename not in self.test_resource_files):
            raise exceptions.ValidationError(
                {'entry_point_filename':
                    '{} is not a resource file for this test'.format(
                        self.entry_point_filename)})

    def to_dict(self):
        result = super().to_dict()
        result.update({
            'interpreter': self.interpreter,
            'interpreter_flags': self.interpreter_flags,
            'entry_point_filename': self.entry_point_filename,
        })
        return result
