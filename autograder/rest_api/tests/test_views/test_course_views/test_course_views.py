from unittest import mock

from django.contrib.auth.models import User, Permission
from django.urls import reverse
from django.core import exceptions

from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models

from autograder.rest_api.tests.test_views.ag_view_test_base import AGViewTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class ListCoursesTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.courses = [obj_build.make_course() for i in range(4)]

    def test_superuser_get_course_list(self):
        [superuser] = obj_build.make_users(1, superuser=True)

        self.client.force_authenticate(user=superuser)
        response = self.client.get(reverse('list-create-courses'))

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
            response = self.client.get(reverse('list-create-courses'))
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateCourseTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_superuser_create_course(self):
        superuser = obj_build.make_user(superuser=True)
        self.client.force_authenticate(superuser)

        name = 'new_course'
        response = self.client.post(reverse('list-create-courses'), {'name': name})
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        loaded_course = ag_models.Course.objects.get(name=name)
        self.assertEqual(loaded_course.to_dict(), response.data)
        self.assertTrue(loaded_course.is_admin(superuser))

    def test_user_with_create_course_permission_create_course(self):
        user = obj_build.make_user()
        user.user_permissions.add(Permission.objects.get(codename='create_course'))
        self.client.force_authenticate(user)

        response = self.client.post(reverse('list-create-courses'), {'name': 'waluigi'})
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        loaded_course = ag_models.Course.objects.get(name='waluigi')
        self.assertEqual(loaded_course.to_dict(), response.data)
        self.assertTrue(loaded_course.is_admin(user))

    def test_other_create_course_permission_denied(self):
        guest = obj_build.make_user()

        name = 'spam'
        self.client.force_authenticate(guest)
        response = self.client.post(reverse('list-create-courses'), {'name': name})

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual(0, ag_models.Course.objects.count())


class CopyCourseViewTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()

        self.client = APIClient()
        self.course = obj_build.make_course()

    def test_superuser_copy_course_new_name_semester_year(self):
        superuser = obj_build.make_user(superuser=True)

        new_name = 'steve'
        new_semester = ag_models.Semester.summer
        new_year = 2019

        self.client.force_authenticate(superuser)
        response = self.client.post(reverse('copy-course', kwargs={'pk': self.course.pk}),
                                    {'new_name': new_name,
                                     'new_semester': new_semester.value,
                                     'new_year': new_year})

        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        new_course = ag_models.Course.objects.get(pk=response.data['pk'])
        self.assertEqual(new_name, new_course.name)
        self.assertEqual(new_semester, new_course.semester)
        self.assertEqual(new_year, new_course.year)

        self.assertEqual(new_course.to_dict(), response.data)

    def test_superuser_view_calls_copy_course(self):
        superuser = obj_build.make_user(superuser=True)

        dummy_course = obj_build.make_course()
        mock_copy_course = mock.Mock(return_value=dummy_course)
        with mock.patch('autograder.rest_api.views.course_views.course_views.copy_course',
                        new=mock_copy_course):
            self.client.force_authenticate(superuser)
            response = self.client.post(
                reverse('copy-course', kwargs={'pk': self.course.pk}),
                {'new_name': 'Clone',
                 'new_semester': ag_models.Semester.winter.value,
                 'new_year': 2020}
            )

            mock_copy_course.assert_called_once_with(
                course=self.course, new_course_name='Clone',
                new_course_semester=ag_models.Semester.winter,
                new_course_year=2020)

    def test_admin_copy_course_new_name_semester_and_year(self):
        user = obj_build.make_admin_user(self.course)

        new_name = 'stave'
        new_semester = ag_models.Semester.fall
        new_year = 2017

        self.client.force_authenticate(user)
        response = self.client.post(reverse('copy-course', kwargs={'pk': self.course.pk}),
                                    {'new_name': new_name,
                                     'new_semester': new_semester.value,
                                     'new_year': new_year})

        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        new_course = ag_models.Course.objects.get(pk=response.data['pk'])
        self.assertEqual(new_name, new_course.name)
        self.assertEqual(new_semester, new_course.semester)
        self.assertEqual(new_year, new_course.year)

        self.assertEqual(new_course.to_dict(), response.data)

    def test_copy_course_view_calls_copy_course_function(self):
        user = obj_build.make_admin_user(self.course)

        dummy_course = obj_build.make_course()
        mock_copy_course = mock.Mock(return_value=dummy_course)
        with mock.patch('autograder.rest_api.views.course_views.course_views.copy_course',
                        new=mock_copy_course):
            self.client.force_authenticate(user)
            response = self.client.post(
                reverse('copy-course', kwargs={'pk': self.course.pk}),
                {'new_name': 'Cloney',
                 'new_semester': ag_models.Semester.spring.value,
                 'new_year': 2021}
            )

            mock_copy_course.assert_called_once_with(
                course=self.course, new_course_name='Cloney',
                new_course_semester=ag_models.Semester.spring,
                new_course_year=2021)

    def test_user_not_admin_permission_denied(self):
        other_course = obj_build.make_course()
        user = obj_build.make_admin_user(other_course)

        self.client.force_authenticate(user)
        response = self.client.post(
            reverse('copy-course', kwargs={'pk': self.course.pk}),
            {
                'new_name': 'New',
                'new_semester': ag_models.Semester.summer.value,
                'new_year': 2021
            }
        )
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_user_can_create_courses_but_not_admin_permission_denied(self):
        user = obj_build.make_user()
        user.user_permissions.add(Permission.objects.get(codename='create_course'))

        self.client.force_authenticate(user)
        response = self.client.post(
            reverse('copy-course', kwargs={'pk': self.course.pk}),
            {'new_name': 'New',
             'new_semester': ag_models.Semester.summer.value,
             'new_year': 2021}
        )
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_error_missing_body_params(self):
        superuser = obj_build.make_user(superuser=True)

        new_name = 'steve'
        new_semester = ag_models.Semester.summer
        new_year = 2019

        self.client.force_authenticate(superuser)
        response = self.client.post(reverse('copy-course', kwargs={'pk': self.course.pk}),
                                    {'new_name': new_name,
                                     'new_semester': new_semester.value})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        response = self.client.post(reverse('copy-course', kwargs={'pk': self.course.pk}),
                                    {'new_name': new_name,
                                     'new_year': new_year})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        response = self.client.post(reverse('copy-course', kwargs={'pk': self.course.pk}),
                                    {'new_semester': new_semester.value,
                                     'new_year': new_year})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_error_non_unique_course(self):
        superuser = obj_build.make_user(superuser=True)
        self.client.force_authenticate(superuser)

        self.course.semester = ag_models.Semester.fall
        self.course.year = 2017
        self.course.save()

        response = self.client.post(
            reverse('copy-course', kwargs={'pk': self.course.pk}),
            {'new_name': self.course.name,
             'new_semester': self.course.semester.value,
             'new_year': self.course.year}
        )

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('exists', response.data['__all__'][0])


class RetrieveCourseTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_get_course_by_pk(self):
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


class UpdateCourseTestCase(AGViewTestBase):
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


class UserRolesForCourseTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.course = obj_build.make_course()
        self.url = reverse('course-user-roles', kwargs={'pk': self.course.pk})

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


class CourseByNameSemesterYearViewTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_get_course_by_name_semester_and_year(self):
        course = obj_build.make_course(semester=ag_models.Semester.winter, year=2019)
        url = reverse('course-by-fields',
                      kwargs={'name': course.name, 'semester': course.semester.value,
                              'year': course.year})

        guest = obj_build.make_user()

        self.client.force_authenticate(guest)
        response = self.client.get(url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(course.to_dict(), response.data)

    def test_invalid_semester(self):
        course = obj_build.make_course(semester=ag_models.Semester.winter, year=2019)
        url = reverse('course-by-fields',
                      kwargs={'name': course.name, 'semester': 'bad',
                              'year': course.year})

        guest = obj_build.make_user()

        self.client.force_authenticate(guest)
        response = self.client.get(url)

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
