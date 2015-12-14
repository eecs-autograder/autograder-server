import datetime
# import tempfile

from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse, resolve
from django.utils import timezone
from django.test import RequestFactory

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.core.tests.dummy_object_utils as obj_ut

from .utils import (
    process_get_request, process_post_request,
    process_patch_request, process_delete_request, json_load_bytes)

from autograder.core.frontend.json_api_serializers import (
    project_to_json, autograder_test_case_to_json)
from autograder.core.models import Project, AutograderTestCaseFactory

import autograder.core.shared.feedback_configuration as fbc


class _SetUpBase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.admin = obj_ut.create_dummy_users()

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)
        self.project = obj_ut.create_dummy_projects(self.semester)

        self.course.add_course_admins(self.admin)

        self.staff = obj_ut.create_dummy_users()
        self.project.semester.add_semester_staff(self.staff)

        self.enrolled = obj_ut.create_dummy_users()
        self.project.semester.add_enrolled_students(self.enrolled)

        self.nobody = obj_ut.create_dummy_users()


class AddProjectRequestTestCase(_SetUpBase):
    def setUp(self):
        super().setUp()

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
        for user in (self.staff, self.enrolled, self.nobody):
            response = _add_project_request(
                self.semester, self.new_project_name, user)
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


# -----------------------------------------------------------------------------

class GetProjectRequestTestCase(_SetUpBase):
    def setUp(self):
        super().setUp()

        self.visible_project = obj_ut.create_dummy_projects(self.semester)
        self.visible_project.visible_to_students = True
        self.visible_project.required_student_files = ['spam.cpp']
        self.visible_project.validate_and_save()

        self.hidden_project = obj_ut.create_dummy_projects(self.semester)
        self.hidden_project.required_student_files = ['spam.cpp']
        self.hidden_project.validate_and_save()

        for proj in (self.visible_project, self.hidden_project):
            for i in range(5):
                AutograderTestCaseFactory.validate_and_create(
                    'compiled_test_case',
                    name='test{}'.format(i), project=proj,
                    compiler='g++', files_to_compile_together=['spam.cpp'],
                    student_resource_files=proj.required_student_files,
                    executable_name='cheese')

    def test_course_admin_get_project(self):
        for project in (self.visible_project, self.hidden_project):
            response = _get_project_request(project.pk, self.admin)
            self.assertEqual(200, response.status_code)
            expected = {
                'data': project_to_json(project),
                'meta': {
                    'permissions': {
                        'is_staff': True,
                        'can_edit': True
                    },
                    'username': self.admin.username
                },
                'included': [
                    autograder_test_case_to_json(test_case)
                    for test_case in project.autograder_test_cases.all()
                ]
            }
            self.assertEqual(expected, json_load_bytes(response.content))

    def test_semester_staff_get_project(self):
        for project in (self.visible_project, self.hidden_project):
            response = _get_project_request(project.pk, self.staff)
            self.assertEqual(200, response.status_code)
            expected = {
                'data': project_to_json(project),
                'meta': {
                    'permissions': {
                        'is_staff': True,
                        'can_edit': False
                    },
                    'username': self.staff.username
                },
                'included': [
                    autograder_test_case_to_json(test_case)
                    for test_case in project.autograder_test_cases.all()
                ]
            }
            self.assertEqual(expected, json_load_bytes(response.content))

    def test_enrolled_student_get_project(self):
        response = _get_project_request(self.visible_project.pk, self.enrolled)
        self.assertEqual(200, response.status_code)
        expected = {
            'data': project_to_json(self.visible_project),
            'meta': {
                'permissions': {
                    'is_staff': False,
                    'can_edit': False
                },
                'username': self.enrolled.username
            }
        }
        expected['data']['attributes'].pop('project_files')
        self.assertEqual(expected, json_load_bytes(response.content))

        response = _get_project_request(self.hidden_project.pk, self.enrolled)
        self.assertEqual(403, response.status_code)

    def test_get_project_not_found(self):
        response = _get_project_request(42, self.admin)
        self.assertEqual(404, response.status_code)

    def test_nobody_user_get_project_forbidden(self):
        for project in (self.visible_project, self.hidden_project):
            response = _get_project_request(
                project.pk, self.nobody)
            self.assertEqual(403, response.status_code)

    def test_nobody_user_can_view_public_and_visible_project(self):
        self.visible_project.allow_submissions_from_non_enrolled_students = True
        self.visible_project.validate_and_save()

        response = _get_project_request(self.visible_project.pk, self.nobody)
        self.assertEqual(200, response.status_code)
        expected = {
            'data': project_to_json(self.visible_project),
            'meta': {
                'permissions': {
                    'is_staff': False,
                    'can_edit': False
                },
                'username': self.nobody.username
            }
        }
        expected['data']['attributes'].pop('project_files')
        self.assertEqual(expected, json_load_bytes(response.content))


def _get_project_request(project_id, user):
    url = '/projects/project/{}/'.format(project_id)
    return process_get_request(url, user)


# -----------------------------------------------------------------------------

class PatchProjectRequestTestCase(_SetUpBase):
    # def setUp(self):
    #     super().setUp()

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
                    'allow_submissions_from_non_enrolled_students': True,
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

        for attribute, value in attributes.items():
            self.assertEqual(loaded_project['attributes'][attribute], value)

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

        for user in (self.staff, self.enrolled, self.nobody):
            response = _patch_project_request(
                self.project.pk, request_content, user)
            self.assertEqual(403, response.status_code)

            loaded_project = Project.objects.get(pk=self.project.pk)
            self.assertEqual(
                project_to_json(loaded_project), project_to_json(self.project))

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

        loaded_project = Project.objects.get(pk=self.project.pk)
        self.assertEqual(
            project_to_json(loaded_project), project_to_json(self.project))

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


