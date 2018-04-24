from django.urls import reverse
from django.contrib.auth.models import User

from rest_framework import status
from rest_framework.test import APIClient

import autograder.rest_api.serializers as ag_serializers

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls


class _SetUp(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.course = obj_build.make_course()
        self.client = APIClient()
        self.url = reverse('course-students', kwargs={'pk': self.course.pk})

        [self.admin] = obj_build.make_admin_users(self.course, 1)
        [self.staff] = obj_build.make_staff_users(self.course, 1)
        [self.guest] = obj_build.make_users(1)


class ListStudentsTestCase(test_impls.ListObjectsTest, _SetUp):
    def setUp(self):
        super().setUp()

        self.students = obj_build.create_dummy_users(4)
        self.course.students.add(*self.students)

    # Note: As far as I can tell, making the list of enrolled students
    # visible to other enrolled students might be a FERPA violation.
    # Make sure you look into this if you ever decide to make this data
    # accessible to enrolled students (such as for autocomplete when
    # sending group invitations).
    def test_admin_or_staff_list_students(self):
        expected_content = ag_serializers.UserSerializer(
            self.students, many=True).data

        for user in self.staff, self.admin:
            self.do_list_objects_test(
                self.client, user, self.url, expected_content)

    def test_other_list_students_permission_denied(self):
        for user in self.students[0], self.guest:
            self.do_permission_denied_get_test(self.client, user, self.url)


class AddStudentsTestCase(_SetUp):
    def setUp(self):
        super().setUp()

        self.current_students = obj_build.create_dummy_users(2)
        self.course.students.add(*self.current_students)

    def test_admin_add_students(self):
        self.client.force_authenticate(self.admin)
        new_student_names = (
            ['steve', 'bill'] +
            [user.username for user in obj_build.create_dummy_users(3)])

        self.assertEqual(len(self.current_students), self.course.students.count())

        response = self.client.post(self.url, {'new_students': new_student_names})

        new_students = list(
            User.objects.filter(username__in=new_student_names))

        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
        self.assertCountEqual(new_students + self.current_students,
                              self.course.students.all())

    def test_other_add_students_permission_denied(self):
        for user in self.staff, self.current_students[0], self.guest:
            self.client.force_authenticate(user)
            response = self.client.post(self.url, {'new_students': ['steve']})
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

            self.assertCountEqual(self.current_students,
                                  self.course.students.all())

    def test_error_missing_request_param(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)


class UpdateStudentsTestCase(_SetUp):
    def setUp(self):
        super().setUp()

        self.current_students = obj_build.create_dummy_users(5)
        self.course.students.add(*self.current_students)

    def test_admin_update_students(self):
        new_roster = obj_build.create_dummy_users(3)
        self.client.force_authenticate(self.admin)

        response = self.client.put(
            self.url,
            {'new_students':
                [user.username for user in new_roster]})
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
        self.assertCountEqual(new_roster, self.course.students.all())

    def test_other_update_students_permission_denied(self):
        for user in self.staff, self.current_students[0], self.guest:
            self.client.force_authenticate(user)
            response = self.client.put(
                self.url,
                {'new_students':
                    [user.username for user in obj_build.create_dummy_users(2)]})
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
            self.assertCountEqual(self.current_students,
                                  self.course.students.all())

    def test_error_missing_request_param(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)


class RemoveStudentsTestCase(_SetUp):
    def setUp(self):
        super().setUp()

        self.remaining_students = obj_build.create_dummy_users(2)
        self.students_to_remove = obj_build.create_dummy_users(5)
        self.all_enrolled = self.remaining_students + self.students_to_remove
        self.total_num_enrolled = len(self.all_enrolled)

        self.course.students.add(*self.all_enrolled)

        self.request_body = {
            'remove_students':
                ag_serializers.UserSerializer(self.students_to_remove, many=True).data
        }

    def test_admin_remove_students(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(self.url, self.request_body)
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

        self.assertCountEqual(self.remaining_students,
                              self.course.students.all())

    def test_other_remove_students_permission_denied(self):
        for user in self.staff, self.remaining_students[0], self.guest:
            self.client.force_authenticate(user)
            response = self.client.patch(self.url, self.request_body)
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_error_missing_request_param(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
