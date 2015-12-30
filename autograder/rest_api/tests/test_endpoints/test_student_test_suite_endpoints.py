import itertools

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist

from autograder.core.models import (
    StudentTestSuiteFactory, StudentTestSuiteBase, Project)

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk


class GetUpdateDeleteStudentTestSuiteTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.admin = obj_ut.create_dummy_user()
        self.staff = obj_ut.create_dummy_user()
        self.enrolled = obj_ut.create_dummy_user()
        self.nobody = obj_ut.create_dummy_user()

        self.project = obj_ut.build_project(
            course_kwargs={'administrators': [self.admin]},
            semester_kwargs={
                'staff': [self.staff], 'enrolled_students': [self.enrolled]},
            project_kwargs={
                'allow_submissions_from_non_enrolled_students': True,
                'visible_to_students': True,
                'expected_student_file_patterns': [
                    Project.FilePatternTuple('test_*.cpp', 0, 3)
                ]})

        self.semester = self.project.semester
        self.course = self.semester.course

        self.project_url = reverse(
            'project:get', kwargs={'pk': self.project.pk})

        self.points_per_buggy = 2
        self.points_for_suite = 4

        proj_files = [
            SimpleUploadedFile('correct.cpp', b'blah'),
            SimpleUploadedFile('buggy1.cpp', b'buuug'),
            SimpleUploadedFile('buggy2.cpp', b'buuug')
        ]
        for file_ in proj_files:
            self.project.add_project_file(file_)

        self.suite = StudentTestSuiteFactory.validate_and_create(
            'compiled_student_test_suite',
            name='suitey',
            project=self.project,
            student_test_case_filename_pattern='test_*.cpp',
            correct_implementation_filename='correct.cpp',
            buggy_implementation_filenames=['buggy1.cpp', 'buggy2.cpp'],
        )

        self.suite_url = reverse(
            'suite:get', kwargs={'pk': self.suite.pk})

    def test_course_admin_or_semester_staff_get_suite(self):
        for user in self.admin, self.staff:
            client = MockClient(user)
            response = client.get(self.suite_url)

            self.assertEqual(200, response.status_code)

            expected_content = {
                "urls": {
                    "self":     self.suite_url,
                    "project": self.project_url,
                }
            }
            expected_content.update(self.suite.to_json())

            self.assertEqual(
                expected_content, json_load_bytes(response.content))

    def test_other_get_suite_permission_denied(self):
        for user in self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.get(self.suite_url)

            self.assertEqual(403, response.status_code)

    # -------------------------------------------------------------------------

    def test_course_admin_edit_suite(self):
        args = {
            'name': 'spammy',
            'buggy_implementation_filenames': (
                self.suite.buggy_implementation_filenames[:1]),
            'compiler_flags': ['flag', 'stag']
        }

        client = MockClient(self.admin)
        response = client.patch(self.suite_url, args)

        self.assertEqual(200, response.status_code)
        self.assertEqual(args, json_load_bytes(response.content))

        loaded = StudentTestSuiteBase.objects.get(pk=self.suite.pk)
        for arg, value in args.items():
            self.assertEqual(value, getattr(loaded, arg))

    def test_course_admin_edit_suite_invalid_settings(self):
        args = {
            'name': 'sausage',
            'buggy_implementation_filenames': ['not_a_file']
        }

        client = MockClient(self.admin)
        response = client.patch(self.suite_url, args)

        self.assertEqual(400, response.status_code)

        loaded = StudentTestSuiteBase.objects.get(pk=self.suite.pk)
        for arg in args:
            self.assertEqual(
                getattr(self.suite, arg), getattr(loaded, arg))

    def test_other_edit_suite_permission_denied(self):
        args = {
            'name': 'spammy',
            'buggy_implementation_filenames': (
                self.suite.buggy_implementation_filenames[:1]),
            'compiler_flags': ['flag', 'stag']
        }

        for user in self.staff, self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.patch(self.suite_url, args)
            self.assertEqual(403, response.status_code)

            loaded = StudentTestSuiteBase.objects.get(pk=self.suite.pk)
            for arg in args:
                self.assertEqual(
                    getattr(self.suite, arg), getattr(loaded, arg))

    # -------------------------------------------------------------------------

    def test_course_admin_delete_suite(self):
        client = MockClient(self.admin)
        response = client.delete(self.suite_url)

        self.assertEqual(204, response.status_code)
        with self.assertRaises(ObjectDoesNotExist):
            StudentTestSuiteBase.objects.get(pk=self.suite.pk)

    def test_other_delete_suite_permission_denied(self):
        for user in self.staff, self.enrolled, self.nobody:
            client = MockClient(user)
            response = client.delete(self.suite_url)

            self.assertEqual(403, response.status_code)
            StudentTestSuiteBase.objects.get(pk=self.suite.pk)