def _patch_project_request(project_id, data, user):
    url = '/projects/project/{}/'.format(project_id)
    return process_patch_request(url, data, user)


# -----------------------------------------------------------------------------

class DeleteProjectRequestTestCase(_SetUpBase):
    # def setUp(self):
    #     super().setUp()

    def test_valid_delete_project(self):
        self.course.add_course_admins(self.admin)

        self.assertIsNotNone(self.project.pk)

        response = _delete_project_request(self.project.pk, self.admin)
        self.assertEqual(204, response.status_code)

        with self.assertRaises(ObjectDoesNotExist):
            Project.objects.get(pk=self.project.pk)

    def test_delete_project_permission_denied(self):
        for user in (self.staff, self.enrolled, self.nobody):
            self.assertIsNotNone(self.project.pk)

            response = _delete_project_request(self.project.pk, user)
            self.assertEqual(403, response.status_code)

            loaded_project = Project.objects.get(pk=self.project.pk)
            self.assertEqual(
                project_to_json(loaded_project), project_to_json(self.project))

    def test_delete_project_not_found(self):
        response = _delete_project_request(42, self.admin)
        self.assertEqual(404, response.status_code)


def _delete_project_request(project_id, user):
    url = '/projects/project/{}/'.format(project_id)
    return process_delete_request(url, user)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class ProjectFileTestCase(_SetUpBase):
    def setUp(self):
        super().setUp()

        self.file = SimpleUploadedFile('spam.txt', b'spam egg sausage spam')
        self.project.add_project_file(self.file)

    def test_valid_add_project_file(self):
        new_file = SimpleUploadedFile('new_file', b"I'm a new file!")
        response = _add_project_file_request(
            self.project.pk, new_file, self.admin)

        self.assertEqual(201, response.status_code)

        loaded_project = Project.objects.get(pk=self.project.pk)
        self.assertTrue(loaded_project.has_file('new_file'))
        file_ = loaded_project.get_file('new_file')
        self.assertEqual(file_.read(), b"I'm a new file!")

        expected = {
            'filename': new_file.name,
            'size': new_file.size,
            'file_url': reverse(
                'project-file-handler', args=[self.project.pk, new_file.name])
        }

        self.assertEqual(expected, json_load_bytes(response.content))

    # def test_error_add_file_already_exists(self):
    #     response = _add_project_file_request(
    #         self.project.pk, self.file, self.admin)

    #     self.assertEqual

    def test_add_file_permission_denied(self):
        new_file = SimpleUploadedFile('new_file', b"Fiiiile")

        for user in (self.staff, self.enrolled, self.nobody):
            response = _add_project_file_request(
                self.project.pk, new_file, user)
            self.assertEqual(403, response.status_code)

            loaded_project = Project.objects.get(pk=self.project.pk)
            self.assertFalse(loaded_project.has_file('new_file'))

    def test_add_file_error(self):
        new_file = SimpleUploadedFile(
            '../very bad filename; echo "haxorz!"; #', b"bwa ha ha")
        response = _add_project_file_request(
            self.project.pk, new_file, self.admin)
        self.assertEqual(409, response.status_code)

        self.assertTrue('error' in json_load_bytes(response.content))

        self.assertFalse(self.project.has_file(new_file.name))

    def test_valid_get_project_file(self):
        for user in (self.admin, self.staff):
            response = _get_project_file_request(
                self.project.pk, self.file.name, user)

            self.assertEqual(200, response.status_code)
            self.file.seek(0)
            self.assertEqual(
                self.file.read(), b''.join(response.streaming_content))

    def test_get_project_file_permission_denied(self):
        for user in (self.enrolled, self.nobody):
            response = _get_project_file_request(
                self.project.pk, self.file.name, user)
            self.assertEqual(403, response.status_code)
            self.assertEqual(b'', response.content)

    def test_get_project_file_not_found(self):
        response = _get_project_file_request(
            self.project.pk, 'not_a_file', self.admin)
        self.assertEqual(404, response.status_code)

    def test_valid_delete_project_file(self):
        response = _delete_project_file_request(
            self.project.pk, self.file.name, self.admin)
        self.assertEqual(204, response.status_code)

        loaded_project = Project.objects.get(pk=self.project.pk)
        self.assertFalse(loaded_project.has_file(self.file.name))

    def test_delete_project_file_permission_denied(self):
        for user in (self.staff, self.enrolled, self.nobody):
            response = _delete_project_file_request(
                self.project.pk, self.file.name, user)
            self.assertEqual(403, response.status_code)

        self.assertTrue(self.project.has_file(self.file.name))

    def test_delete_project_file_not_found(self):
        response = _delete_project_file_request(
            self.project.pk, 'not_a_file', self.admin)
        self.assertEqual(404, response.status_code)


# -----------------------------------------------------------------------------

def _get_project_file_request(project_id, filename, user):
    url = '/projects/project/{}/file/{}/'.format(project_id, filename)
    return process_get_request(url, user)


def _add_project_file_request(project_id, file_, user):
    url = '/projects/project/{}/add-file/'.format(project_id)
    data = {'file': file_}

    request = RequestFactory().post(url, data)
    request.user = user

    resolved = resolve(request.path)
    return resolved.func(request, *resolved.args, **resolved.kwargs)


def _delete_project_file_request(project_id, filename, user):
    url = '/projects/project/{}/file/{}/'.format(project_id, filename)
    return process_delete_request(url, user)
