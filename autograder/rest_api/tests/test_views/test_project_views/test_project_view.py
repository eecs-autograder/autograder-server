from django.core.urlresolvers import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut


class _ProjectSetUp:
    def setUp(self):
        super().setUp()

        self.client = APIClient()

        self.course = obj_ut.build_course()

        self.admin = obj_ut.create_dummy_user()
        self.course.administrators.add(self.admin)

        self.staff = obj_ut.create_dummy_user()
        self.course.staff.add(self.staff)

        self.enrolled = obj_ut.create_dummy_user()
        self.course.enrolled_students.add(self.enrolled)

        self.nobody = obj_ut.create_dummy_user()

        self.project = ag_models.Project.objects.validate_and_create(
            name='spammy', course=self.course)
        self.url = reverse('project-detail', kwargs={'pk': self.project.pk})


class RetrieveProjectTestCase(_ProjectSetUp, TemporaryFilesystemTestCase):
    def test_admin_get_project(self):
        self.do_valid_load_project_test(self.admin)

    def test_staff_get_project(self):
        self.do_valid_load_project_test(self.staff)

    def test_student_get_visible_project(self):
        self.project.validate_and_update(visible_to_students=True)
        self.do_valid_load_project_test(self.enrolled)

    def test_other_get_visible_public_project(self):
        self.project.validate_and_update(
            visible_to_students=True,
            allow_submissions_from_non_enrolled_students=True)
        self.do_valid_load_project_test(self.nobody)

    def test_student_get_hidden_project_permission_denied(self):
        self.project.validate_and_update(
            visible_to_students=False,
            allow_submissions_from_non_enrolled_students=True)
        self.do_permission_denied_test(self.enrolled)

    def test_other_get_hidden_public_project_permission_denied(self):
        self.project.validate_and_update(
            visible_to_students=False,
            allow_submissions_from_non_enrolled_students=True)
        self.do_permission_denied_test(self.nobody)

    def test_other_get_non_public_project_permission_denied(self):
        self.project.validate_and_update(
            visible_to_students=True,
            allow_submissions_from_non_enrolled_students=False)
        self.do_permission_denied_test(self.nobody)

    def do_valid_load_project_test(self, user):
        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self.project.to_dict(), response.data)

    def do_permission_denied_test(self, user):
        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class UpdateProjectTestCase(_ProjectSetUp, TemporaryFilesystemTestCase):
    def test_admin_edit_project(self):
        args = {
            'name': 'waaaaa',
            'min_group_size': 4,
            'max_group_size': 5
        }

        self.client.force_authenticate(self.admin)
        response = self.client.patch(self.url, args)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        self.project.refresh_from_db()
        self.assertEqual(self.project.to_dict(), response.data)

        for arg_name, value in args.items():
            self.assertEqual(value, getattr(self.project, arg_name))

    def test_edit_project_invalid_settings(self):
        args = {
            'min_group_size': self.project.min_group_size + 2,
            'max_group_size': self.project.max_group_size + 1
        }

        self.client.force_authenticate(self.admin)
        response = self.client.patch(self.url, args)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        self.project.refresh_from_db()
        for arg_name, value in args.items():
            self.assertNotEqual(value, getattr(self.project, arg_name))

    def test_non_admin_edit_project_permission_denied(self):
        original_name = self.project.name
        for user in self.staff, self.enrolled, self.nobody:
            self.client.force_authenticate(user)
            response = self.client.patch(self.url, {'name': 'steve'})
            self.assertEqual(403, response.status_code)

            self.project.refresh_from_db()
            self.assertEqual(original_name, self.project.name)
