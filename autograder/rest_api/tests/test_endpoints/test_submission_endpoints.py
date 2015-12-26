import itertools

from django.core.urlresolvers import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.core.models import Submission
from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk

_SUBMISSION_FILES = [
    SimpleUploadedFile('file1.cpp', b'blah'),
    SimpleUploadedFile('file2.cpp', b'blee'),
    SimpleUploadedFile('file3.cpp', b'bloo'),
]

_SUBMISSION_FILENAMES = [file_.name for file_ in _SUBMISSION_FILES]


class GetSubmissionTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_valid_student_get_own_submission(self):
        group = obj_ut.build_submission_group(
            project_kwargs={'required_student_files': _SUBMISSION_FILENAMES})

        submission = Submission.objects.validate_and_create(
            submission_group=group)

        client = MockClient(self.group.members.all().first())
        response = client.get(reverse())

    def test_course_admin_or_semester_staff_get_student_submission(self):
        self.fail()

    def test_student_get_other_submission_permission_denied(self):
        self.fail()

    def test_student_get_submission_project_hidden_permission_denied(self):
        self.fail()

    def test_non_enrolled_student_non_public_project_get_submission_permission_denied(self):
        self.fail()

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListSubmittedFilesTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_valid_student_list_submitted_files(self):
        self.fail()

    def test_course_admin_or_semester_staff_list_student_submitted_files(self):
        self.fail()

    def test_student_list_other_submitted_files_permission_denied(self):
        self.fail()

    def test_student_list_submitted_files_project_hidden_permission_denied(self):
        self.fail()

    def test_non_enrolled_student_non_public_project_list_submitted_files_permission_denied(self):
        self.fail()

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAutograderTestCaseResultsTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    # cross check with test_submission_request_handlers.py

    def test_valid_student_list_test_case_results(self):
        # make sure only results from visible tests are listed
        self.fail()

    def test_course_admin_or_semester_staff_get_student_results(self):
        # should only see visible tests
        self.fail()

    def test_course_admin_or_semester_staff_get_own_results(self):
        # should see all test cases
        self.fail()

    def test_student_list_other_student_results_permission_denied(self):
        self.fail()

    def test_student_list_own_results_project_hidden_permission_denied(self):
        self.fail()

    def test_non_enrolled_student_non_public_project_list_results_permission_denied(self):
        self.fail()

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListStudentTestSuiteResultsTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    # cross check with test_submission_request_handlers.py

    def test_valid_student_list_test_case_results(self):
        # make sure only results from visible tests are listed
        self.fail()

    def test_course_admin_or_semester_staff_get_student_results(self):
        # should only see visible tests
        self.fail()

    def test_course_admin_or_semester_staff_get_own_results(self):
        # should see all test cases
        self.fail()

    def test_student_list_other_student_results_permission_denied(self):
        self.fail()

    def test_student_list_own_results_project_hidden_permission_denied(self):
        self.fail()

    def test_non_enrolled_student_non_public_project_list_results_permission_denied(self):
        self.fail()
