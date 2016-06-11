from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from rest_framework import status
from rest_framework.test import APIClient

import autograder.rest_api.serializers as ag_serializers

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut


class _StaffSetUp:
    def setUp(self):
        super().setUp()

        self.client = APIClient()

        self.course = obj_ut.build_course()

        self.admin = obj_ut.create_dummy_user()
        self.course.administrators.add(self.admin)

        self.enrolled = obj_ut.create_dummy_user()
        self.course.enrolled_students.add(self.enrolled)

        self.nobody = obj_ut.create_dummy_user()

        self.url = reverse('course-staff-list',
                           kwargs={'course_pk': self.course.pk})


class ListStaffTestCase(_StaffSetUp, TemporaryFilesystemTestCase):
    def test_admin_or_staff_list_staff(self):
        staff = obj_ut.create_dummy_users(3)
        self.course.staff.add(*staff)

        expected_content = ag_serializers.UserSerializer(staff, many=True).data

        for user in self.admin, staff[0]:
            self.client.force_authenticate(user)

            response = self.client.get(self.url)

            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertCountEqual(expected_content, response.data)

    def test_other_list_staff_permission_denied(self):
        for user in self.enrolled, self.nobody:
            self.client.force_authenticate(user)

            response = self.client.get(self.url)
            self.assertEqual(403, response.status_code)


class AddStaffTestCase(_StaffSetUp, TemporaryFilesystemTestCase):
    def test_admin_add_staff(self):
        current_staff = obj_ut.create_dummy_users(2)
        self.course.staff.add(*current_staff)

        new_staff_names = ['staffy1', 'staffy2']
        new_staff = obj_ut.create_dummy_users(2)

        self.assertEqual(len(current_staff), self.course.staff.count())

        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.url,
            {'new_staff':
                new_staff_names + [user.username for user in new_staff]})
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

        created_staff = [
            User.objects.get(username=username)
            for username in new_staff_names]

        self.assertCountEqual(current_staff + created_staff + new_staff,
                              self.course.staff.all())

    def test_other_add_staff_permission_denied(self):
        current_staff = obj_ut.create_dummy_user()
        self.course.staff.add(current_staff)

        for user in current_staff, self.enrolled, self.nobody:
            self.client.force_authenticate(user)
            response = self.client.post(
                self.url, {'new_staff': ['spam', 'steve']})

            self.assertEqual(403, response.status_code)

            self.assertCountEqual([current_staff],
                                  self.course.staff.all())


class RemoveStaffTestCase(_StaffSetUp, TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.remaining_staff = obj_ut.create_dummy_user()
        self.current_staff = obj_ut.create_dummy_users(3)
        self.all_staff = [self.remaining_staff] + self.current_staff
        self.total_num_staff = len(self.all_staff)

        self.course.staff.add(*self.all_staff)

        self.request_body = {
            'remove_staff': [user.username for user in self.current_staff]
        }

    def test_admin_remove_staff(self):
        self.client.force_authenticate(self.admin)

        response = self.client.delete(self.url, self.request_body)
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

        self.assertCountEqual([self.remaining_staff],
                              self.course.staff.all())

    def test_other_remove_staff_permission_denied(self):
        for user in self.remaining_staff, self.enrolled, self.nobody:
            self.assertEqual(self.total_num_staff,
                             self.course.staff.count())

            self.client.force_authenticate(user)
            response = self.client.delete(self.url, self.request_body)
            self.assertEqual(403, response.status_code)

            self.assertCountEqual(self.all_staff, self.course.staff.all())

            self.course.staff.add(*self.current_staff)
