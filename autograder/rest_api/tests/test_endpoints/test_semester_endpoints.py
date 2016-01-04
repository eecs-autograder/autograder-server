import copy
import itertools

from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
# from django.contrib.auth.models import User
from django.utils import timezone

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from autograder.core.models import Course, Semester, Project
from autograder.rest_api.endpoints.semester_endpoints import (
    DEFAULT_ENROLLED_STUDENT_PAGE_SIZE)

import autograder.core.tests.dummy_object_utils as obj_ut

from .utilities import MockClient, json_load_bytes


def _common_setup(fixture):
    fixture.admin = obj_ut.create_dummy_user()
    fixture.staff = obj_ut.create_dummy_users(3)
    fixture.enrolled = obj_ut.create_dummy_users(5)
    fixture.nobody = obj_ut.create_dummy_user()

    fixture.semester = obj_ut.build_semester(
        course_kwargs={'administrators': [fixture.admin]},
        semester_kwargs={
            'staff': fixture.staff, 'enrolled_students': fixture.enrolled})
    fixture.course = fixture.semester.course

    fixture.course_url = reverse(
        'course:get', kwargs={'pk': fixture.course.pk})

    fixture.semester_url = reverse(
        'semester:get', kwargs={'pk': fixture.semester.pk})
    fixture.staff_url = reverse(
        'semester:staff', kwargs={'pk': fixture.semester.pk})
    fixture.enrolled_url = reverse(
        'semester:enrolled_students', kwargs={'pk': fixture.semester.pk})
    fixture.projects_url = reverse(
        'semester:projects', kwargs={'pk': fixture.semester.pk})


class GetUpdateSemesterTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        _common_setup(self)

    def test_course_admin_or_semester_staff_get_semester(self):
        expected_content = {
            "type": "semester",
            "id": self.semester.pk,
            "name": self.semester.name,
            "course_name": self.semester.course.name,
            "urls": {
                "self": self.semester_url,
                "course": self.course_url,
                "staff": self.staff_url,
                "enrolled_students": self.enrolled_url,
                "projects": self.projects_url
            }
        }

        for user in self.admin, self.staff[0]:
            client = MockClient(user)
            response = client.get(self.semester_url)
            self.assertEqual(200, response.status_code)
            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_enrolled_student_get_semester(self):
        expected_content = {
            "type": "semester",
            "id": self.semester.pk,
            "name": self.semester.name,
            "course_name": self.semester.course.name,
            "urls": {
                "self": self.semester_url,
                "course": self.course_url,
                "projects": self.projects_url
            }
        }

        client = MockClient(self.enrolled[0])
        response = client.get(self.semester_url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            expected_content, json_load_bytes(response.content))

    def test_other_get_semester_permission_denied(self):
        client = MockClient(self.nobody)
        response = client.get(self.semester_url)
        self.assertEqual(403, response.status_code)

    # -------------------------------------------------------------------------

    def test_course_admin_patch_semester(self):
        new_name = 'spam'
        old_name = self.semester.name
        expected_content = {
            "name": new_name,
        }

        client = MockClient(self.admin)
        response = client.patch(self.semester_url, {'name': new_name})

        self.assertEqual(200, response.status_code)
        self.assertEqual(expected_content, json_load_bytes(response.content))

        with self.assertRaises(ObjectDoesNotExist):
            Semester.objects.get(name=old_name)

        loaded = Semester.objects.get(pk=self.semester.pk)
        self.assertEqual(new_name, loaded.name)

    def test_other_patch_semester_permission_denied(self):
        new_name = 'spaaaam'
        old_name = self.semester.name
        for user in self.staff[0], self.enrolled[0], self.nobody:
            client = MockClient(user)
            response = client.patch(self.semester_url, {'name': new_name})
            self.assertEqual(403, response.status_code)

            with self.assertRaises(ObjectDoesNotExist):
                Semester.objects.get(name=new_name)

            loaded = Semester.objects.get(pk=self.semester.pk)
            self.assertEqual(old_name, loaded.name)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddRemoveSemesterStaffTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        _common_setup(self)

        self.staff_names = list(sorted(set(
            itertools.chain(
                (user.username for user in self.staff),
                (self.admin.username,)
            )
        )))

    def test_course_admin_list_staff(self):
        expected_content = {
            'staff': self.staff_names
        }

        client = MockClient(self.admin)
        response = client.get(self.staff_url)
        self.assertEqual(200, response.status_code)
        actual_content = json_load_bytes(response.content)
        actual_content['staff'].sort()
        self.assertEqual(expected_content, actual_content)

    def test_other_list_staff_permission_denied(self):
        for user in self.enrolled[0], self.nobody:
            client = MockClient(user)
            response = client.get(self.staff_url)

            self.assertEqual(403, response.status_code)

    # -------------------------------------------------------------------------

    def test_course_admin_add_staff(self):
        new_staff_names = ['staffy1', 'staffy2']
        self.staff_names += new_staff_names
        self.staff_names.sort()

        client = MockClient(self.admin)
        response = client.post(self.staff_url, {'staff': new_staff_names})
        self.assertEqual(201, response.status_code)

        expected_content = {
            'staff': self.staff_names
        }

        actual_content = json_load_bytes(response.content)
        actual_content['staff'].sort()
        self.assertEqual(expected_content, actual_content)

        self.assertCountEqual(
            self.staff_names, self.semester.semester_staff_names)

    def test_other_add_staff_permission_denied(self):
        for user in self.staff[0], self.enrolled[0], self.nobody:
            client = MockClient(user)
            response = client.post(
                self.staff_url, {'staff': ['spam', 'steve']})

            self.assertEqual(403, response.status_code)

            self.assertCountEqual(
                self.staff_names, self.semester.semester_staff_names)

    # -------------------------------------------------------------------------

    def test_course_admin_remove_staff(self):
        client = MockClient(self.admin)
        to_remove = copy.copy(self.staff_names)
        to_remove.remove(self.admin.username)
        remaining = [self.admin.username]

        response = client.delete(self.staff_url, {'staff': to_remove})

        self.assertEqual(200, response.status_code)

        expected_content = {
            'staff': remaining
        }

        actual_content = json_load_bytes(response.content)
        actual_content['staff'].sort()
        self.assertEqual(expected_content, actual_content)

        self.assertCountEqual(
            remaining, self.semester.semester_staff_names)

    def test_other_remove_staff_permission_denied(self):
        for user in self.staff[0], self.enrolled[0], self.nobody:
            client = MockClient(user)
            response = client.delete(
                self.staff_url,
                {'staff': [user.username for user in self.staff]})
            self.assertEqual(403, response.status_code)

            self.assertCountEqual(
                self.staff_names, self.semester.semester_staff_names)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddUpdateRemoveEnrolledStudentsTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        _common_setup(self)

        self.enrolled_names = list(sorted(
            (user.username for user in self.enrolled)))

    def test_list_students_default(self):
        more_users = obj_ut.create_dummy_users(30)
        self.semester.enrolled_students.add(*more_users)
        self.enrolled_names += [user.username for user in more_users]
        self.enrolled_names.sort()

        expected_content = {
            'enrolled_students': (
                self.enrolled_names[:DEFAULT_ENROLLED_STUDENT_PAGE_SIZE]),
            "total_num_students_matching_query": len(self.enrolled_names)
        }

        for user in self.enrolled[0], self.staff[0], self.admin:
            client = MockClient(user)
            response = client.get(self.enrolled_url)
            self.assertEqual(200, response.status_code)
            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_list_students_first_page_custom_page_size(self):
        size = 2
        expected_content = {
            'enrolled_students': self.enrolled_names[:size],
            "total_num_students_matching_query": len(self.enrolled_names)
        }

        for user in self.enrolled[0], self.staff[0], self.admin:
            client = MockClient(user)
            response = client.get(self.enrolled_url, {'page_size': size})
            self.assertEqual(200, response.status_code)
            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_list_students_middle_page_custom_page_size(self):
        size = 2
        page_num = 1
        expected_content = {
            'enrolled_students': self.enrolled_names[
                size * page_num:size * (page_num + 1)],
            "total_num_students_matching_query": len(self.enrolled_names)
        }

        for user in self.enrolled[0], self.staff[0], self.admin:
            client = MockClient(user)
            response = client.get(
                self.enrolled_url,
                {'page_size': size, 'page_number': page_num})
            self.assertEqual(200, response.status_code)
            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_list_students_last_page_custom_page_size(self):
        size = 2
        page_num = 2
        expected_content = {
            'enrolled_students': self.enrolled_names[
                size * page_num:],
            "total_num_students_matching_query": len(self.enrolled_names)
        }

        for user in self.enrolled[0], self.staff[0], self.admin:
            client = MockClient(user)
            response = client.get(
                self.enrolled_url,
                {'page_size': size, 'page_number': page_num})
            self.assertEqual(200, response.status_code)
            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_list_students_filter_by_username_startswith(self):
        self.enrolled[0].username = 'steve'
        self.enrolled[0].save()
        self.enrolled[-1].username = 'stove'
        self.enrolled[-1].save()

        expected_content = {
            'enrolled_students': ['steve', 'stove'],
            "total_num_students_matching_query": 2,
        }

        for user in self.enrolled[0], self.staff[0], self.admin:
            client = MockClient(user)
            response = client.get(
                self.enrolled_url, {'username_starts_with': 'st'})
            self.assertEqual(200, response.status_code)
            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_list_students_filter_by_username_startswith_with_pagination(self):
        self.enrolled[0].username = 'steve'
        self.enrolled[0].save()
        self.enrolled[-1].username = 'stove'
        self.enrolled[-1].save()

        expected_content = {
            'enrolled_students': ['stove'],
            "total_num_students_matching_query": 2,
        }

        for user in self.enrolled[0], self.staff[0], self.admin:
            client = MockClient(user)
            response = client.get(
                self.enrolled_url,
                {'username_starts_with': 'st',
                 'page_size': 1, 'page_number': 1})
            self.assertEqual(200, response.status_code)
            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_non_enrolled_list_students_permission_denied(self):
        client = MockClient(self.nobody)
        response = client.get(self.enrolled_url)
        self.assertEqual(403, response.status_code)

    # -------------------------------------------------------------------------

    def test_admin_add_enrolled_students(self):
        client = MockClient(self.admin)
        new_students = ['steve', 'bill']

        response = client.post(
            self.enrolled_url, {'enrolled_students': new_students})

        self.assertEqual(201, response.status_code)

        self.enrolled_names += new_students
        self.enrolled_names.sort()

        expected_content = {
            'enrolled_students': (
                self.enrolled_names[:DEFAULT_ENROLLED_STUDENT_PAGE_SIZE]),
            'total_num_students_matching_query': len(self.enrolled_names)
        }

        self.assertEqual(expected_content, json_load_bytes(response.content))

        for student in new_students:
            self.assertTrue(student in self.semester.enrolled_student_names)

    def test_other_add_enrolled_students_permission_denied(self):
        for user in self.staff[0], self.enrolled[0], self.nobody:
            client = MockClient(user)
            response = client.post(
                self.enrolled_url, {'enrolled_students': ['steve']})
            self.assertEqual(403, response.status_code)

            self.assertEqual(
                self.enrolled_names,
                sorted(self.semester.enrolled_student_names))

    def test_admin_update_enrolled_students(self):
        client = MockClient(self.admin)
        new_students = ['steve', 'bill']

        response = client.patch(
            self.enrolled_url, {'enrolled_students': new_students})

        self.assertEqual(200, response.status_code)

        expected_content = {
            'enrolled_students': list(sorted(new_students)),
            'total_num_students_matching_query': len(new_students)
        }

        self.assertEqual(expected_content, json_load_bytes(response.content))

        self.assertCountEqual(
            sorted(new_students), sorted(self.semester.enrolled_student_names))

    def test_other_update_enrolled_students_permission_denied(self):
        for user in self.staff[0], self.enrolled[0], self.nobody:
            client = MockClient(user)
            response = client.patch(
                self.enrolled_url, {'enrolled_students': ['steve']})
            self.assertEqual(403, response.status_code)

            self.assertEqual(
                self.enrolled_names,
                sorted(self.semester.enrolled_student_names))

    # -------------------------------------------------------------------------

    def test_admin_remove_enrolled_students(self):
        client = MockClient(self.admin)
        response = client.delete(
            self.enrolled_url,
            {'enrolled_students': [self.enrolled_names[0]]})
        self.assertEqual(200, response.status_code)

        self.enrolled_names = self.enrolled_names[1:]

        expected_content = {
            'enrolled_students': (
                self.enrolled_names[:DEFAULT_ENROLLED_STUDENT_PAGE_SIZE]),
            'total_num_students_matching_query': len(self.enrolled_names)
        }

        self.assertEqual(expected_content, json_load_bytes(response.content))

        self.assertEqual(
            self.enrolled_names, sorted(self.semester.enrolled_student_names))

    def test_other_remove_enrolled_students_permission_denied(self):
        for user in self.staff[0], self.enrolled[0], self.nobody:
            client = MockClient(user)
            response = client.delete(
                self.enrolled_url,
                {'enrolled_students': [self.enrolled_names[0]]})
            self.assertEqual(403, response.status_code)

            self.assertEqual(
                self.enrolled_names,
                sorted(self.semester.enrolled_student_names))

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddProjectTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        _common_setup(self)

        self.visible_project = obj_ut.build_project(
            project_kwargs={'semester': self.semester,
                            'visible_to_students': True})

        self.visible_project2 = obj_ut.build_project(
            project_kwargs={'semester': self.semester,
                            'visible_to_students': True})

        self.hidden_project = obj_ut.build_project(
            project_kwargs={'semester': self.semester,
                            'visible_to_students': False})

        self.all_projects = sorted(
            (self.visible_project, self.visible_project2, self.hidden_project),
            key=lambda obj: obj.pk)

    def test_admin_or_staff_list_projects(self):
        expected_content = {
            "projects": [
                {
                    'name': project.name,
                    'url': reverse('project:get', kwargs={'pk': project.pk})
                }
                for project in sorted(
                    self.all_projects, key=lambda obj: obj.name)
            ]
        }

        for user in self.admin, self.staff[0]:
            client = MockClient(user)
            response = client.get(self.projects_url)

            self.assertEqual(200, response.status_code)
            actual_content = json_load_bytes(response.content)
            actual_content['projects'].sort(key=lambda obj: obj['name'])

            self.assertEqual(expected_content, actual_content)

    def test_enrolled_student_list_projects_visible_only(self):
        visible_projects = (project for project in self.all_projects
                            if project.visible_to_students)
        expected_content = {
            "projects": [
                {
                    'name': project.name,
                    'url': reverse('project:get', kwargs={'pk': project.pk})
                }
                for project in sorted(
                    visible_projects, key=lambda obj: obj.name)
            ]
        }

        client = MockClient(self.enrolled[0])
        response = client.get(self.projects_url)

        self.assertEqual(200, response.status_code)
        actual_content = json_load_bytes(response.content)
        actual_content['projects'].sort(key=lambda obj: obj['name'])

        self.assertEqual(expected_content, actual_content)

    def test_other_list_projects_permission_denied(self):
        client = MockClient(self.nobody)
        response = client.get(self.projects_url)
        self.assertEqual(403, response.status_code)

    # -------------------------------------------------------------------------

    def test_course_admin_add_project_default_args(self):
        args = {'name': 'spam project'}
        client = MockClient(self.admin)
        response = client.post(self.projects_url, args)

        self.assertEqual(201, response.status_code)

        actual_content = json_load_bytes(response.content)

        loaded = Project.objects.get(name=args['name'])

        expected_content = {
            "name": loaded.name,
            "url": reverse('project:get', kwargs={'pk': loaded.pk})
        }

        self.assertEqual(expected_content, actual_content)

    def test_course_admin_add_project_no_defaults(self):
        args = {
            'name': 'spam project',
            "visible_to_students": True,
            "closing_time": timezone.now().replace(microsecond=0),
            "disallow_student_submissions": True,
            "allow_submissions_from_non_enrolled_students": True,
            "min_group_size": 2,
            "max_group_size": 3,
            "required_student_files": ['spam.cpp', 'eggs.cpp'],
            "expected_student_file_patterns": [
                ['test_*.cpp', 1, 4], ['cheese[0-9].txt', 0, 2]
            ]
        }
        client = MockClient(self.admin)
        response = client.post(self.projects_url, args)

        self.assertEqual(201, response.status_code)

        actual_content = json_load_bytes(response.content)

        loaded = Project.objects.get(name=args['name'])

        args['expected_student_file_patterns'] = [
            Project.FilePatternTuple(*list_) for list_ in
            args['expected_student_file_patterns']
        ]

        for arg, value in args.items():
            self.assertEqual(value, getattr(loaded, arg))

        expected_content = {
            "name": loaded.name,
            "url": reverse('project:get', kwargs={'pk': loaded.pk})
        }

        self.assertEqual(expected_content, actual_content)

    def test_other_add_project_permission_denied(self):
        project_name = 'spam_project'
        for user in self.staff[0], self.enrolled[0], self.nobody:
            client = MockClient(user)
            response = client.post(self.projects_url, {'name': project_name})

            self.assertEqual(403, response.status_code)

            with self.assertRaises(ObjectDoesNotExist):
                Project.objects.get(name=project_name)
