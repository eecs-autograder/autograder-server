from .shared_tests_and_setup import StudentTestSuiteBaseTests

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)


class CompiledStudentTestSuiteTestCase(
        StudentTestSuiteBaseTests, TemporaryFilesystemTestCase):

    # -------------------------------------------------------------------------

    def get_student_test_suite_type_str_for_factory(self):
        return 'compiled_student_test_suite'
