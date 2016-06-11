from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from rest_framework import status
from rest_framework.test import APIClient

import autograder.rest_api.serializers as ag_serializers

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut


class _EnrolledSetUp:
    def setUp(self):
        super().setUp()

        self.client = APIClient()

        self.course = obj_ut.build_course()

        self.admin = obj_ut.create_dummy_user()
        self.course.administrators.add(self.admin)

        self.staff = obj_ut.create_dummy_user()
        self.course.staff.add(self.staff)

        self.nobody = obj_ut.create_dummy_user()

        self.url = reverse('course-enrolled-students-list',
                           kwargs={'course_pk': self.course.pk})


class ListEnrolledStudentsTestCase(_EnrolledSetUp,
                                   TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.enrolled_students = obj_ut.create_dummy_users(4)
        self.course.enrolled_students.add(*self.enrolled_students)

    # Note: As far as I can tell, making the list of enrolled students
    # visible to other enrolled students might be a FERPA violation.
    # Make sure you look into this if you ever decide to make this data
    # accessible to enrolled students (such as for autocomplete when
    # sending group invitations).
    def test_admin_or_staff_list_students(self):
        expected_content = ag_serializers.UserSerializer(
            self.enrolled_students, many=True).data

        for user in self.staff, self.admin:
            self.client.force_authenticate(user)
            response = self.client.get(self.url)

            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertEqual(expected_content, response.data)

    def test_other_list_students_permission_denied(self):
        for user in self.enrolled_students[0], self.nobody:
            self.client.force_authenticate(user)
            response = self.client.get(self.url)
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class AddEnrolledStudentsTestCase(_EnrolledSetUp, TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.current_students = obj_ut.create_dummy_users(2)
        self.course.enrolled_students.add(*self.current_students)

    def test_admin_add_enrolled_students(self):
        self.client.force_authenticate(self.admin)
        new_student_names = (
            ['steve', 'bill'] +
            [user.username for user in obj_ut.create_dummy_users(3)])

        self.assertEqual(len(self.current_students),
                         self.course.enrolled_students.count())

        response = self.client.post(
            self.url,
            {'new_enrolled_students': new_student_names})

        new_students = list(
            User.objects.filter(username__in=new_student_names))

        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
        self.assertCountEqual(new_students + self.current_students,
                              self.course.enrolled_students.all())

    def test_other_add_enrolled_students_permission_denied(self):
        for user in self.staff, self.current_students[0], self.nobody:
            self.client.force_authenticate(user)
            response = self.client.post(
                self.url, {'new_enrolled_students': ['steve']})
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

            self.assertCountEqual(self.current_students,
                                  self.course.enrolled_students.all())


class UpdateEnrolledStudentsTestCase(_EnrolledSetUp,
                                     TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.current_students = obj_ut.create_dummy_users(5)
        self.course.enrolled_students.add(*self.current_students)

    def test_admin_update_enrolled_students(self):
        new_roster = obj_ut.create_dummy_users(3)
        self.client.force_authenticate(self.admin)

        response = self.client.put(
            self.url,
            {'new_enrolled_students':
                [user.username for user in new_roster]})
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
        self.assertCountEqual(new_roster, self.course.enrolled_students.all())

    def test_other_update_enrolled_students_permission_denied(self):
        for user in self.staff, self.current_students[0], self.nobody:
            self.client.force_authenticate(user)
            response = self.client.put(
                self.url,
                {'new_enrolled_students':
                    [user.username for user in obj_ut.create_dummy_users(2)]})
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
            self.assertCountEqual(self.current_students,
                                  self.course.enrolled_students.all())


class RemoveEnrolledStudentsTestCase(_EnrolledSetUp,
                                     TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.remaining_students = obj_ut.create_dummy_users(2)
        self.students_to_remove = obj_ut.create_dummy_users(5)
        self.all_enrolled = self.remaining_students + self.students_to_remove
        self.total_num_enrolled = len(self.all_enrolled)

        self.course.enrolled_students.add(*self.all_enrolled)

        self.request_body = {
            'remove_enrolled_students':
                [user.username for user in self.students_to_remove]
        }

    def test_admin_remove_enrolled_students(self):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(self.url, self.request_body)
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

        self.assertCountEqual(self.remaining_students,
                              self.course.enrolled_students.all())

    def test_other_remove_enrolled_students_permission_denied(self):
        for user in self.staff, self.remaining_students[0], self.nobody:
            self.client.force_authenticate(user)
            response = self.client.delete(self.url, self.request_body)
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
