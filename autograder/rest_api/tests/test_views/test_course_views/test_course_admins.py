import itertools

from django.core.urlresolvers import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.rest_api.serializers as ag_serializers

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut


class _AdminsSetUp:
    def setUp(self):
        super().setUp()

        self.client = APIClient()

        self.superuser = obj_ut.create_dummy_user()
        self.superuser.is_superuser = True
        self.superuser.save()

        self.course = obj_ut.build_course()

        self.url = reverse('course-admins-list',
                           kwargs={'course_pk': self.course.pk})


class ListCourseAdminsTestCase(_AdminsSetUp, TemporaryFilesystemTestCase):
    def test_superuser_or_admin_list_administrators(self):
        admins = obj_ut.create_dummy_users(3)
        self.course.administrators.add(*admins)

        expected_content = ag_serializers.UserSerializer(admins,
                                                         many=True).data

        for user in self.superuser, admins[0]:
            self.client.force_authenticate(user)

            response = self.client.get(self.url)

            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertCountEqual(expected_content, response.data)

    def test_other_list_administrators_permission_denied(self):
        nobody = obj_ut.create_dummy_user()

        self.client.force_authenticate(nobody)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class AddCourseAdminsTestCase(_AdminsSetUp, TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_superuser_or_admin_add_administrators(self):
        current_admins = obj_ut.create_dummy_users(2)
        self.course.administrators.add(*current_admins)
        new_admin_names = ['steve', 'stave', 'stove', 'stive']
        new_admins = obj_ut.create_dummy_users(2)

        for user in (self.superuser, current_admins[0]):
            self.assertEqual(len(current_admins),
                             self.course.administrators.count())

            self.client.force_authenticate(self.superuser)
            response = self.client.post(
                self.url,
                {'new_admins':
                    new_admin_names + [user.username for user in new_admins]})

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
        nobody = obj_ut.create_dummy_user()
        self.client.force_authenticate(nobody)

        new_admin_name = 'steve'
        response = self.client.post(self.url, {'new_admins': [new_admin_name]})

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual(0, self.course.administrators.count())


# class RemoveCourseAdminsTestCase(TemporaryFilesystemTestCase):
#     def test_superuser_or_admin_remove_single_administrators(self):
#         expected_content = {
#             "administrators": list(sorted([
#                 self.admin.username, self.admin2.username
#             ]))
#         }

#         iterable = zip(
#             [self.admin2, self.superuser],
#             [self.admin.username, self.admin2.username])
#         for user, admin_to_remove in iterable:
#             expected_content['administrators'].remove(admin_to_remove)

#             client = MockClient(user)
#             response = client.delete(
#                 self.course_admins_url, {'administrators': [admin_to_remove]})

#             self.assertEqual(200, response.status_code)

#             self.assertEqual(
#                 expected_content, json_load_bytes(response.content))

#     def test_remove_multiple_administrators(self):
#         client = MockClient(self.superuser)
#         response = client.delete(
#             self.course_admins_url,
#             {'administrators': [self.admin.username, self.admin2.username]})

#         self.assertEqual(200, response.status_code)

#         loaded = Course.objects.get(pk=self.course.pk)
#         self.assertCountEqual(loaded.administrators.all(), [])

#     def test_error_admin_remove_self_from_admin_list(self):
#         client = MockClient(self.admin)
#         response = client.delete(
#             self.course_admins_url,
#             {'administrators': [self.admin2.username, self.admin.username]})
#         self.assertEqual(400, response.status_code)

#         loaded = Course.objects.get(pk=self.course.pk)
#         self.assertCountEqual(
#             loaded.administrators.all(), [self.admin, self.admin2])

#     def test_other_remove_administrators_permission_denied(self):
#         client = MockClient(self.nobody)
#         response = client.delete(
#             self.course_admins_url,
#             {'administrators': [self.admin2.username, self.admin.username]})

#         self.assertEqual(403, response.status_code)

#         loaded = Course.objects.get(pk=self.course.pk)
#         self.assertCountEqual(
#             loaded.administrators.all(), [self.admin, self.admin2])


