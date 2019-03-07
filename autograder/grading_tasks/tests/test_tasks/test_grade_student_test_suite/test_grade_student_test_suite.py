import os
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import tag

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core import constants
from autograder.grading_tasks import tasks
from autograder.utils.testing import UnitTestBase


@tag('slow', 'sandbox')
@mock.patch('autograder.grading_tasks.tasks.utils.time.sleep')
class EECS280StyleStudentTestGradingIntegrationTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.files_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'eecs280_student_test_grading')
        instructor_filenames = [
            'proj_module.h', 'proj_module.cpp',
            'unit_test_framework.h', 'unit_test_framework.cpp',
            'Makefile'
        ]

        self.project = obj_build.make_project()

        for filename in instructor_filenames:
            full_path = os.path.join(self.files_dir, filename)
            with open(full_path, 'rb') as f:
                file_obj = SimpleUploadedFile(filename, f.read())
            ag_models.InstructorFile.objects.validate_and_create(
                project=self.project, file_obj=file_obj)

        ag_models.ExpectedStudentFile.objects.validate_and_create(
            project=self.project,
            pattern='student_tests.cpp')

        self.bugs_exposed = ['RETURN_42_BUG', 'RETURN_TRUE_BUG', 'INFINITE_LOOP_BUG']
        self.bugs_not_exposed = ['RETURN_3_BUG']
        self.student_suite = ag_models.StudentTestSuite.objects.validate_and_create(
            name='EECS 280 Student Tests', project=self.project,
            instructor_files_needed=self.project.instructor_files.all(),
            student_files_needed=self.project.expected_student_files.all(),
            buggy_impl_names=self.bugs_exposed + self.bugs_not_exposed,

            use_setup_command=True,
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
                'cmd': ('make student_test=${student_test_name} '
                        'bug_name=${buggy_impl_name} buggy_impl'),
                'process_spawn_limit': constants.MAX_PROCESS_LIMIT,
            },
            points_per_exposed_bug=1)  # type: ag_models.StudentTestSuite

        with open(os.path.join(self.files_dir, 'student_tests.cpp'), 'rb') as f:
            self.submission = obj_build.make_submission(
                submitted_files=[SimpleUploadedFile('student_tests.cpp', f.read())],
                group=obj_build.make_group(project=self.project))

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

        self.assertEqual(0, result.get_test_names_result.return_code)

        with open(result.get_test_names_result.stdout_filename) as f:
            print('get_test_names_result.stdout_filename')
            print(f.read())
        with open(result.get_test_names_result.stderr_filename) as f:
            print('get_test_names_result.stderr_filename')
            print(f.read())

        with open(result.setup_result.stdout_filename) as f:
            print('setup_result stdout')
            print(f.read())
        with open(result.setup_result.stderr_filename) as f:
            print('setup_result stderr')
            print(f.read())

        with open(result.get_test_names_result.stdout_filename) as f:
            print('get_test_names_result stdout')
            print(f.read())
        with open(result.get_test_names_result.stderr_filename) as f:
            print('get_test_names_result stderr')
            print(f.read())

        with open(result.validity_check_stdout_filename) as f:
            print('open_validity_check_stdout')
            print(f.read())
        with open(result.validity_check_stderr_filename) as f:
            print('open_validity_check_stderr')
            print(f.read())

        with open(result.grade_buggy_impls_stdout_filename) as f:
            print('open_grade_buggy_impls_stdout')
            print(f.read())
        with open(result.grade_buggy_impls_stderr_filename) as f:
            print('open_grade_buggy_impls_stderr')
            print(f.read())

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

        with open(result.get_test_names_result.stdout_filename) as f:
            self.assertEqual('', f.read())
        with open(result.get_test_names_result.stderr_filename) as f:
            self.assertEqual('', f.read())

        with open(result.validity_check_stdout_filename) as f:
            self.assertEqual('', f.read())
        with open(result.validity_check_stderr_filename) as f:
            self.assertEqual('', f.read())

        with open(result.grade_buggy_impls_stdout_filename) as f:
            self.assertEqual('', f.read())
        with open(result.grade_buggy_impls_stderr_filename) as f:
            self.assertEqual('', f.read())

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

            with open(result.get_test_names_result.stdout_filename) as f:
                self.assertEqual('', f.read())
            with open(result.get_test_names_result.stderr_filename) as f:
                self.assertEqual('', f.read())

            with open(result.validity_check_stdout_filename) as f:
                self.assertEqual('', f.read())
            with open(result.validity_check_stderr_filename) as f:
                self.assertEqual('', f.read())

            with open(result.grade_buggy_impls_stdout_filename) as f:
                self.assertEqual('', f.read())
            with open(result.grade_buggy_impls_stderr_filename) as f:
                self.assertEqual('', f.read())


