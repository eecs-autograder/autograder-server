from django.urls import reverse
from django.core import exceptions

from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class ListCoursesTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.courses = [obj_build.make_course() for i in range(4)]

    def test_superuser_get_course_list(self):
        [superuser] = obj_build.make_users(1, superuser=True)

        self.client.force_authenticate(user=superuser)
        response = self.client.get(reverse('course-list'))

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        expected_content = [course.to_dict() for course in self.courses]
        self.assertCountEqual(expected_content, response.data)

    def test_other_get_course_list_permission_denied(self):
        [admin] = obj_build.make_users(1)
        for course in self.courses:
            course.admins.add(admin)
        [guest] = obj_build.make_users(1)

        for user in admin, guest:
            self.client.force_authenticate(user=user)
            response = self.client.get(reverse('course-list'))
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateCourseTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_superuser_create_course(self):
        [superuser] = obj_build.make_users(1, superuser=True)
        self.client.force_authenticate(superuser)

        name = 'new_course'
        response = self.client.post(reverse('course-list'), {'name': name})
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        loaded_course = ag_models.Course.objects.get(name=name)
        self.assertEqual(loaded_course.to_dict(), response.data)

    def test_other_create_course_permission_denied(self):
        [guest] = obj_build.make_users(1)

        name = 'spam'
        self.client.force_authenticate(guest)
        response = self.client.post(reverse('course-list'), {'name': name})

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual(0, ag_models.Course.objects.count())


class RetrieveCourseTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_get_course(self):
        course = obj_build.make_course()
        [admin] = obj_build.make_admin_users(course, 1)
        [guest] = obj_build.make_users(1)

        for user in admin, guest:
            self.client.force_authenticate(user)
            response = self.client.get(reverse('course-detail', kwargs={'pk': course.pk}))

            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertEqual(course.to_dict(), response.data)

    def test_get_course_not_found(self):
        [guest] = obj_build.make_users(1)
        self.client.force_authenticate(guest)

        response = self.client.get(reverse('course-detail', kwargs={'pk': 3456}))
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)


class UpdateCourseTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.course = obj_build.make_course()
        [self.guest] = obj_build.make_users(1)

    def test_admin_patch_course(self):
        old_name = self.course.name
        new_name = 'steve'

        [admin] = obj_build.make_admin_users(self.course, 1)
        self.client.force_authenticate(admin)
        response = self.client.patch(
            reverse('course-detail', kwargs={'pk': self.course.pk}), {"name": new_name})

        with self.assertRaises(exceptions.ObjectDoesNotExist):
            ag_models.Course.objects.get(name=old_name)

        self.course.refresh_from_db()
        self.assertEqual(self.course.name, new_name)

        self.assertEqual(self.course.to_dict(), response.data)

    def test_other_patch_course_permission_denied(self):
        old_name = self.course.name
        self.client.force_authenticate(self.guest)

        response = self.client.patch(reverse('course-detail', kwargs={'pk': self.course.pk}),
                                     {"name": 'steve'})

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        self.course.refresh_from_db()
        self.assertEqual(self.course.name, old_name)

    def test_patch_course_not_found(self):
        self.client.force_authenticate(self.guest)

        response = self.client.patch(reverse('course-detail', kwargs={'pk': 3456}),
                                     {"name": 'spam'})

        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)


class UserRolesForCourseTestCase(test_impls.GetObjectTest, UnitTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.course = obj_build.make_course()
        self.url = reverse('course-my-roles', kwargs={'pk': self.course.pk})

    def expected_response_base(self):
        return {
            "is_admin": False,
            "is_staff": False,
            "is_student": False,
            "is_handgrader": False
        }

    def test_admin_user_roles(self):
        [admin] = obj_build.make_admin_users(self.course, 1)

        expected = self.expected_response_base()
        expected['is_admin'] = True
        expected['is_staff'] = True

        self.do_get_object_test(self.client, admin, self.url, expected)

    def test_staff_user_roles(self):
        [staff] = obj_build.make_staff_users(self.course, 1)

        expected = self.expected_response_base()
        expected['is_staff'] = True

        self.do_get_object_test(self.client, staff, self.url, expected)

    def test_student_user_roles(self):
        [student] = obj_build.make_student_users(self.course, 1)

        expected = self.expected_response_base()
        expected['is_student'] = True

        self.do_get_object_test(self.client, student, self.url, expected)

    def test_handgrader_user_roles(self):
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)

        expected = self.expected_response_base()
        expected['is_handgrader'] = True

        self.do_get_object_test(self.client, handgrader, self.url, expected)

    def test_other_user_roles(self):
        [guest] = obj_build.make_users(1)

        self.do_get_object_test(
            self.client, guest, self.url,
            self.expected_response_base())
