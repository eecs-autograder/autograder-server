import os
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import tag

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core import constants
from autograder.grading_tasks import tasks
from autograder.utils.testing import TransactionUnitTestBase, UnitTestBase
from autograder_sandbox.autograder_sandbox import AutograderSandbox, CompletedCommand
import tempfile


@tag('slow', 'sandbox')
@mock.patch('autograder.utils.retry.sleep')
class EECS280StyleMutationTestGradingIntegrationTestCase(UnitTestBase):
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
        self.mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name='EECS 280 Student Tests', project=self.project,
            instructor_files_needed=self.project.instructor_files.all(),
            student_files_needed=self.project.expected_student_files.all(),
            buggy_impl_names=self.bugs_exposed + self.bugs_not_exposed,

            use_setup_command=True,
            setup_command={
                'cmd': 'make student_tests.exe',
            },
            get_student_test_names_command={
                'cmd': 'make -s get_test_names',
            },
            student_test_validity_check_command={
                'cmd': 'make ${student_test_name}.validity_check',
            },
            grade_buggy_impl_command={
                'cmd': ('make student_test=${student_test_name} '
                        'bug_name=${buggy_impl_name} buggy_impl'),
            },
            points_per_exposed_bug=1)  # type: ag_models.MutationTestSuite

        with open(os.path.join(self.files_dir, 'student_tests.cpp'), 'rb') as f:
            self.submission = obj_build.make_submission(
                submitted_files=[SimpleUploadedFile('student_tests.cpp', f.read())],
                group=obj_build.make_group(project=self.project))

        self.valid_tests = ['test_return_42', 'test_return_true']
        self.invalid_tests = ['incorrectly_test_return3', 'this_test_times_out']
        self.timeout_tests = ['this_test_times_out']
        self.all_tests = set(self.valid_tests + self.invalid_tests + self.timeout_tests)

    def test_grade_non_deferred(self, *args):
        tasks.grade_submission_task(self.submission.pk)

        result = ag_models.MutationTestSuiteResult.objects.get(
            mutation_test_suite=self.mutation_suite)

        self.assertEqual(0, result.setup_result.return_code)

        print(result.student_tests)
        print(result.invalid_tests)
        self.assertCountEqual(self.all_tests, result.student_tests)
        self.assertCountEqual(self.invalid_tests, result.invalid_tests)
        self.assertCountEqual(self.timeout_tests, result.timed_out_tests)
        self.assertCountEqual(self.bugs_exposed, result.bugs_exposed)

        self.assertEqual(0, result.get_test_names_result.return_code)

        self._print_mutation_result_output(result)

    def test_run_student_tests_in_batch(self, *args) -> None:
        self.mutation_suite.validate_and_update(
            grade_buggy_impl_command={
                'cmd': ("make student_test_batch='${all_valid_test_names}' "
                        "bug_name=${buggy_impl_name} buggy_impl_batch"),
            }
        )
        tasks.grade_submission_task(self.submission.pk)

        result = ag_models.MutationTestSuiteResult.objects.get(
            mutation_test_suite=self.mutation_suite)

        self.assertEqual(0, result.setup_result.return_code)

        print(result.student_tests)
        print(result.invalid_tests)
        self._print_mutation_result_output(result)

        self.assertCountEqual(self.all_tests, result.student_tests)
        self.assertCountEqual(self.invalid_tests, result.invalid_tests)
        self.assertCountEqual(self.timeout_tests, result.timed_out_tests)
        self.assertCountEqual(self.bugs_exposed, result.bugs_exposed)

        self.assertEqual(0, result.get_test_names_result.return_code)

    def _print_mutation_result_output(self, result: ag_models.MutationTestSuiteResult) -> None:
        with open(result.get_test_names_result.stdout_filename) as f:
            print('get_test_names_result.stdout_filename')
            print(f.read(), flush=True)
        with open(result.get_test_names_result.stderr_filename) as f:
            print('get_test_names_result.stderr_filename')
            print(f.read(), flush=True)

        with open(result.setup_result.stdout_filename) as f:
            print('setup_result stdout')
            print(f.read(), flush=True)
        with open(result.setup_result.stderr_filename) as f:
            print('setup_result stderr')
            print(f.read(), flush=True)

        with open(result.get_test_names_result.stdout_filename) as f:
            print('get_test_names_result stdout')
            print(f.read(), flush=True)
        with open(result.get_test_names_result.stderr_filename) as f:
            print('get_test_names_result stderr')
            print(f.read(), flush=True)

        with open(result.validity_check_stdout_filename) as f:
            print('open_validity_check_stdout')
            print(f.read(), flush=True)
        with open(result.validity_check_stderr_filename) as f:
            print('open_validity_check_stderr')
            print(f.read(), flush=True)

        with open(result.grade_buggy_impls_stdout_filename) as f:
            print('open_grade_buggy_impls_stdout')
            print(f.read(), flush=True)
        with open(result.grade_buggy_impls_stderr_filename) as f:
            print('open_grade_buggy_impls_stderr')
            print(f.read(), flush=True)

    def test_grade_deferred(self, *args):
        self.mutation_suite.validate_and_update(deferred=True)
        tasks.grade_submission_task(self.submission.pk)

        result = ag_models.MutationTestSuiteResult.objects.get(
            mutation_test_suite=self.mutation_suite)

        self.assertEqual(0, result.setup_result.return_code)

        print(result.student_tests)
        print(result.invalid_tests)
        self.assertCountEqual(self.all_tests, result.student_tests)
        self.assertCountEqual(self.invalid_tests, result.invalid_tests)
        self.assertCountEqual(self.timeout_tests, result.timed_out_tests)
        self.assertCountEqual(self.bugs_exposed, result.bugs_exposed)

    def test_setup_command_fails_no_tests_discovered(self, *args):
        self.mutation_suite.validate_and_update(setup_command={'cmd': 'false'})

        tasks.grade_submission_task(self.submission.pk)
        result = ag_models.MutationTestSuiteResult.objects.get(
            mutation_test_suite=self.mutation_suite)

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
        self.mutation_suite.validate_and_update(setup_command={'cmd': 'sleep 10'})
        with mock.patch('autograder.core.constants.MAX_SUBPROCESS_TIMEOUT', new=1):
            tasks.grade_submission_task(self.submission.pk)

            result = ag_models.MutationTestSuiteResult.objects.get(
                mutation_test_suite=self.mutation_suite)
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
@mock.patch('autograder.utils.retry.sleep')
class MutationTestSuiteGradingEdgeCaseTestCase(UnitTestBase):
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

        mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name='qeoriuqewrpqiuerqopwr',
            project=self.project,
            instructor_files_needed=[instructor_file],
            get_student_test_names_command={
                'cmd': 'cat {}'.format(instructor_file.name)
            }
        )
        tasks.grade_submission_task(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

        result = ag_models.MutationTestSuiteResult.objects.get(mutation_test_suite=mutation_suite)
        self.assertIsNone(result.setup_result)

        self.assertEqual(0, result.get_test_names_result.return_code)
        self.assertSequenceEqual(escaped_names, result.student_tests)
        self.assertSequenceEqual([], result.invalid_tests)

    def test_too_many_student_tests(self, *args):
        tests = ['test1', 'test2', 'test3']
        mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name='too maaaany',
            project=self.project,
            get_student_test_names_command={
                'cmd': 'echo {}'.format(' '.join(tests))
            },
            max_num_student_tests=1
        )
        tasks.grade_submission_task(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

        result = ag_models.MutationTestSuiteResult.objects.get(mutation_test_suite=mutation_suite)
        self.assertEqual(tests[:1], result.student_tests)
        self.assertEqual(tests[1:], result.discarded_tests)

    def test_no_setup_command(self, *args):
        test_names = 'test1 test2 test3'

        mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name='sweet',
            project=self.project,
            get_student_test_names_command={
                'cmd': 'echo {}'.format(test_names)
            }
        )
        tasks.grade_submission_task(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

        result = ag_models.MutationTestSuiteResult.objects.get(
            mutation_test_suite=mutation_suite)
        self.assertIsNone(result.setup_result)

        self.assertEqual(0, result.get_test_names_result.return_code)
        self.assertSequenceEqual(test_names.split(), result.student_tests)
        self.assertSequenceEqual([], result.invalid_tests)

    def test_get_test_names_stdout_and_stderr(self, *args):
        test_names = 'test1 test2 test3'
        stderr = 'stderry'
        mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name='sweet',
            project=self.project,
            get_student_test_names_command={
                'cmd': 'bash -c "printf \'{}\'; printf \'{}\' >&2"'.format(test_names, stderr)
            }
        )
        tasks.grade_submission_task(self.submission.pk)

        result = ag_models.MutationTestSuiteResult.objects.get(
            mutation_test_suite=mutation_suite)

        self.assertEqual(0, result.get_test_names_result.return_code)
        self.assertSequenceEqual(test_names.split(), result.student_tests)

        with open(result.get_test_names_result.stdout_filename) as f:
            self.assertEqual(test_names, f.read())

        with open(result.get_test_names_result.stderr_filename) as f:
            self.assertEqual(stderr, f.read())

    def test_get_test_names_return_code_nonzero(self, *args):
        test_names = 'test1 test2 test3'
        stderr = 'stderry'
        mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name='sweet',
            project=self.project,
            get_student_test_names_command={
                'cmd': 'bash -c "printf \'{}\'; printf \'{}\' >&2; false"'.format(
                    test_names, stderr)
            }
        )
        tasks.grade_submission_task(self.submission.pk)

        result = ag_models.MutationTestSuiteResult.objects.get(
            mutation_test_suite=mutation_suite)

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

        mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name='suito',
            project=self.project,
            sandbox_docker_image=eecs490_image,
            use_setup_command=True,
            setup_command={
                'cmd': 'racket --version'
            }
        )

        tasks.grade_mutation_test_suite_impl(mutation_suite, self.submission)

        result = self.submission.mutation_test_suite_results.get(
            mutation_test_suite=mutation_suite)
        self.assertEqual(0, result.setup_result.return_code)

    def test_network_access_allowed(self, *args):
        mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name='suito',
            project=self.project,
            allow_network_access=True,
            use_setup_command=True,
            setup_command={
                'cmd': 'ping -c 2 www.google.com'
            }
        )

        tasks.grade_mutation_test_suite_impl(mutation_suite, self.submission)

        result = self.submission.mutation_test_suite_results.get(
            mutation_test_suite=mutation_suite)
        self.assertEqual(0, result.setup_result.return_code)

    def test_resource_limits_applied(self, *args) -> None:
        mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name='Suiteo',
            project=self.project,
            buggy_impl_names=['bug1'],
            use_setup_command=True,
            setup_command={
                'cmd': 'true',
                'block_process_spawn': True,
                'use_virtual_memory_limit': True,
                'virtual_memory_limit': 40000000,
                'time_limit': 10,
            },
            get_student_test_names_command={
                'cmd': 'echo test1',
                'block_process_spawn': False,
                'use_virtual_memory_limit': True,
                'virtual_memory_limit': 40000001,
                'time_limit': 11,
            },
        )
        mutation_suite.student_test_validity_check_command.update({
            'block_process_spawn': True,
            'use_virtual_memory_limit': True,
            'virtual_memory_limit': 40000002,
            'time_limit': 12,
        })
        mutation_suite.grade_buggy_impl_command.update({
            'block_process_spawn': True,
            'use_virtual_memory_limit': True,
            'virtual_memory_limit': 40000003,
            'time_limit': 13,
        })
        mutation_suite.save()

        sandbox = AutograderSandbox()
        original_run_command = sandbox.run_command

        def wrapped_run_command(*args, **kwargs):
            return original_run_command(*args, **kwargs)

        run_command_mock = mock.Mock(side_effect=wrapped_run_command)
        sandbox.run_command = run_command_mock
        with mock.patch(
            'autograder.grading_tasks.tasks.grade_mutation_test_suite.AutograderSandbox',
            return_value=sandbox
        ):
            tasks.grade_submission_task(self.submission.pk)

        expected_cmds = ['true', 'echo test1', 'echo test1', 'echo bug1 test1']
        expected_calls = [
            mock.call(
                ['bash', '-c', expected_cmds[i]], stdin=None, as_root=False,
                block_process_spawn=cmd.block_process_spawn,
                max_virtual_memory=cmd.virtual_memory_limit,
                timeout=cmd.time_limit,
                truncate_stdout=constants.MAX_RECORDED_OUTPUT_LENGTH,
                truncate_stderr=constants.MAX_RECORDED_OUTPUT_LENGTH,
            )
            for (i, cmd) in enumerate((mutation_suite.setup_command,
                                       mutation_suite.get_student_test_names_command,
                                       mutation_suite.student_test_validity_check_command,
                                       mutation_suite.grade_buggy_impl_command))
        ]

        run_command_mock.assert_has_calls(expected_calls)

    def test_use_virtual_memory_limit_false_no_limit_applied(self, *args) -> None:
        time_limit = 5
        mutation_suite = ag_models.MutationTestSuite.objects.validate_and_create(
            name='qeoriuqewrpqiuerqopwr',
            project=self.project,
            use_setup_command=True,
            setup_command={
                'cmd': 'true',
                'use_virtual_memory_limit': False,
                'virtual_memory_limit': 40000,
                'time_limit': time_limit
            }
        )

        sandbox = AutograderSandbox()

        def make_run_command_ret_val(*args, **kwargs):
            return CompletedCommand(
                return_code=0, stdout=tempfile.NamedTemporaryFile(),
                stderr=tempfile.NamedTemporaryFile(), timed_out=False,
                stdout_truncated=False, stderr_truncated=False)

        run_command_mock = mock.Mock(side_effect=make_run_command_ret_val)
        sandbox.run_command = run_command_mock
        with mock.patch(
            'autograder.grading_tasks.tasks.grade_mutation_test_suite.AutograderSandbox',
            return_value=sandbox
        ):
            tasks.grade_submission_task(self.submission.pk)

        expected_cmd_args = {
            'timeout': time_limit,
            'block_process_spawn': False,
            'max_virtual_memory': None,
            'truncate_stdout': constants.MAX_RECORDED_OUTPUT_LENGTH,
            'truncate_stderr': constants.MAX_RECORDED_OUTPUT_LENGTH,
        }
        run_command_mock.assert_has_calls([
            mock.call(['bash', '-c', 'true'], stdin=None, as_root=False, **expected_cmd_args),
        ])


@mock.patch('autograder.utils.retry.sleep')
class NoRetryOnObjectNotFoundTestCase(TransactionUnitTestBase):
    def test_mutation_test_suite_not_found_no_retry(self, sleep_mock) -> None:
        submission = obj_build.make_submission()
        suite = obj_build.make_mutation_test_suite()

        ag_models.MutationTestSuite.objects.get(pk=suite.pk).delete()

        tasks.grade_deferred_mutation_test_suite(suite.pk, submission.pk)
        tasks.grade_mutation_test_suite_impl(suite, submission)
        sleep_mock.assert_not_called()
