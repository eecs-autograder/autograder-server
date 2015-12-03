from .student_test_suite_base import StudentTestSuiteBase

from autograder.models.utils import (
    PolymorphicModelValidatableOnSave, PolymorphicManagerWithValidateOnCreate,
    filename_matches_any_pattern)


class CompiledStudentTestSuite(StudentTestSuiteBase):
    """
    This class enables evaluating a suite of student test cases that
    are compiled and then run.

    This class does not define any new fields.

    Overridden methods:
        evaluate()
    """
    objects = PolymorphicManagerWithValidateOnCreate()
