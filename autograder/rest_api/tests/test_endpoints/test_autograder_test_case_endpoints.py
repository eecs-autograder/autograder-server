import itertools

from django.core.urlresolvers import reverse

from autograder.core.models import (
    AutograderTestCaseFactory, AutograderTestCaseBase)

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk


class GetUpdateDeleteAutograderTestCaseTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.admin = obj_ut.create_dummy_user()
        self.staff = obj_ut.create_dummy_user()
        self.enrolled = obj_ut.create_dummy_user()
        self.nobody = obj_ut.create_dummy_user()

        self.required_filenames = ['spam', 'egg']

        self.project = obj_ut.build_project(
            course_kwargs={'administrators': [self.admin]},
            semester_kwargs={
                'staff': [self.staff], 'enrolled_students': [self.enrolled]},
            project_kwargs={
                'allow_submissions_from_non_enrolled_students': True,
                'visible_to_students': True,
                'required_student_files': self.required_filenames})

        self.semester = self.project.semester
        self.course = self.semester.course

        self.project_url = reverse(
            'project:get', kwargs={'pk': self.project.pk})

        # self.test_case =

    def test_course_admin_or_semester_staff_get_test_case(self):
        self.fail()

    def test_other_get_test_case_permission_denied(self):
        self.fail()

    def test_course_admin_get_test_case_not_found(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_course_admin_edit_test_case(self):
        self.fail()

    def test_course_admin_edit_test_case_invalid_settings(self):
        self.fail()

    def test_other_edit_test_case_permission_denied(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_course_admin_delete_test_case(self):
        self.fail()

    def test_other_delete_test_case_permission_denied(self):
        self.fail()