@tag('slow', 'sandbox')
@mock.patch('autograder.grading_tasks.tasks.utils.time.sleep')
class StudentTestCaseGradingEdgeCaseTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()
        self.submission = obj_build.make_submission(
            group=obj_build.make_group(project=self.project))

    def test_non_unicode_chars_in_test_names(self, *args):
        non_unicode = b'test\x80 test2 test3'
        escaped_names = non_unicode.decode(errors='backslashreplace').split()
        instructor_file = ag_models.InstructorFile.objects.validate_and_create(
            file_obj=SimpleUploadedFile('test_names', non_unicode),
            project=self.project)

        student_suite = ag_models.StudentTestSuite.objects.validate_and_create(
            name='qeoriuqewrpqiuerqopwr',
            project=self.project,
            instructor_files_needed=[instructor_file],
            get_student_test_names_command={
                'cmd': 'cat {}'.format(instructor_file.name)
            }
        )
        tasks.grade_submission(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

        result = ag_models.StudentTestSuiteResult.objects.get(student_test_suite=student_suite)
        self.assertIsNone(result.setup_result)

        self.assertEqual(0, result.get_test_names_result.return_code)
        self.assertSequenceEqual(escaped_names, result.student_tests)
        self.assertSequenceEqual([], result.invalid_tests)

    def test_too_many_student_tests(self, *args):
        tests = ['test1', 'test2', 'test3']
        student_suite = ag_models.StudentTestSuite.objects.validate_and_create(
            name='too maaaany',
            project=self.project,
            get_student_test_names_command={
                'cmd': 'echo {}'.format(' '.join(tests))
            },
            max_num_student_tests=1
        )
        tasks.grade_submission(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

        result = ag_models.StudentTestSuiteResult.objects.get(student_test_suite=student_suite)
        self.assertEqual(tests[:1], result.student_tests)
        self.assertEqual(tests[1:], result.discarded_tests)

    def test_no_setup_command(self, *args):
        test_names = 'test1 test2 test3'

        student_suite = ag_models.StudentTestSuite.objects.validate_and_create(
            name='sweet',
            project=self.project,
            get_student_test_names_command={
                'cmd': 'echo {}'.format(test_names)
            }
        )
        tasks.grade_submission(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

        result = ag_models.StudentTestSuiteResult.objects.get(
            student_test_suite=student_suite)
        self.assertIsNone(result.setup_result)

        self.assertEqual(0, result.get_test_names_result.return_code)
        self.assertSequenceEqual(test_names.split(), result.student_tests)
        self.assertSequenceEqual([], result.invalid_tests)

    def test_get_test_names_stdout_and_stderr(self, *args):
        test_names = 'test1 test2 test3'
        stderr = 'stderry'
        student_suite = ag_models.StudentTestSuite.objects.validate_and_create(
            name='sweet',
            project=self.project,
            get_student_test_names_command={
                'cmd': 'bash -c "printf \'{}\'; printf \'{}\' >&2"'.format(test_names, stderr)
            }
        )
        tasks.grade_submission(self.submission.pk)

        result = ag_models.StudentTestSuiteResult.objects.get(
            student_test_suite=student_suite)

        self.assertEqual(0, result.get_test_names_result.return_code)
        self.assertSequenceEqual(test_names.split(), result.student_tests)

        with open(result.get_test_names_result.stdout_filename) as f:
            self.assertEqual(test_names, f.read())

        with open(result.get_test_names_result.stderr_filename) as f:
            self.assertEqual(stderr, f.read())

    def test_get_test_names_return_code_nonzero(self, *args):
        test_names = 'test1 test2 test3'
        stderr = 'stderry'
        student_suite = ag_models.StudentTestSuite.objects.validate_and_create(
            name='sweet',
            project=self.project,
            get_student_test_names_command={
                'cmd': 'bash -c "printf \'{}\'; printf \'{}\' >&2; false"'.format(
                    test_names, stderr)
            }
        )
        tasks.grade_submission(self.submission.pk)

        result = ag_models.StudentTestSuiteResult.objects.get(
            student_test_suite=student_suite)

        self.assertNotEqual(0, result.get_test_names_result.return_code)
        self.assertSequenceEqual([], result.student_tests)

        with open(result.get_test_names_result.stdout_filename) as f:
            self.assertEqual(test_names, f.read())

        with open(result.get_test_names_result.stderr_filename) as f:
            self.assertEqual(stderr, f.read())

        # Make sure that validity check and buggy impl grading didn't happen
        with open(result.validity_check_stdout_filename) as f:
            self.assertEqual('', f.read())

        with open(result.validity_check_stderr_filename) as f:
            self.assertEqual('', f.read())

        with open(result.grade_buggy_impls_stdout_filename) as f:
            self.assertEqual('', f.read())

        with open(result.grade_buggy_impls_stderr_filename) as f:
            self.assertEqual('', f.read())

    def test_non_default_docker_image(self, *args):
        eecs490_image = ag_models.SandboxDockerImage.objects.get_or_create(
            name='eecs490_image', display_name='EECS 490', tag='jameslp/eecs490')[0]

        student_suite = ag_models.StudentTestSuite.objects.validate_and_create(
            name='suito',
            project=self.project,
            sandbox_docker_image=eecs490_image,
            use_setup_command=True,
            setup_command={
                'cmd': 'racket --version'
            }
        )

        tasks.grade_student_test_suite_impl(student_suite, self.submission)

        result = self.submission.student_test_suite_results.get(student_test_suite=student_suite)
        self.assertEqual(0, result.setup_result.return_code)

    def test_network_access_allowed(self, *args):
        student_suite = ag_models.StudentTestSuite.objects.validate_and_create(
            name='suito',
            project=self.project,
            allow_network_access=True,
            use_setup_command=True,
            setup_command={
                'cmd': 'ping -c 2 www.google.com'
            }
        )

        tasks.grade_student_test_suite_impl(student_suite, self.submission)

        result = self.submission.student_test_suite_results.get(student_test_suite=student_suite)
        self.assertEqual(0, result.setup_result.return_code)
