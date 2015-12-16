from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.core.tests.dummy_object_utils as obj_ut

from .utils import (
    process_get_request, process_post_request,
    process_patch_request, process_delete_request, json_load_bytes)

from autograder.core.frontend.json_api_serializers import (
    project_to_json, autograder_test_case_to_json)
from autograder.core.models import (
    AutograderTestCaseBase, AutograderTestCaseFactory)

import autograder.core.shared.feedback_configuration as fbc


class _SetUpBase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.admin = obj_ut.create_dummy_user()
        self.staff = obj_ut.create_dummy_user()
        self.enrolled = obj_ut.create_dummy_user()
        self.nobody = obj_ut.create_dummy_user()

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)

        self.course.add_course_admins(self.admin)
        self.semester.add_semester_staff(self.staff)
        self.semester.add_enrolled_students(self.enrolled)

        self.project = obj_ut.create_dummy_projects(self.semester)

        self.project.required_student_files = ['spam.cpp', 'egg.cpp']
        self.project.add_project_file(
            SimpleUploadedFile('cheese.txt', b'cheeeese'))
        self.project.validate_and_save()

        self.ag_test_json = {
            'data': {
                'type': 'compiled_and_run_test_case',
                'attributes': {
                    'name': 'test',
                    'command_line_arguments': ['spam'],
                    'standard_input': 'eggs',
                    'test_resource_files': ['cheese.txt'],
                    'student_resource_files': self.project.required_student_files,
                    'time_limit': 5,
                    'expected_return_code': 0,
                    'expect_any_nonzero_return_code': False,
                    'expected_standard_output': 'asdlkjf',
                    'expected_standard_error_output': 'qoweiur',
                    'use_valgrind': True,
                    'valgrind_flags': ['spam', 'egg'],
                    'compiler': 'g++',
                    'compiler_flags': ['-Wall'],
                    'files_to_compile_together': ['spam.cpp', 'egg.cpp'],
                    'executable_name': 'sausage',
                    'points_for_correct_return_code': 1,
                    'points_for_correct_output': 2,
                    'deduction_for_valgrind_errors': 3,
                    'points_for_compilation_success': 4,
                    'feedback_configuration': (
                        fbc.AutograderTestCaseFeedbackConfiguration().to_json()
                    )
                },
                'relationships': {
                    'project': {
                        'data': project_to_json(
                            self.project, all_fields=False)
                    }
                }
            }
        }
        self.ag_test_starter = AutograderTestCaseFactory.new_instance(
            'compiled_and_run_test_case',
            project=self.project, **self.ag_test_json['data']['attributes'])

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class AddAutograderTestCaseRequestTestCase(_SetUpBase):
    def setUp(self):
        super().setUp()

    def test_valid_add_compiled_test(self):
        response = _add_ag_test_request(
            self.project, self.ag_test_json, self.admin)
        self.assertEqual(201, response.status_code)

        loaded_test = AutograderTestCaseBase.objects.get(
            name=self.ag_test_starter.name, project=self.project)
        expected = {
            'data': autograder_test_case_to_json(loaded_test)
        }

        self.assertEqual(expected, json_load_bytes(response.content))

    def test_add_test_permission_denied(self):
        for user in (self.staff, self.enrolled, self.nobody):
            response = _add_ag_test_request(
                self.project, self.ag_test_json, user)
            self.assertEqual(403, response.status_code)

    def test_error_add_duplicate_test(self):
        self.ag_test_starter.validate_and_save()
        response = _add_ag_test_request(
            self.project, self.ag_test_json, self.admin)
        self.assertEqual(409, response.status_code)

    def test_error_bad_test_type(self):
        self.ag_test_json['data']['type'] = 'not_a_test_type'
        response = _add_ag_test_request(
            self.project, self.ag_test_json, self.admin)
        self.assertEqual(400, response.status_code)


def _add_ag_test_request(project, data, user):
    url = '/ag-test-cases/ag-test-case/'
    return process_post_request(url, data, user)

# -----------------------------------------------------------------------------


class GetAutograderTestCaseRequestTestCase(_SetUpBase):
    def setUp(self):
        super().setUp()

        self.ag_test_starter.validate_and_save()

    def test_course_admin_or_staff_get_test_case(self):
        for user, is_admin in ((self.admin, True), (self.staff, False)):
            response = _get_ag_test_request(self.ag_test_starter.pk, user)
            self.assertEqual(200, response.status_code)

            expected = {
                'data': autograder_test_case_to_json(self.ag_test_starter),
                'meta': {
                    'permissions': {
                        'can_edit': is_admin,
                        'can_delete': is_admin
                    }
                }
            }
            self.assertEqual(expected, json_load_bytes(response.content))

    def test_get_test_case_permission_denied(self):
        for user in (self.enrolled, self.nobody):
            response = _get_ag_test_request(self.ag_test_starter.pk, user)
            self.assertEqual(403, response.status_code)

    def test_get_test_case_not_found(self):
        response = _get_ag_test_request(42, self.admin)
        self.assertEqual(404, response.status_code)


def _get_ag_test_request(test_id, user):
    url = '/ag-test-cases/ag-test-case/{}/'.format(test_id)
    return process_get_request(url, user)

# -----------------------------------------------------------------------------


