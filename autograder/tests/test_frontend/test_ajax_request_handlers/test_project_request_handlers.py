from django.core.exceptions import ObjectDoesNotExist

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.tests.dummy_object_utils as obj_ut

from .utils import (
    process_get_request, process_post_request,
    process_patch_request, json_load_bytes)

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

    def test_course_admin_get_project(self):
        self.fail()

    def test_semester_staff_get_project(self):
        self.fail()

    def test_enrolled_student_get_project(self):
        self.fail()

    def test_nobody_user_get_project(self):
        # TODO: visible_to_non_enrolled_students field for project
        self.fail()


# -----------------------------------------------------------------------------

class PatchProjectRequestTestCase(TemporaryFilesystemTestCase):
    def test_valid_patch_project(self):
        self.fail()

    def test_patch_project_permission_denied(self):
        self.fail()

    def test_patch_project_field_errors(self):
        self.fail()


# -----------------------------------------------------------------------------

class DeleteProjectRequestTestCase(TemporaryFilesystemTestCase):
    def test_valid_delete_project(self):
        self.fail()

    def test_delete_project_permission_denied(self):
        self.fail()


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
