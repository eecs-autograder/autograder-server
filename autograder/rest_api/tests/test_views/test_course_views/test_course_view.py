from django.core.urlresolvers import reverse
from django.core import exceptions

from rest_framework import status

import autograder.core.models as ag_models

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
import autograder.rest_api.tests.test_views.common_generic_data as test_data


class ListCoursesTestCase(test_data.Client, test_data.Superuser,
                          TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.admin = obj_ut.create_dummy_user()
        self.courses = [
            obj_ut.build_course(
                course_kwargs={'administrators': [self.admin]})
            for i in range(4)]

    def test_superuser_get_course_list(self):
        superuser = obj_ut.create_dummy_user()
        superuser.is_superuser = True
        superuser.save()

        self.client.force_authenticate(user=superuser)
        response = self.client.get(reverse('course-list'))

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        expected_content = [course.to_dict() for course in self.courses]
        self.assertCountEqual(expected_content, response.data)

    def test_other_get_course_list_permission_denied(self):
        nobody = obj_ut.create_dummy_user()

        for user in self.admin, nobody:
            self.client.force_authenticate(user=user)
            response = self.client.get(reverse('course-list'))
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateCourseTestCase(test_data.Client, test_data.Superuser,
                           TemporaryFilesystemTestCase):
    def test_superuser_create_course(self):
        self.client.force_authenticate(self.superuser)
        name = 'new_course'
        response = self.client.post(reverse('course-list'), {'name': name})
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        loaded_course = ag_models.Course.objects.get(name=name)
        self.assertEqual(loaded_course.to_dict(), response.data)

    def test_other_create_course_permission_denied(self):
        nobody = obj_ut.create_dummy_user()

        name = 'spam'
        self.client.force_authenticate(nobody)
        response = self.client.post(reverse('course-list'), {'name': name})

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual(0, ag_models.Course.objects.count())


class RetrieveCourseTestCase(test_data.Client, test_data.Course,
                             TemporaryFilesystemTestCase):
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
                           TemporaryFilesystemTestCase):
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