class PatchAutograderTestCaseRequestTestCase(_SetUpBase):
    def setUp(self):
        super().setUp()
        self.ag_test_starter.validate_and_save()

    def test_valid_patch_test_case_all_attributes(self):
        request_content = {
            'data': {
                'type': 'compiled_and_run_test_case',
                'id': self.ag_test_starter.pk,
                'attributes': {
                    'command_line_arguments': ['eggs'],
                    'standard_input': 'spam',
                    'test_resource_files': [],
                    'time_limit': 2,
                    'expected_return_code': None,
                    'expect_any_nonzero_return_code': True,
                    'expected_standard_output': 'woooah',
                    'expected_standard_error_output': '',
                    'use_valgrind': False,
                    'valgrind_flags': ['--leak_check=full'],
                    'compiler': 'g++',
                    'compiler_flags': ['-Wall', '-Wextra'],
                    'files_to_compile_together': ['egg.cpp'],
                    'executable_name': 'baked_beans',
                    'points_for_correct_return_code': 2,
                    'points_for_correct_output': 3,
                    'deduction_for_valgrind_errors': 4,
                    'points_for_compilation_success': 5,
                    'feedback_configuration': (
                        (fbc.AutograderTestCaseFeedbackConfiguration.
                            get_max_feedback().to_json()))
                }
            }
        }

        response = _patch_ag_test_request(
            self.ag_test_starter.pk, request_content, self.admin)
        self.assertEqual(204, response.status_code)

        loaded_test = AutograderTestCaseBase.objects.get(
            name=self.ag_test_starter.name, project=self.project)
        loaded_test_json = autograder_test_case_to_json(loaded_test)

        attributes = request_content['data']['attributes']
        for attribute, value in attributes.items():
            self.assertEqual(loaded_test_json['attributes'][attribute], value)

    def test_valid_patch_test_case_some_attributes(self):
        request_content = {
            'data': {
                'type': 'compiled_and_run_test_case',
                'id': self.ag_test_starter.pk,
                'attributes': {
                    'time_limit': 2
                }
            }
        }

        response = _patch_ag_test_request(
            self.ag_test_starter.pk, request_content, self.admin)
        self.assertEqual(204, response.status_code)

        loaded_test = AutograderTestCaseBase.objects.get(
            name=self.ag_test_starter.name, project=self.project)

        self.assertEqual(2, loaded_test.time_limit)

    def test_patch_test_case_permisison_denied(self):
        request_content = {
            'data': {
                'type': 'compiled_and_run_test_case',
                'id': self.ag_test_starter.pk,
                'attributes': {
                    'time_limit': 2
                }
            }
        }
        for user in (self.staff, self.enrolled, self.nobody):
            response = _patch_ag_test_request(
                self.ag_test_starter.pk, request_content, user)
            self.assertEqual(403, response.status_code)

            loaded = AutograderTestCaseBase.objects.get(
                name=self.ag_test_starter.name, project=self.project)
            self.assertEqual(
                autograder_test_case_to_json(self.ag_test_starter),
                autograder_test_case_to_json(loaded))

    def test_patch_test_case_field_errors(self):
        request_content = {
            'data': {
                'type': 'compiled_and_run_test_case',
                'id': self.ag_test_starter.pk,
                'attributes': {
                    'time_limit': 0
                }
            }
        }

        response = _patch_ag_test_request(
            self.ag_test_starter.pk, request_content, self.admin)
        self.assertEqual(409, response.status_code)

        loaded = AutograderTestCaseBase.objects.get(
            name=self.ag_test_starter.name, project=self.project)
        self.assertEqual(
            autograder_test_case_to_json(self.ag_test_starter),
            autograder_test_case_to_json(loaded))

    def test_patch_test_case_not_found(self):
        request_content = {
            'data': {
                'type': 'compiled_and_run_test_case',
                'id': 42,
                'attributes': {
                    'time_limit': 2
                }
            }
        }

        response = _patch_ag_test_request(
            42, request_content, self.admin)
        self.assertEqual(404, response.status_code)


def _patch_ag_test_request(test_id, data, user):
    url = '/ag-test-cases/ag-test-case/{}/'.format(test_id)
    return process_patch_request(url, data, user)

# -----------------------------------------------------------------------------


class DeleteAutograderTestCaseRequestTestCase(_SetUpBase):
    def setUp(self):
        super().setUp()
        self.ag_test_starter.validate_and_save()

    def test_valid_delete_test_case(self):
        self.assertIsNotNone(self.ag_test_starter.pk)

        response = _delete_ag_test_request(self.ag_test_starter.pk, self.admin)
        self.assertEqual(204, response.status_code)

        with self.assertRaises(ObjectDoesNotExist):
            AutograderTestCaseBase.objects.get(
                name=self.ag_test_starter.name, project=self.project)

    def test_delete_project_permission_denied(self):
        for user in (self.staff, self.enrolled, self.nobody):
            response = _delete_ag_test_request(self.ag_test_starter.pk, user)
            self.assertEqual(403, response.status_code)

            loaded = AutograderTestCaseBase.objects.get(
                name=self.ag_test_starter.name, project=self.project)

            self.assertEqual(
                autograder_test_case_to_json(loaded),
                autograder_test_case_to_json(self.ag_test_starter))

    def test_delete_project_not_found(self):
        response = _delete_ag_test_request(42, self.admin)
        self.assertEqual(404, response.status_code)


def _delete_ag_test_request(test_id, user):
    url = '/ag-test-cases/ag-test-case/{}/'.format(test_id)
    return process_delete_request(url, user)
