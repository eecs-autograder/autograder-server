import itertools

from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist

from autograder.core.models import (
    AutograderTestCaseFactory, AutograderTestCaseBase)

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk


class GetUpdateDeleteAutograderTestCaseTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.admin = obj_ut.create_dummy_user()
        self.staff = obj_ut.create_dummy_user()
        self.enrolled = obj_ut.create_dummy_user()
        self.nobody = obj_ut.create_dummy_user()

        self.required_filenames = ['spam', 'egg']

        self.project = obj_ut.build_project(
            course_kwargs={'administrators': [self.admin]},
            semester_kwargs={
                'staff': [self.staff], 'enrolled_students': [self.enrolled]},
            project_kwargs={
                'allow_submissions_from_non_enrolled_students': True,
                'visible_to_students': True,
                'required_student_files': self.required_filenames})

        self.semester = self.project.semester
        self.course = self.semester.course

        self.project_url = reverse(
            'project:get', kwargs={'pk': self.project.pk})

        self.test_case = AutograderTestCaseFactory.validate_and_create(
            'compiled_and_run_test_case',
            name='testy', project=self.project,
            expected_return_code=0,
            compiler='g++',
            files_to_compile_together=self.required_filenames,
            student_resource_files=self.required_filenames,
            executable_name='prog')

        self.test_url = reverse(
            'ag-test:get', kwargs={'pk': self.test_case.pk})

    def test_course_admin_or_semester_staff_get_test_case(self):
        for user in self.admin, self.staff:
            client = MockClient(user)
            response = client.get(self.test_url)

            self.assertEqual(200, response.status_code)

            expected_content = {
                "urls": {
                    "self": self.test_url,
                    "project": self.project_url
                }
            }
            expected_content.update(self.test_case.to_json())

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_other_get_test_case_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.get(self.test_url)

            self.assertEqual(403, response.status_code)

    # -------------------------------------------------------------------------

    def test_course_admin_edit_test_case_some_fields(self):
        args = {
            'files_to_compile_together': self.required_filenames[:1],
            'name': 'westy',
            'expected_standard_output': 'spamegg\n'
        }

        client = MockClient(self.admin)
        response = client.patch(self.test_url, args)

        self.assertEqual(200, response.status_code)

        self.assertEqual(args, json_load_bytes(response.content))

        loaded = AutograderTestCaseBase.objects.get(pk=self.test_case.pk)
        for arg, value in args.items():
            self.assertEqual(value, getattr(loaded, arg))

        # sanity check that other fields weren't edited
        self.assertEqual(
            self.test_case.expected_return_code, loaded.expected_return_code)

    def test_course_admin_edit_test_case_all_fields(self):
        self.fail()
        args = {
            'files_to_compile_together': self.required_filenames[:1],
            'name': 'westy',
            'expected_standard_output': 'spamegg\n'
        }

        client = MockClient(self.admin)
        response = client.patch(self.test_url, args)

        self.assertEqual(200, response.status_code)

        self.assertEqual(args, json_load_bytes(response.content))

        loaded = AutograderTestCaseBase.objects.get(pk=self.test_case.pk)
        for arg, value in args.items():
            self.assertEqual(value, getattr(loaded, arg))

        # sanity check that other fields weren't edited
        self.assertEqual(
            self.test_case.expected_return_code, loaded.expected_return_code)

    def test_course_admin_edit_test_case_invalid_settings(self):
        args = {
            'files_to_compile_together': ['not_a_student_file'],
            'name': 'oopsy'
        }

        client = MockClient(self.admin)
        response = client.patch(self.test_url, args)

        self.assertEqual(400, response.status_code)

        loaded = AutograderTestCaseBase.objects.get(pk=self.test_case.pk)

        for arg in args:
            self.assertEqual(
                getattr(self.test_case, arg), getattr(loaded, arg))

    def test_other_edit_test_case_permission_denied(self):
        for user in self.staff, self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.patch(self.test_url, {'name': 'spam'})

            self.assertEqual(403, response.status_code)

            loaded = AutograderTestCaseBase.objects.get(pk=self.test_case.pk)
            self.assertEqual(self.test_case.name, loaded.name)

    # -------------------------------------------------------------------------

    def test_course_admin_delete_test_case(self):
        client = MockClient(self.admin)
        response = client.delete(self.test_url)

        self.assertEqual(204, response.status_code)

        with self.assertRaises(ObjectDoesNotExist):
            AutograderTestCaseBase.objects.get(pk=self.test_case.pk)

    def test_other_delete_test_case_permission_denied(self):
        for user in self.staff, self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.delete(self.test_url)

            self.assertEqual(403, response.status_code)

            AutograderTestCaseBase.objects.get(pk=self.test_case.pk)
