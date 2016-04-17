# import uuid

from django.core import exceptions

# from django.core.validators import (
#     MinValueValidator, MaxValueValidator, RegexValidator)

# from autograder.core.models.utils import PolymorphicManagerWithValidateOnCreate

from .autograder_test_case_base import AutograderTestCaseBase

# import autograder.utilities.fields as ag_fields
# import autograder.core.shared.global_constants as gc
# import autograder.core.shared.utilities as ut
# import autograder.core.shared.feedback_configuration as fbc

# from autograder.core.tests.temporary_filesystem_test_case import (
#     TemporaryFilesystemTestCase)


class CompiledAutograderTestCase(AutograderTestCaseBase):
    """
    This class allows evaluating a program that will be compiled
    and then run.

    Field changes:
        compiler -- This field is REQUIRED
    """
    class Meta:
        proxy = True

    # Fat interface fields
    # compiler = ag_fields.ShortStringField(
    #     choices=zip(gc.SUPPORTED_COMPILERS, gc.SUPPORTED_COMPILERS))

    # compiler_flags = ag_fields.StringArrayField(
    #     default=list, blank=True, string_validators=[
    #         RegexValidator(gc.COMMAND_LINE_ARG_WHITELIST_REGEX)],
    #     )

    # project_files_to_compile_together = ag_fields.StringArrayField(
    #     default=list, blank=True, strip_strings=False)

    # student_files_to_compile_together = ag_fields.StringArrayField(
    #     default=list, blank=True, strip_strings=False)

    # executable_name = ag_fields.ShortStringField(
    #     validators=[ut.check_user_provided_filename],
    #     default="compiled_program")

    def test_checks_compilation(self):
        return True

    def clean(self):
        if not self.compiler:
            raise exceptions.ValidationError(
                {'compiler': 'The "compiler" field must be '
                             'specified for this AG test type'})
    #     errors = {}

    #     try:
    #         super().clean()
    #     except ValidationError as e:
    #         errors = e.message_dict

    #     errors.update(self._clean_project_files_to_compile_together())
    #     errors.update(self._clean_student_files_to_compile_together())

    #     if errors:
    #         raise ValidationError(errors)

    # def _clean_project_files_to_compile_together(self):
    #     errors = []
    #     for filename in self.project_files_to_compile_together:
    #         if filename not in self.test_resource_files:
    #             errors.append(
    #                 'File {0} not a resource file for this test'.format(
    #                     filename))

    #     if errors:
    #         return {'project_files_to_compile_together': errors}

    #     return {}

    # def _clean_student_files_to_compile_together(self):
    #     errors = []
    #     for filename in self.student_files_to_compile_together:
    #         if filename not in self.student_resource_files:
    #             errors.append(
    #                 'File {0} not a resource file for this test'.format(
    #                     filename))

    #     if errors:
    #         return {'student_files_to_compile_together': errors}

    #     return {}

    # -------------------------------------------------------------------------

    def _compile_program(self, submission, result_ref, autograder_sandbox):
        compilation_command = (
            [self.compiler] + self.compiler_flags +
            self.project_files_to_compile_together +
            self.student_files_to_compile_together
        )

        if self.compiler == 'g++' and self.executable_name:
            compilation_command += ['-o', self.executable_name]

        compile_result = autograder_sandbox.run_command(
            compilation_command, timeout=self.time_limit)
        result_ref.submission = submission
        result_ref.compilation_standard_output = compile_result.stdout
        result_ref.compilation_standard_error_output = compile_result.stderr
        result_ref.compilation_return_code = compile_result.return_code

    # -------------------------------------------------------------------------

    # def to_dict(self):
    #     value = super().to_dict()
    #     value.update({
    #         "compiler": self.compiler,
    #         "compiler_flags": self.compiler_flags,
    #         "project_files_to_compile_together": self.project_files_to_compile_together,
    #         "student_files_to_compile_together": self.student_files_to_compile_together,
    #         "executable_name": self.executable_name,
    #     })
    #     return value
