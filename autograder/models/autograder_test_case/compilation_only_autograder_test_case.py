from django.core.exceptions import ValidationError

from autograder.models import AutograderTestCaseResultBase
from autograder.models.utils import PolymorphicManagerWithValidateOnCreate

from .autograder_test_case_base import AutograderTestCaseBase


class CompilationOnlyAutograderTestCase(AutograderTestCaseBase):
    """
    This class defines a type of test case that involves compiling
    a program but not running it.

    This class does not define any new fields.
    Instead, the following fields inherited from the base class
    are now REQUIRED:
        compiler
        compiler_flags (This field is allowed to be empty)
        files_to_compile_together

    Overridden methods:
        clean()
        test_checks_compilation()
        get_type_str()
        run()
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

        if errors:
            raise ValidationError(errors)

    def test_checks_compilation(self):
        return True

    def get_type_str(self):
        return 'compilation_only_test_case'

    # -------------------------------------------------------------------------

    def run(self, submission):
        result = AutograderTestCaseResultBase(test_case=self)
        self._compile_program(submission, result)

        return result
