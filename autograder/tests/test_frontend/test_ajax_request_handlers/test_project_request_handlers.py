import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.tests.dummy_object_utils as obj_ut

from .utils import (
    process_get_request, process_post_request,
    process_patch_request, process_delete_request, json_load_bytes)

from autograder.frontend.json_api_serializers import (
    semester_to_json, project_to_json)
from autograder.models import Project


class AddProjectRequestTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.admin = obj_ut.create_dummy_users()

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)

        self.course.add_course_admins(self.admin)

        self.new_project_name = 'project42'

    def test_valid_add_project(self):
        response = _add_project_request(
            self.semester, self.new_project_name, self.admin)

        self.assertEqual(201, response.status_code)

        loaded_project = Project.objects.get(
            name=self.new_project_name, semester=self.semester)
        expected = {
            'data': project_to_json(loaded_project)
        }

        self.assertEqual(expected, json_load_bytes(response.content))

    def test_add_project_permission_denied(self):
        # Staff member (non-admin)
        staff = obj_ut.create_dummy_users()
        response = _add_project_request(
            self.semester, self.new_project_name, staff)
        self.assertEqual(403, response.status_code)

        with self.assertRaises(ObjectDoesNotExist):
            Project.objects.get(
                name=self.new_project_name, semester=self.semester)

        # Enrolled student
        enrolled = obj_ut.create_dummy_users()
        response = _add_project_request(self.semester, 'haxorz', enrolled)
        self.assertEqual(403, response.status_code)

        with self.assertRaises(ObjectDoesNotExist):
            Project.objects.get(
                name=self.new_project_name, semester=self.semester)

        # Nobody user
        nobody = obj_ut.create_dummy_users()
        response = _add_project_request(self.semester, 'haxorz', nobody)
        self.assertEqual(403, response.status_code)

        with self.assertRaises(ObjectDoesNotExist):
            Project.objects.get(
                name=self.new_project_name, semester=self.semester)

    def test_error_add_duplicate_project(self):
        Project.objects.validate_and_create(
            name=self.new_project_name, semester=self.semester)

        response = _add_project_request(
            self.semester, self.new_project_name, self.admin)
        self.assertEqual(409, response.status_code)

        self.assertTrue('errors' in json_load_bytes(response.content))


# -----------------------------------------------------------------------------

class GetProjectRequestTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.user = obj_ut.create_dummy_users()

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)

        self.visible_project = obj_ut.create_dummy_projects(self.semester)
        self.visible_project.visible_to_students = True
        self.visible_project.validate_and_save()

        self.hidden_project = obj_ut.create_dummy_projects(self.semester)

    def test_course_admin_or_staff_get_project(self):
        self.course.add_course_admins(self.user)

        response = _get_project_request(self.visible_project.pk, self.user)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {'data': project_to_json(self.visible_project)},
            json_load_bytes(response.content))

        response = _get_project_request(self.hidden_project.pk, self.user)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {'data': project_to_json(self.hidden_project)},
            json_load_bytes(response.content))

    def test_enrolled_student_get_project(self):
        self.semester.add_enrolled_students(self.user)

        response = _get_project_request(self.visible_project.pk, self.user)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {'data': project_to_json(self.visible_project)},
            json_load_bytes(response.content))

        response = _get_project_request(self.hidden_project.pk, self.user)
        self.assertEqual(403, response.status_code)

    def test_get_project_not_found(self):
        response = _get_project_request(42, self.user)
        self.assertEqual(404, response.status_code)

    def test_nobody_user_get_project(self):
        # TODO: visible_to_non_enrolled_students field for project
        response = _get_project_request(self.visible_project.pk, self.user)
        self.assertEqual(403, response.status_code)

        response = _get_project_request(self.hidden_project.pk, self.user)
        self.assertEqual(403, response.status_code)


# -----------------------------------------------------------------------------

class PatchProjectRequestTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.admin = obj_ut.create_dummy_users()
        self.user = obj_ut.create_dummy_users()

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)
        self.project = obj_ut.create_dummy_projects(self.semester)

        self.course.add_course_admins(self.admin)

    def test_valid_patch_project_all_attributes(self):
        closing_time = (timezone.now() + datetime.timedelta(days=1)).replace(
            hour=23, minute=55, second=0, microsecond=0)

        request_content = {
            'data': {
                'type': 'project',
                'id': self.project.pk,
                'attributes': {
                    'visible_to_students': True,
                    'closing_time': closing_time,
                    'disallow_student_submissions': True,
                    'min_group_size': 2,
                    'max_group_size': 3,
                    'required_student_files': ['spam.cpp', 'eggs.cpp'],
                    'expected_student_file_patterns': [
                        ['test_*.cpp', 1, 5], ['cheese[0-9].txt', 0, 2]]
                }
            }
        }

        response = _patch_project_request(
            self.project.pk, request_content, self.admin)

        self.assertEqual(204, response.status_code)

        loaded_project = project_to_json(
            Project.objects.get(pk=self.project.pk))

        attributes = request_content['data']['attributes']
        attributes['expected_student_file_patterns'] = [
            Project.FilePatternTuple(*list_) for list_ in
            attributes['expected_student_file_patterns']
        ]

        for attribute, value in request_content['data']['attributes'].items():
            self.assertEqual(
                loaded_project['attributes'][attribute],
                value)

    def test_valid_patch_project_some_attributes(self):
        request_content = {
            'data': {
                'type': 'project',
                'id': self.project.pk,
                'attributes': {
                    'visible_to_students': True
                }
            }
        }

        response = _patch_project_request(
            self.project.pk, request_content, self.admin)

        self.assertEqual(204, response.status_code)

        loaded_project = Project.objects.get(pk=self.project.pk)
        self.assertTrue(loaded_project.visible_to_students)

    def test_patch_project_permission_denied(self):
        request_content = {
            'data': {
                'type': 'project',
                'id': self.project.pk,
                'attributes': {
                    'visible_to_students': True
                }
            }
        }

        response = _patch_project_request(
            self.project.pk, request_content, self.user)

        self.assertEqual(403, response.status_code)

    def test_patch_project_field_errors(self):
        request_content = {
            'data': {
                'type': 'project',
                'id': self.project.pk,
                'attributes': {
                    'min_group_size': 2,
                    'max_group_size': '1'
                }
            }
        }

        response = _patch_project_request(
            self.project.pk, request_content, self.admin)

        self.assertEqual(409, response.status_code)
        self.assertTrue('errors' in json_load_bytes(response.content))

    def test_patch_project_not_found(self):
        request_content = {
            'data': {
                'type': 'project',
                'id': 42,
                'attributes': {
                    'visible_to_students': True
                }
            }
        }

        response = _patch_project_request(
            42, request_content, self.admin)

        self.assertEqual(404, response.status_code)


# -----------------------------------------------------------------------------

class DeleteProjectRequestTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.user = obj_ut.create_dummy_users()

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)
        self.project = obj_ut.create_dummy_projects(self.semester)

    def test_valid_delete_project(self):
        self.course.add_course_admins(self.user)

        self.assertIsNotNone(self.project.pk)

        response = _delete_project_request(self.project.pk, self.user)
        self.assertEqual(204, response.status_code)

        with self.assertRaises(ObjectDoesNotExist):
            Project.objects.get(pk=self.project.pk)

    def test_delete_project_permission_denied(self):
        self.assertIsNotNone(self.project.pk)

        response = _delete_project_request(self.project.pk, self.user)
        self.assertEqual(403, response.status_code)

    def test_delete_project_not_found(self):
        response = _delete_project_request(42, self.user)
        self.assertEqual(404, response.status_code)


# -----------------------------------------------------------------------------

def _add_project_request(semester, project_name, user):
    url = '/projects/project/'
    data = {
        'data': {
            'type': 'project',
            'attributes': {
                'name': project_name
            },
            'relationships': {
                'semester': {
                    'data': {
                        'type': 'semester',
                        'id': semester.pk
                    }
                }
            }
        }
    }
    return process_post_request(url, data, user)


def _get_project_request(project_id, user):
    url = '/projects/project/{}/'.format(project_id)
    return process_get_request(url, user)


def _patch_project_request(project_id, data, user):
    url = '/projects/project/{}/'.format(project_id)
    return process_patch_request(url, data, user)


def _delete_project_request(project_id, user):
    url = '/projects/project/{}/'.format(project_id)
    return process_delete_request(url, user)
