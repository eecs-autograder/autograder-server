from .shared_tests_and_setup import StudentTestSuiteBaseTests

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.tests.dummy_object_utils as obj_ut


class StudentTestSuiteResultTestCase(TemporaryFilesystemTestCase):
    def test_valid_initialization_with_defaults(self):
        self.fail()

    def test_valid_initialization_no_defaults(self):
        self.fail()
