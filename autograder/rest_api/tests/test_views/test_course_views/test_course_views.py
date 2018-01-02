from django.urls import reverse
from django.core import exceptions

from rest_framework import status

import autograder.core.models as ag_models

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class ListCoursesTestCase(test_data.Client, test_data.Superuser,
                          UnitTestBase):
    def setUp(self):
        super().setUp()

        self.admin = obj_build.create_dummy_user()
        self.courses = [
            obj_build.build_course(
                course_kwargs={'administrators': [self.admin]})
            for i in range(4)]

    def test_superuser_get_course_list(self):
        superuser = obj_build.create_dummy_user()
        superuser.is_superuser = True
        superuser.save()

        self.client.force_authenticate(user=superuser)
        response = self.client.get(reverse('course-list'))

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        expected_content = [course.to_dict() for course in self.courses]
        self.assertCountEqual(expected_content, response.data)

    def test_other_get_course_list_permission_denied(self):
        nobody = obj_build.create_dummy_user()

        for user in self.admin, nobody:
            self.client.force_authenticate(user=user)
            response = self.client.get(reverse('course-list'))
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateCourseTestCase(test_data.Client, test_data.Superuser,
                           UnitTestBase):
    def test_superuser_create_course(self):
        self.client.force_authenticate(self.superuser)
        name = 'new_course'
        response = self.client.post(reverse('course-list'), {'name': name})
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        loaded_course = ag_models.Course.objects.get(name=name)
        self.assertEqual(loaded_course.to_dict(), response.data)

    def test_other_create_course_permission_denied(self):
        nobody = obj_build.create_dummy_user()

        name = 'spam'
        self.client.force_authenticate(nobody)
        response = self.client.post(reverse('course-list'), {'name': name})

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual(0, ag_models.Course.objects.count())


class RetrieveCourseTestCase(test_data.Client, test_data.Course,
                             UnitTestBase):
    def test_get_course(self):
        for user in self.admin, self.nobody:
            self.client.force_authenticate(user)
            response = self.client.get(
                reverse('course-detail', kwargs={'pk': self.course.pk}))

            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertEqual(self.course.to_dict(), response.data)

    def test_get_course_not_found(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get(
            reverse('course-detail', kwargs={'pk': 3456}))
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)


class UpdateCourseTestCase(test_data.Client, test_data.Course,
                           UnitTestBase):
    def test_admin_patch_course(self):
        old_name = self.course.name
        new_name = 'steve'

        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            reverse('course-detail', kwargs={'pk': self.course.pk}),
            {"name": new_name})

        with self.assertRaises(exceptions.ObjectDoesNotExist):
            ag_models.Course.objects.get(name=old_name)

        self.course.refresh_from_db()
        self.assertEqual(self.course.name, new_name)

        self.assertEqual(self.course.to_dict(), response.data)

    def test_other_patch_course_permission_denied(self):
        old_name = self.course.name
        self.client.force_authenticate(self.nobody)

        response = self.client.patch(
            reverse('course-detail', kwargs={'pk': self.course.pk}),
            {"name": 'steve'})

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        self.course.refresh_from_db()
        self.assertEqual(self.course.name, old_name)

    def test_patch_course_not_found(self):
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            reverse('course-detail', kwargs={'pk': 3456}),
            {"name": 'spam'})

        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)


class UserRolesForCourseTestCase(test_data.Client, test_data.Course,
                                 test_impls.GetObjectTest, UnitTestBase):
    def expected_response_base(self):
        return {
            "is_admin": False,
            "is_staff": False,
            "is_enrolled": False
        }

    def test_admin_user_roles(self):
        expected = self.expected_response_base()
        expected['is_admin'] = True
        expected['is_staff'] = True

        self.do_get_object_test(
            self.client, self.admin, self.course_roles_url(self.course),
            expected)

    def test_staff_user_roles(self):
        expected = self.expected_response_base()
        expected['is_staff'] = True

        self.do_get_object_test(
            self.client, self.staff, self.course_roles_url(self.course),
            expected)

    def test_enrolled_user_roles(self):
        expected = self.expected_response_base()
        expected['is_enrolled'] = True

        self.do_get_object_test(
            self.client, self.enrolled, self.course_roles_url(self.course),
            expected)

    def test_other_user_roles(self):
        self.do_get_object_test(
            self.client, self.nobody, self.course_roles_url(self.course),
            self.expected_response_base())
