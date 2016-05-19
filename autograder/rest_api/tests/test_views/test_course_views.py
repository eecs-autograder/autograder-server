import itertools

from django.core.urlresolvers import reverse
from django.core import exceptions
from django.contrib.auth.models import User

from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut


class ListCoursesTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.client = APIClient()

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


class CreateCourseTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_superuser_create_course(self):
        superuser = obj_ut.create_dummy_user()
        superuser.is_superuser = True
        superuser.save()

        self.client.force_authenticate(superuser)
        name = 'new_course'
        response = self.client.post(reverse('course-list'), {'name': name})
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        loaded_course = ag_models.Course.objects.get(name=name)
        self.assertEqual(loaded_course.to_dict(), response.data)

    def test_other_create_course_permission_denied(self):
        admin = obj_ut.create_dummy_user()
        nobody = obj_ut.create_dummy_user()

        name = 'spam'
        for user in admin, nobody:
            self.client.force_authenticate(user)
            response = self.client.post(reverse('course-list'), {'name': name})

            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
            self.assertEqual(0, ag_models.Course.objects.count())


class RetrieveCourseTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.client = APIClient()

        self.admin = obj_ut.create_dummy_user()
        self.course = obj_ut.build_course(
            course_kwargs={'administrators': [self.admin]})

    def test_get_course(self):
        nobody = obj_ut.create_dummy_user()

        for user in self.admin, nobody:
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


class UpdateCourseTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.client = APIClient()

        self.admin = obj_ut.create_dummy_user()
        self.course = obj_ut.build_course(
            course_kwargs={'administrators': [self.admin]})

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
        nobody = obj_ut.create_dummy_user()

        old_name = self.course.name
        self.client.force_authenticate(nobody)

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

# -----------------------------------------------------------------------------


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

        for user in self.superuser, self.admin:
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

    # -------------------------------------------------------------------------


class RemoveCourseAdminTestCase(TemporaryFilesystemTestCase):
    def test_superuser_or_admin_remove_single_administrators(self):
        expected_content = {
            "administrators": list(sorted([
                self.admin.username, self.admin2.username
            ]))
        }

        iterable = zip(
            [self.admin2, self.superuser],
            [self.admin.username, self.admin2.username])
        for user, admin_to_remove in iterable:
            expected_content['administrators'].remove(admin_to_remove)

            client = MockClient(user)
            response = client.delete(
                self.course_admins_url, {'administrators': [admin_to_remove]})

            self.assertEqual(200, response.status_code)

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_remove_multiple_administrators(self):
        client = MockClient(self.superuser)
        response = client.delete(
            self.course_admins_url,
            {'administrators': [self.admin.username, self.admin2.username]})

        self.assertEqual(200, response.status_code)

        loaded = Course.objects.get(pk=self.course.pk)
        self.assertCountEqual(loaded.administrators.all(), [])

    def test_error_admin_remove_self_from_admin_list(self):
        client = MockClient(self.admin)
        response = client.delete(
            self.course_admins_url,
            {'administrators': [self.admin2.username, self.admin.username]})
        self.assertEqual(400, response.status_code)

        loaded = Course.objects.get(pk=self.course.pk)
        self.assertCountEqual(
            loaded.administrators.all(), [self.admin, self.admin2])

    def test_other_remove_administrators_permission_denied(self):
        client = MockClient(self.nobody)
        response = client.delete(
            self.course_admins_url,
            {'administrators': [self.admin2.username, self.admin.username]})

        self.assertEqual(403, response.status_code)

        loaded = Course.objects.get(pk=self.course.pk)
        self.assertCountEqual(
            loaded.administrators.all(), [self.admin, self.admin2])



class ListSemestersTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.admin = obj_ut.create_dummy_user()

        self.staff = obj_ut.create_dummy_user()
        self.nobody = obj_ut.create_dummy_user()

        self.semester = obj_ut.build_semester(
            course_kwargs={'administrators': [self.admin]},
            semester_kwargs={'staff': [self.staff]})

        self.course = self.semester.course

        self.semester2 = obj_ut.build_semester(
            semester_kwargs={'course': self.course})

        self.course_semesters_url = reverse(
            'course:semesters', kwargs={'pk': self.course.pk})

    def test_course_admin_list_semesters(self):
        expected_content = {
            'semesters': [
                {
                    "name": semester.name,
                    "url": reverse('semester:get', kwargs={'pk': semester.pk})
                }
                for semester in sorted(
                    [self.semester, self.semester2], key=lambda obj: obj.name)
            ]
        }

        client = MockClient(self.admin)
        response = client.get(self.course_semesters_url)
        self.assertEqual(200, response.status_code)
        actual_content = json_load_bytes(response.content)
        actual_content['semesters'].sort(key=lambda obj: obj['name'])
        self.assertEqual(expected_content, actual_content)

    def test_other_list_semesters_permission_denied(self):
        for user in self.nobody, self.staff:
            client = MockClient(user)
            response = client.get(self.course_semesters_url)
            self.assertEqual(403, response.status_code)

    # -------------------------------------------------------------------------


class CreateSemesterTestCase(TemporaryFilesystemTestCase):
    def test_course_admin_create_semester(self):
        new_name = 'spam'

        client = MockClient(self.admin)
        response = client.post(self.course_semesters_url, {'name': new_name})
        self.assertEqual(201, response.status_code)

        loaded = self.course.semesters.get(name=new_name)

        expected_content = {
            "name": new_name,
            "url": reverse('semester:get', kwargs={'pk': loaded.pk})
        }

        self.assertEqual(expected_content, json_load_bytes(response.content))

    def test_other_create_semester_permission_denied(self):
        new_name = 'steve'
        for user in self.staff, self.nobody:
            client = MockClient(user)
            response = client.post(
                self.course_semesters_url, {'name': new_name})
            self.assertEqual(403, response.status_code)

            with self.assertRaises(ObjectDoesNotExist):
                Semester.objects.get(name=new_name)

    def test_bad_request_semester_already_exists(self):
        client = MockClient(self.admin)
        response = client.post(
            self.course_semesters_url, {'name': self.semester.name})
        self.assertEqual(400, response.status_code)
