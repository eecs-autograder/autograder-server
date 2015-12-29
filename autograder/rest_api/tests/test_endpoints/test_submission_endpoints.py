import itertools

from django.core.urlresolvers import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.core.models import Submission
from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk


def _common_set_up(fixture):
    fixture.admin = obj_ut.create_dummy_user()
    fixture.staff = obj_ut.create_dummy_user()
    fixture.enrolled = obj_ut.create_dummy_user()
    fixture.nobody = obj_ut.create_dummy_user()

    fixture.project = obj_ut.build_project(
        course_kwargs={'administrators': [fixture.admin]},
        semester_kwargs={
            'staff': [fixture.staff], 'enrolled_students': [fixture.enrolled]},
        project_kwargs={'allow_submissions_from_non_enrolled_students': True})

    fixture.semester = fixture.project.semester
    fixture.course = fixture.semester.course

    fixture.admin.courses_is_admin_for.add(fixture.course)
    fixture.staff.semesters_is_staff_for.add(fixture.semester)
    fixture.enrolled.semesters_is_enrolled_in.add(fixture.semester)

    fixture.visible_project = obj_ut.build_project(
        project_kwargs={'semester': fixture.semester,
                        'visible_to_students': True,
                        'allow_submissions_from_non_enrolled_students': True})

    fixture.course_url = reverse(
        'course:get', kwargs={'pk': fixture.course.pk})

    fixture.semester_url = reverse(
        'semester:get', kwargs={'pk': fixture.semester.pk})
    fixture.staff_url = reverse(
        'semester:staff', kwargs={'pk': fixture.semester.pk})
    fixture.enrolled_url = reverse(
        'semester:enrolled_students', kwargs={'pk': fixture.semester.pk})
    fixture.projects_url = reverse(
        'semester:projects', kwargs={'pk': fixture.semester.pk})

    fixture.project_url = reverse(
        'project:get', kwargs={'pk': fixture.project.pk})

    fixture.admin_group_obj = _make_group_obj(
        fixture.admin, fixture.visible_project)
    fixture.staff_group_obj = _make_group_obj(
        fixture.staff, fixture.visible_project)
    fixture.enrolled_group_obj = _make_group_obj(
        fixture.enrolled, fixture.visible_project)
    fixture.nobody_group_obj = _make_group_obj(
        fixture.nobody, fixture.visible_project)

    fixture.users_and_groups_visible_proj = [
        fixture.admin_group_obj, fixture.staff_group_obj,
        fixture.enrolled_group_obj, fixture.nobody_group_obj
    ]

    fixture.users_and_groups_hidden_proj = [
        _make_group_obj(user, fixture.project)
        for user in (fixture.admin, fixture.staff,
                     fixture.enrolled, fixture.nobody)
    ]


def _make_group_obj(user, project):
    obj = {
        'user': user,
        'group': SubmissionGroup.objects.validate_and_create(
            members=[user.username], project=project),
    }
    obj['url'] = reverse('group:get', kwargs={'pk': obj['group'].pk})
    return obj


_SUBMISSION_FILES = [
    SimpleUploadedFile('file1.cpp', b'blah'),
    SimpleUploadedFile('file2.cpp', b'blee'),
    SimpleUploadedFile('file3.cpp', b'bloo'),
]

_SUBMISSION_FILENAMES = [file_.name for file_ in _SUBMISSION_FILES]


class GetSubmissionTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_valid_user_get_own_submission(self):
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
