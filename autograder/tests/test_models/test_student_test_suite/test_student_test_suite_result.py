from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.tests.dummy_object_utils as obj_ut


class _SharedSetUp(TemporaryFilesystemTestCase):
    def setUp(self):
        self.project = obj_ut.build_project({

        })


class StudentTestSuiteResultTestCase(TemporaryFilesystemTestCase):
    def test_valid_initialization_with_defaults(self):
        self.fail()

    def test_valid_initialization_no_defaults(self):
        self.fail()


class StudentTestSuiteResultSerializerTestCase(TemporaryFilesystemTestCase):
    def test_to_json_low_feedback(self):
        self.fail()

    def test_to_json_medium_feedback(self):
        self.fail()

    def test_to_json_full_feedback(self):
        self.fail()

    def test_to_json_with_submission_no_feedback_override(self):
        self.fail()

    def test_to_json_with_submission_feedback_override(self):
        self.fail()

    def test_to_json_with_manual_feedback_override(self):
        self.fail()

    def test_to_json_with_submission_and_manual_feedback_override(self):
        self.fail()
