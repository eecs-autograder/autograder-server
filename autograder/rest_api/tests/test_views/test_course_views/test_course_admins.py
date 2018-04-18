import itertools

from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.rest_api.serializers as ag_serializers

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class _SetUp(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.course = obj_build.make_course()
        self.client = APIClient()
        self.url = reverse('course-admins', kwargs={'pk': self.course.pk})

        [self.superuser] = obj_build.make_users(1, superuser=True)
        [self.staff] = obj_build.make_staff_users(self.course, 1)
        [self.enrolled] = obj_build.make_enrolled_users(self.course, 1)
        [self.guest] = obj_build.make_users(1)


class ListCourseAdminsTestCase(_SetUp):
    def test_superuser_admin_or_staff_list_administrators(self):
        admins = obj_build.create_dummy_users(3)
        self.course.administrators.add(*admins)

        expected_content = ag_serializers.UserSerializer(admins,
                                                         many=True).data

        for user in self.superuser, admins[0], self.staff:
            self.client.force_authenticate(user)

            response = self.client.get(self.url)

            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertCountEqual(expected_content, response.data)

    def test_other_list_administrators_permission_denied(self):
        for user in self.guest, self.enrolled:
            self.client.force_authenticate(user)

            response = self.client.get(self.url)
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class AddCourseAdminsTestCase(_SetUp):
    def setUp(self):
        super().setUp()

    def test_superuser_or_admin_add_administrators(self):
        current_admins = obj_build.create_dummy_users(2)
        self.course.administrators.add(*current_admins)
        new_admin_names = ['steve', 'stave', 'stove', 'stive']
        new_admins = obj_build.create_dummy_users(2)

        for user in (self.superuser, current_admins[0]):
            self.assertEqual(len(current_admins),
                             self.course.administrators.count())

            self.client.force_authenticate(self.superuser)
            response = self.client.post(
                self.url,
                {'new_admins': new_admin_names + [user.username for user in new_admins]})

            self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

            expected_usernames = list(
                itertools.chain(
                    [user.username for user in current_admins],
                    new_admin_names,
                    [user.username for user in new_admins]))

            self.assertCountEqual(expected_usernames,
                                  self.course.administrator_names)

            self.course.administrators.set(current_admins, clear=True)

    def test_other_add_administrators_permission_denied(self):
        for user in self.staff, self.enrolled, self.guest:
            self.client.force_authenticate(user)

            new_admin_name = 'steve'
            response = self.client.post(self.url, {'new_admins': [new_admin_name]})

            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
            self.assertEqual(0, self.course.administrators.count())

    def test_error_missing_request_param(self):
        self.client.force_authenticate(self.superuser)
        response = self.client.post(self.url, {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)


class RemoveCourseAdminsTestCase(_SetUp):
    def setUp(self):
        super().setUp()

        self.remaining_admin = obj_build.create_dummy_user()
        self.current_admins = obj_build.create_dummy_users(3)
        self.all_admins = [self.remaining_admin] + self.current_admins
        self.total_num_admins = len(self.all_admins)

        self.course.administrators.add(*self.all_admins)

        self.request_body = {
            'remove_admins': ag_serializers.UserSerializer(
                self.current_admins, many=True).data
        }

    def test_superuser_or_admin_remove_admins(self):
        for user in self.superuser, self.remaining_admin:
            self.assertEqual(self.total_num_admins,
                             self.course.administrators.count())
            self.client.force_authenticate(user)

            response = self.client.patch(self.url, self.request_body)
            self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

            self.assertCountEqual([self.remaining_admin],
                                  self.course.administrators.all())

            self.course.administrators.add(*self.current_admins)

    def test_error_admin_remove_self_from_admin_list(self):
        self.client.force_authenticate(self.remaining_admin)
        response = self.client.patch(
            self.url,
            {'remove_admins':
                ag_serializers.UserSerializer([self.remaining_admin], many=True).data})

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        self.assertTrue(self.course.is_administrator(self.remaining_admin))

    def test_other_remove_administrators_permission_denied(self):
        for user in self.guest, self.enrolled, self.staff:
            self.client.force_authenticate(user)
            response = self.client.patch(self.url, self.request_body)

            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

            self.assertCountEqual(self.all_admins,
                                  self.course.administrators.all())

    def test_error_missing_request_param(self):
        self.client.force_authenticate(self.superuser)
        response = self.client.patch(self.url, {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
