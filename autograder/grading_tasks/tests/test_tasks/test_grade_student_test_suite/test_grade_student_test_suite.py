import os
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import tag

import autograder.core.models as ag_models
from autograder.core import constants
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build

from autograder.grading_tasks import tasks


@tag('slow', 'sandbox')
@mock.patch('autograder.grading_tasks.tasks.utils.time.sleep')
class EECS280StyleStudentTestGradingTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.files_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'eecs280_student_test_grading')
        project_filenames = ['proj_module.h', 'proj_module.cpp',
                             'unit_test_framework.h', 'unit_test_framework.cpp',
                             'Makefile']

        self.project = obj_build.make_project()

        for filename in project_filenames:
            full_path = os.path.join(self.files_dir, filename)
            with open(full_path, 'rb') as f:
                file_obj = SimpleUploadedFile(filename, f.read())
            ag_models.UploadedFile.objects.validate_and_create(
                project=self.project, file_obj=file_obj)

        ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            project=self.project,
            pattern='student_tests.cpp')

        self.bugs_exposed = ['RETURN_42_BUG', 'RETURN_TRUE_BUG', 'INFINITE_LOOP_BUG']
        self.bugs_not_exposed = ['RETURN_3_BUG']
        self.student_suite = ag_models.StudentTestSuite.objects.validate_and_create(
            name='EECS 280 Student Tests', project=self.project,
            project_files_needed=self.project.uploaded_files.all(),
            student_files_needed=self.project.expected_student_file_patterns.all(),
            buggy_impl_names=self.bugs_exposed + self.bugs_not_exposed,
            setup_command={
                'cmd': 'make student_tests.exe',
                'process_spawn_limit': constants.MAX_PROCESS_LIMIT,
            },
            get_student_test_names_command={
                'cmd': 'make -s get_test_names',
                'process_spawn_limit': constants.MAX_PROCESS_LIMIT,
            },
            student_test_validity_check_command={
                'cmd': 'make ${student_test_name}.validity_check',
                'process_spawn_limit': constants.MAX_PROCESS_LIMIT,
            },
            grade_buggy_impl_command={
                'cmd': 'make CPPFLAGS=-D${buggy_impl_name} ${student_test_name}.with_buggy_impl',
                'process_spawn_limit': constants.MAX_PROCESS_LIMIT,
            },
            points_per_exposed_bug=1)  # type: ag_models.StudentTestSuite

        with open(os.path.join(self.files_dir, 'student_tests.cpp'), 'rb') as f:
            self.submission = obj_build.build_submission(
                submitted_files=[SimpleUploadedFile('student_tests.cpp', f.read())],
                submission_group=obj_build.make_group(project=self.project))

        self.valid_tests = ['test_return_42', 'test_return_true']
        self.invalid_tests = ['incorrectly_test_return3', 'this_test_times_out']
        self.timeout_tests = ['this_test_times_out']
        self.all_tests = set(self.valid_tests + self.invalid_tests + self.timeout_tests)

    def test_grade_non_deferred(self, *args):
        tasks.grade_submission(self.submission.pk)

        result = ag_models.StudentTestSuiteResult.objects.get(
            student_test_suite=self.student_suite)

        self.assertEqual(0, result.setup_result.return_code)

        print(result.student_tests)
        print(result.invalid_tests)
        self.assertCountEqual(self.all_tests, result.student_tests)
        self.assertCountEqual(self.invalid_tests, result.invalid_tests)
        self.assertCountEqual(self.timeout_tests, result.timed_out_tests)
        self.assertCountEqual(self.bugs_exposed, result.bugs_exposed)

        with result.setup_result.open_stdout() as f:
            print('setup_result.open_stdout')
            print(f.read().decode())
        with result.setup_result.open_stderr() as f:
            print('setup_result.open_stderr')
            print(f.read().decode())
        with result.open_validity_check_stdout() as f:
            print('open_validity_check_stdout')
            print(f.read().decode())
        with result.open_validity_check_stderr() as f:
            print('open_validity_check_stderr')
            print(f.read().decode())
        with result.open_grade_buggy_impls_stdout() as f:
            print('open_grade_buggy_impls_stdout')
            print(f.read().decode())
        with result.open_grade_buggy_impls_stderr() as f:
            print('open_grade_buggy_impls_stderr')
            print(f.read().decode())

    def test_grade_deferred(self, *args):
        self.student_suite.validate_and_update(deferred=True)
        tasks.grade_submission(self.submission.pk)

        result = ag_models.StudentTestSuiteResult.objects.get(
            student_test_suite=self.student_suite)

        self.assertEqual(0, result.setup_result.return_code)

        print(result.student_tests)
        print(result.invalid_tests)
        self.assertCountEqual(self.all_tests, result.student_tests)
        self.assertCountEqual(self.invalid_tests, result.invalid_tests)
        self.assertCountEqual(self.timeout_tests, result.timed_out_tests)
        self.assertCountEqual(self.bugs_exposed, result.bugs_exposed)

    def test_setup_command_fails_no_tests_discovered(self, *args):
        self.student_suite.setup_command.validate_and_update(cmd='false')

        tasks.grade_submission(self.submission.pk)
        result = ag_models.StudentTestSuiteResult.objects.get(
            student_test_suite=self.student_suite)

        self.assertNotEqual(0, result.setup_result.return_code)

        self.assertEqual([], result.bugs_exposed)
        self.assertEqual([], result.student_tests)
        self.assertEqual([], result.invalid_tests)
        self.assertEqual([], result.timed_out_tests)

    def test_setup_command_times_out_no_tests_discovered(self, *args):
        self.student_suite.setup_command.validate_and_update(cmd='sleep 10')
        with mock.patch('autograder.core.constants.MAX_SUBPROCESS_TIMEOUT', new=1):
            tasks.grade_submission(self.submission.pk)

            result = ag_models.StudentTestSuiteResult.objects.get(
                student_test_suite=self.student_suite)
            self.assertTrue(result.setup_result.timed_out)

            self.assertEqual([], result.bugs_exposed)
            self.assertEqual([], result.student_tests)
            self.assertEqual([], result.invalid_tests)
            self.assertEqual([], result.timed_out_tests)

    def test_non_unicode_chars_in_test_names(self, *args):
        self.fail()

    def test_no_setup_command(self, *args):
        self.fail()
