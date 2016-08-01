from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from rest_framework import status

import autograder.rest_api.serializers as ag_serializers

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.rest_api.tests.test_views.common_generic_data as test_data


class _StaffSetUp(test_data.Client, test_data.Course):
    def setUp(self):
        super().setUp()
        self.url = reverse('course-staff-list',
                           kwargs={'course_pk': self.course.pk})


class ListStaffTestCase(_StaffSetUp, UnitTestBase):
    def test_admin_or_staff_list_staff(self):
        staff = obj_build.create_dummy_users(3)
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


class AddStaffTestCase(_StaffSetUp, UnitTestBase):
    def test_admin_add_staff(self):
        current_staff = obj_build.create_dummy_users(2)
        self.course.staff.add(*current_staff)

        new_staff_names = (
            ['staffy1', 'staffy2'] +
            [user.username for user in obj_build.create_dummy_users(2)])

        self.assertEqual(len(current_staff), self.course.staff.count())

        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.url, {'new_staff': new_staff_names})
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

        new_staff = list(User.objects.filter(username__in=new_staff_names))

        self.assertCountEqual(current_staff + new_staff,
                              self.course.staff.all())

    def test_other_add_staff_permission_denied(self):
        current_staff = obj_build.create_dummy_user()
        self.course.staff.add(current_staff)

        for user in current_staff, self.enrolled, self.nobody:
            self.client.force_authenticate(user)
            response = self.client.post(
                self.url, {'new_staff': ['spam', 'steve']})

            self.assertEqual(403, response.status_code)

            self.assertCountEqual([current_staff],
                                  self.course.staff.all())


class RemoveStaffTestCase(_StaffSetUp, UnitTestBase):
    def setUp(self):
        super().setUp()

        self.remaining_staff = obj_build.create_dummy_user()
        self.staff_to_remove = obj_build.create_dummy_users(3)
        self.all_staff = [self.remaining_staff] + self.staff_to_remove
        self.total_num_staff = len(self.all_staff)

        self.course.staff.add(*self.all_staff)

        self.request_body = {
            'remove_staff': [user.username for user in self.staff_to_remove]
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

            self.course.staff.add(*self.staff_to_remove)
