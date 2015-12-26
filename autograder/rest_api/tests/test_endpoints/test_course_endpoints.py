from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from autograder.core.models import Course, Semester

import autograder.core.tests.dummy_object_utils as obj_ut

from .utilities import MockClient, json_load_bytes


class ListCreateCourseTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.superuser = obj_ut.create_dummy_user()
        self.superuser.is_superuser = True
        self.superuser.save()

        self.admin = obj_ut.create_dummy_user()
        self.courses = [
            obj_ut.build_course(
                course_kwargs={'administrators': [self.admin]})
            for i in range(4)]

        self.nobody = obj_ut.create_dummy_user()

    def test_superuser_get_course_list(self):
        client = MockClient(self.superuser)
        response = client.get(reverse('courses'))

        self.assertEqual(200, response.status_code)

        expected_content = {
            "courses": [
                {
                    "name": course.name,
                    "url": reverse('course:get', kwargs={'pk': course.pk})
                }
                for course in sorted(self.courses, key=lambda obj: obj.name)
            ]
        }

        actual_content = json_load_bytes(response.content)
        actual_content['courses'].sort(key=lambda obj: obj['name'])

        self.assertEqual(expected_content, actual_content)

    def test_other_get_course_list_permission_denied(self):
        for user in self.admin, self.nobody:
            client = MockClient(user)
            response = client.get(reverse('courses'))
            self.assertEqual(403, response.status_code)

    # -------------------------------------------------------------------------

    def test_superuser_create_course(self):
        client = MockClient(self.superuser)

        name = 'new_course'
        response = client.post(reverse('courses'), {'name': name})
        self.assertEqual(201, response.status_code)

        loaded_course = Course.objects.get(name=name)
        expected_content = {
            "name": name,
            "url": reverse('course:get', kwargs={'pk': loaded_course.pk})
        }

        self.assertEqual(expected_content, json_load_bytes(response.content))

    def test_other_create_course_permission_denied(self):
        name = 'spam'
        for user in self.admin, self.nobody:
            client = MockClient(user)
            response = client.post(reverse('courses'), {'name': name})

            self.assertEqual(403, response.status_code)

            with self.assertRaises(ObjectDoesNotExist):
                Course.objects.get(name=name)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class GetUpdateCourseTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.admin = obj_ut.create_dummy_user()
        self.course = obj_ut.build_course(
            course_kwargs={'administrators': [self.admin]})

        self.nobody = obj_ut.create_dummy_user()

    def test_admin_get_course_all_information_returned(self):
        client = MockClient(self.admin)
        response = client.get(
            reverse('course:get', kwargs={'pk': self.course.pk}))

        self.assertEqual(200, response.status_code)

        expected_content = {
            "type": "course",
            "id": self.course.pk,
            "name": self.course.name,
            "urls": {
                "self": reverse('course:get', kwargs={'pk': self.course.pk}),
                "administrators": reverse(
                    'course:administrators', kwargs={'pk': self.course.pk}),
                "semesters": reverse(
                    'course:semesters', kwargs={'pk': self.course.pk})
            },
        }

        self.assertEqual(expected_content, json_load_bytes(response.content))

    def test_other_get_course_minimal_information_returned(self):
        client = MockClient(self.nobody)
        response = client.get(
            reverse('course:get', kwargs={'pk': self.course.pk}))

        self.assertEqual(200, response.status_code)

        expected_content = {
            "type": "course",
            "id": self.course.pk,
            "name": self.course.name,
            "urls": {
                "self": reverse('course:get', kwargs={'pk': self.course.pk}),
            },
        }

        self.assertEqual(expected_content, json_load_bytes(response.content))

    def test_get_course_not_found(self):
        client = MockClient(self.admin)

        response = client.get(reverse('course:get',  kwargs={'pk': 3456}))
        self.assertEqual(404, response.status_code)

    # -------------------------------------------------------------------------

    def test_admin_patch_course(self):
        old_name = self.course.name
        new_name = 'steve'
        client = MockClient(self.admin)

        response = client.patch(
            reverse('course:get', kwargs={'pk': self.course.pk}),
            {"name": new_name})

        with self.assertRaises(ObjectDoesNotExist):
            Course.objects.get(name=old_name)

        loaded = Course.objects.get(pk=self.course.pk)
        self.assertEqual(loaded.name, new_name)

        expected_content = {
            "type": "course",
            "id": self.course.pk,
            "name": new_name,
            "urls": {
                "self": reverse('course:get', kwargs={'pk': self.course.pk}),
                "administrators": reverse(
                    'course:administrators', kwargs={'pk': self.course.pk}),
                "semesters": reverse(
                    'course:semesters', kwargs={'pk': self.course.pk})
            },
        }

        self.assertEqual(expected_content, json_load_bytes(response.content))

    def test_other_patch_course_permission_denied(self):
        old_name = self.course.name
        client = MockClient(self.nobody)

        response = client.patch(
            reverse('course:get', kwargs={'pk': self.course.pk}),
            {"name": 'steve'})

        self.assertEqual(404, response.status_code)

        loaded = Course.objects.get(pk=self.course.pk)
        self.assertEqual(loaded.name, old_name)

    def test_patch_course_not_found(self):
        client = MockClient(self.admin)

        response = client.patch(
            reverse('course:get',  kwargs={'pk': 3456}),
            {"name": 'spam'})

        self.assertEqual(404, response.status_code)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddRemoveCourseAdministratorsTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.superuser = obj_ut.create_dummy_user()
        self.superuser.is_superuser = True
        self.superuser.save()

        self.admin = obj_ut.create_dummy_user()
        self.admin2 = obj_ut.create_dummy_user()
        self.course = obj_ut.build_course(
            course_kwargs={'administrators': [self.admin, self.admin2]})

        self.nobody = obj_ut.create_dummy_user()

        self.course_admins_url = reverse(
            'course:admins', kwargs={'pk': self.course.pk})

    def test_superuser_or_admin_list_administrators(self):
        expected_content = {
            "administrators": list(sorted([
                self.admin.username, self.admin2.username
            ]))
        }

        for user in self.superuser, self.admin:
            client = MockClient(user)

            response = client.get(self.course_admins_url)

            self.assertEqual(200, response.status_code)

            actual_content = json_load_bytes(response.content)

            self.assertEqual(expected_content, actual_content)

    def test_other_list_administrators_permission_denied(self):
        client = MockClient(self.nobody)
        response = client.get(self.course_admins_url)
        self.assertEqual(403, response.status_code)

    # -------------------------------------------------------------------------

    def test_superuser_or_admin_add_administrators(self):
        expected_content = {
            "administrators": list(sorted([
                self.admin.username, self.admin2.username
            ]))
        }

        new_admin_names = ['new_user1', 'new_user2']
        for user, new_admin_name in zip([self.superuser, self.admin], new_admin_names):
            expected_content['administrators'].append(new_admin_name)

            client = MockClient(user)
            response = client.post(
                self.course_admins_url, {"administrators": [new_admin_name]})

            self.assertEqual(201, response.status_code)
            self.assertEqual(
                expected_content, json_load_bytes(response.content))

            new_admin = User.objects.get(username=new_admin_name)
            self.course.administrators.get(username=new_admin_name)
            new_admin.courses_is_admin_for.get(pk=self.course)

    def test_other_add_administrators_permission_denied(self):
        client = MockClient(self.nobody)
        new_admin_name = 'steve'
        response = client.post(
            self.course_admins_url, {"administrators": [new_admin_name]})

        self.assertEqual(403, response.status_code)

        with self.assertRaises(ObjectDoesNotExist):
            User.objects.get(username=new_admin_name)

    # -------------------------------------------------------------------------

    def test_superuser_or_admin_remove_single_administrators(self):
        expected_content = {
            "administrators": list(sorted([
                self.admin.username, self.admin2.username
            ]))
        }

        iterable = zip(
            [self.superuser, self.admin2],
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

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddSemesterTestCase(TemporaryFilesystemTestCase):
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

    def test_course_admin_create_semester(self):
        new_name = 'spam'

        client = MockClient(self.admin)
        response = client.post(self.course_semesters_url, {'name': new_name})
        self.assertEqual(201, response.status_code)

        loaded = self.course.semesters.get(name='new_name')

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
            self.assertEqual(403, response.content)

            with self.assertRaises(ObjectDoesNotExist):
                Semester.objects.get(name=new_name)

    def test_bad_request_semester_already_exists(self):
        client = MockClient(self.admin)
        response = client.post(
            self.course_semesters_url, {'name': self.semester.name})
        self.assertEqual(400, response.status_code)
