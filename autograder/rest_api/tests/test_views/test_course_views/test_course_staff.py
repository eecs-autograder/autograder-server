from django.urls import reverse
from django.contrib.auth.models import User

from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class _SetUp(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.course = obj_build.make_course()
        self.client = APIClient()
        self.url = reverse('course-staff', kwargs={'pk': self.course.pk})

        [self.admin] = obj_build.make_admin_users(self.course, 1)
        [self.student] = obj_build.make_student_users(self.course, 1)
        [self.guest] = obj_build.make_users(1)
        [self.handgrader] = obj_build.make_handgrader_users(self.course, 1)


class ListStaffTestCase(_SetUp):
    def test_admin_or_staff_or_handgrader_list_staff(self):
        staff = obj_build.create_dummy_users(3)
        self.course.staff.add(*staff)

        expected_content = ag_serializers.UserSerializer(staff, many=True).data

        for user in self.admin, staff[0], self.handgrader:
            self.client.force_authenticate(user)

            response = self.client.get(self.url)

            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertCountEqual(expected_content, response.data)

    def test_other_list_staff_permission_denied(self):
        for user in self.student, self.guest:
            self.client.force_authenticate(user)

            response = self.client.get(self.url)
            self.assertEqual(403, response.status_code)


class AddStaffTestCase(_SetUp):
    def test_admin_add_staff(self):
        current_staff = obj_build.create_dummy_users(2)
        self.course.staff.add(*current_staff)

        new_staff_users = obj_build.make_users(2)
        new_staff_names = ['staffy1', 'staffy2'] + [user.username for user in new_staff_users]

        # Make sure cache invalidation happens
        self.assertFalse(self.course.is_staff(new_staff_users[0]))

        self.assertEqual(len(current_staff), self.course.staff.count())

        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.url, {'new_staff': new_staff_names})
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

        new_staff = list(User.objects.filter(username__in=new_staff_names))

        self.assertCountEqual(current_staff + new_staff, self.course.staff.all())

        # Reload to clear cached attribute
        self.course = ag_models.Course.objects.get(pk=self.course.pk)
        # Make sure cache invalidation happens
        self.assertTrue(self.course.is_staff(new_staff_users[0]))

    def test_other_add_staff_permission_denied(self):
        current_staff = obj_build.create_dummy_user()
        self.course.staff.add(current_staff)

        for user in current_staff, self.student, self.guest, self.handgrader:
            self.client.force_authenticate(user)
            response = self.client.post(
                self.url, {'new_staff': ['spam', 'steve']})

            self.assertEqual(403, response.status_code)

            self.assertCountEqual([current_staff],
                                  self.course.staff.all())

    def test_error_missing_request_param(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)


class RemoveStaffTestCase(_SetUp):
    def setUp(self):
        super().setUp()

        self.remaining_staff = obj_build.create_dummy_user()
        self.staff_to_remove = obj_build.create_dummy_users(3)
        self.all_staff = [self.remaining_staff] + self.staff_to_remove
        self.total_num_staff = len(self.all_staff)

        self.course.staff.add(*self.all_staff)

        self.request_body = {
            'remove_staff': ag_serializers.UserSerializer(
                self.staff_to_remove, many=True).data
        }

    def test_admin_remove_staff(self):
        # Make sure cache invalidation happens
        self.assertTrue(self.course.is_staff(self.staff_to_remove[0]))

        self.client.force_authenticate(self.admin)

        response = self.client.patch(self.url, self.request_body)
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

        self.assertCountEqual([self.remaining_staff],
                              self.course.staff.all())

        # Reload to clear cached attribute
        self.course = ag_models.Course.objects.get(pk=self.course.pk)
        # Make sure cache invalidation happens
        self.assertFalse(self.course.is_staff(self.staff_to_remove[0]))

    def test_other_remove_staff_permission_denied(self):
        for user in self.remaining_staff, self.student, self.guest, self.handgrader:
            self.assertEqual(self.total_num_staff,
                             self.course.staff.count())

            self.client.force_authenticate(user)
            response = self.client.patch(self.url, self.request_body)
            self.assertEqual(403, response.status_code)

            self.assertCountEqual(self.all_staff, self.course.staff.all())

            self.course.staff.add(*self.staff_to_remove)

    def test_error_missing_request_param(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(self.url, {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
