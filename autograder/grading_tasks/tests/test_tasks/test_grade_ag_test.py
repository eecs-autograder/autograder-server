import os
import random
import shlex
import tempfile
from unittest import mock

from autograder_sandbox import AutograderSandbox
from autograder_sandbox.autograder_sandbox import CompletedCommand
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import tag

import autograder.core.models as ag_models
from autograder.core import constants
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase

from autograder.grading_tasks import tasks


@tag('slow', 'sandbox')
@mock.patch('autograder.grading_tasks.tasks.utils.time.sleep')
class AGTestCommandCorrectnessTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.submission = obj_build.build_submission()
        self.project = self.submission.submission_group.project
        self.ag_test_suite = obj_build.make_ag_test_suite(self.project)
        self.ag_test_case = obj_build.make_ag_test_case(self.ag_test_suite)

    def test_points_awarded_and_deducted(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case, set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            cmd='printf hello',
            expected_return_code=ag_models.ExpectedReturnCode.nonzero,
            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stdout_text='hello',
            deduction_for_wrong_return_code=-1,
            points_for_correct_stdout=3)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.stdout_correct)
        self.assertFalse(res.return_code_correct)

        self.assertEqual(2, self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points)
        self.assertEqual(
            3, self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points_possible)

    def test_diff_ignore_case_whitespace_changes_and_blank_lines(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case, set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            cmd="""bash -c 'printf "HELLO    world\n\n\n"; printf "lol WUT\n\n" >&2'""",
            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stdout_text='hello world\n',
            expected_stderr_source=ag_models.ExpectedOutputSource.text,
            expected_stderr_text='lol wut\n',
            points_for_correct_stdout=4,
            points_for_correct_stderr=2,
            ignore_case=True,
            ignore_whitespace_changes=True,
            ignore_blank_lines=True)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.stdout_correct)
        self.assertTrue(res.stderr_correct)

        self.assertEqual(6, self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points)

    def test_diff_ignore_whitespace(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case, set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            cmd="""bash -c 'printf "helloworld"; printf "lolwut" >&2'""",
            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stdout_text='hello world',
            expected_stderr_source=ag_models.ExpectedOutputSource.text,
            expected_stderr_text='lol   wut',
            points_for_correct_stdout=2,
            ignore_whitespace=True)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.stdout_correct)

        self.assertEqual(2, self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points)

    def test_correct_expected_return_code_zero(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "exit 0"',
            expected_return_code=ag_models.ExpectedReturnCode.zero)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.return_code_correct)

    def test_wrong_expected_return_code_zero(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "exit 1"',
            expected_return_code=ag_models.ExpectedReturnCode.zero)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertFalse(res.return_code_correct)

    def test_correct_expected_return_code_nonzero(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "exit 1"',
            expected_return_code=ag_models.ExpectedReturnCode.nonzero)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.return_code_correct)

    def test_wrong_expected_return_code_nonzero(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "exit 0"',
            expected_return_code=ag_models.ExpectedReturnCode.nonzero)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertFalse(res.return_code_correct)

    def test_correct_expected_stdout_text(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='printf "hello"',
            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stdout_text='hello')
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.stdout_correct)

    def test_wrong_expected_stdout_text(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='printf "nope"',
            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stdout_text='hello')
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertFalse(res.stdout_correct)

    def test_correct_expected_stdout_proj_file(self, *args):
        proj_file = ag_models.UploadedFile.objects.validate_and_create(
            project=self.project, file_obj=SimpleUploadedFile('filey.txt', b'waluigi'))
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='printf "waluigi"',
            expected_stdout_source=ag_models.ExpectedOutputSource.project_file,
            expected_stdout_project_file=proj_file)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.stdout_correct)

    def test_wrong_expected_stdout_proj_file(self, *args):
        proj_file = ag_models.UploadedFile.objects.validate_and_create(
            project=self.project, file_obj=SimpleUploadedFile('filey.txt', b'waluigi'))
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='printf "nope"',
            expected_stdout_source=ag_models.ExpectedOutputSource.project_file,
            expected_stdout_project_file=proj_file)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertFalse(res.stdout_correct)

    def test_correct_expected_stderr_text(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "printf hello >&2"',
            expected_stderr_source=ag_models.ExpectedOutputSource.text,
            expected_stderr_text='hello')
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.stderr_correct)

    def test_wrong_expected_stderr_text(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "printf nopers >&2"',
            expected_stderr_source=ag_models.ExpectedOutputSource.text,
            expected_stderr_text='hello')
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertFalse(res.stderr_correct)

    def test_correct_expected_stderr_proj_file(self, *args):
        proj_file = ag_models.UploadedFile.objects.validate_and_create(
            project=self.project, file_obj=SimpleUploadedFile('filey.txt', b'waluigi'))
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "printf waluigi >&2"',
            expected_stderr_source=ag_models.ExpectedOutputSource.project_file,
            expected_stderr_project_file=proj_file)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.stderr_correct)

    def test_wrong_expected_stderr_proj_file(self, *args):
        proj_file = ag_models.UploadedFile.objects.validate_and_create(
            project=self.project, file_obj=SimpleUploadedFile('filey.txt', b'waluigi'))
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "printf norp >&2"',
            expected_stderr_source=ag_models.ExpectedOutputSource.project_file,
            expected_stderr_project_file=proj_file)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertFalse(res.stderr_correct)


@mock.patch('autograder.grading_tasks.tasks.utils.time.sleep')
class AGTestCommandStdinSourceTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.submission = obj_build.build_submission()
        self.project = self.submission.submission_group.project
        self.setup_stdout = 'setuppy stdouty'
        self.setup_stderr = 'setuppy stderrrry'
        self.ag_test_suite = obj_build.make_ag_test_suite(
            self.project,
            setup_suite_cmd='bash -c "printf \'{}\'; printf \'{}\' >&2"'.format(
                self.setup_stdout, self.setup_stderr))
        self.ag_test_case = obj_build.make_ag_test_case(self.ag_test_suite)

    def test_stdin_source_text(self, *args):
        text = 'wuluigio'
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='cat',
            stdin_source=ag_models.StdinSource.text,
            stdin_text=text)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(text, open(res.stdout_filename).read())

    def test_stdin_source_proj_file(self, *args):
        text = ',vnaejfal;skjdf;lakjsdfklajsl;dkjf;'
        proj_file = ag_models.UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=SimpleUploadedFile('filey.txt', text.encode()))
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='cat',
            stdin_source=ag_models.StdinSource.project_file,
            stdin_project_file=proj_file)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(text, open(res.stdout_filename).read())

    def test_stdin_source_setup_stdout(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='cat',
            stdin_source=ag_models.StdinSource.setup_stdout)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(self.setup_stdout, open(res.stdout_filename).read())

    def test_stdin_source_setup_stderr(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='cat',
            stdin_source=ag_models.StdinSource.setup_stderr)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(self.setup_stderr, open(res.stdout_filename).read())


@mock.patch('autograder.grading_tasks.tasks.utils.time.sleep')
class ProjectFilePermissionsTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        project_filename = 'filey.txt'
        self.retcode_points = 42
        self.cmd = obj_build.make_full_ag_test_command(
            set_arbitrary_expected_vals=False, set_arbitrary_points=False,
            cmd='touch {}'.format(project_filename),
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            points_for_correct_return_code=self.retcode_points)

        self.ag_suite = self.cmd.ag_test_case.ag_test_suite
        self.project = self.ag_suite.project
        self.project_file = ag_models.UploadedFile.objects.validate_and_create(
            project=self.project, file_obj=SimpleUploadedFile(project_filename, b'asdkfasdjkf'))
        self.group = obj_build.make_group(project=self.project)
        self.ag_suite.project_files_needed.add(self.project_file)
        self.submission = obj_build.build_submission(submission_group=self.group)

    def test_project_files_read_only(self, *args):
        self.assertTrue(self.ag_suite.read_only_project_files)
        tasks.grade_submission(self.submission.pk)
        self.submission.refresh_from_db()
        self.assertEqual(0, self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points)
        self.assertEqual(
            self.retcode_points,
            self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points_possible)

    def test_project_files_not_read_only(self, *args):
        self.ag_suite.validate_and_update(read_only_project_files=False)
        tasks.grade_submission(self.submission.pk)
        self.submission.refresh_from_db()
        self.assertEqual(self.retcode_points,
                         self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points)
        self.assertEqual(
            self.retcode_points,
            self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points_possible)


@tag('slow', 'sandbox')
@mock.patch('autograder.grading_tasks.tasks.utils.time.sleep')
class ResourceLimitsExceededTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.submission = obj_build.build_submission()
        self.project = self.submission.submission_group.project
        self.ag_test_suite = obj_build.make_ag_test_suite(self.project)
        self.ag_test_case = obj_build.make_ag_test_case(self.ag_test_suite)

        self.too_much_output_size = 20000000  # 20 MB
        too_much_output_prog = """
import sys
print('a' * {0}, end='')
print('b' * {0}, file=sys.stderr, end='')
        """.format(self.too_much_output_size)

        self.too_much_output_file = ag_models.UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=SimpleUploadedFile('too_long.py', too_much_output_prog.encode())
        )  # type: ag_models.UploadedFile

        self.timeout_cmd = "sleep 10"

        self.ag_test_suite.project_files_needed.add(self.too_much_output_file)

        self.non_utf_bytes = b'\x80 and some other stuff just because\n'
        non_utf_prog = """
import sys
sys.stdout.buffer.write({0})
sys.stdout.flush()
sys.stderr.buffer.write({0})
sys.stderr.flush()
        """.format(self.non_utf_bytes)

        self.non_utf_file = ag_models.UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=SimpleUploadedFile('non_utf.py', non_utf_prog.encode()))

        self.ag_test_suite.project_files_needed.add(self.non_utf_file)

    def test_program_times_out(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            cmd=self.timeout_cmd,
            time_limit=1)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.timed_out)

    def test_program_prints_a_lot_of_output(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            cmd='python3 ' + self.too_much_output_file.name,
            time_limit=30)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(0, res.return_code)
        self.assertFalse(res.timed_out)
        self.assertTrue(res.stdout_truncated)
        self.assertTrue(res.stderr_truncated)
        self.assertEqual(constants.MAX_OUTPUT_LENGTH, os.path.getsize(res.stdout_filename))
        self.assertEqual(constants.MAX_OUTPUT_LENGTH, os.path.getsize(res.stderr_filename))

    def test_program_prints_non_unicode_chars(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            cmd='python3 ' + self.non_utf_file.name)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(0, res.return_code)
        self.assertEqual(self.non_utf_bytes, open(res.stdout_filename, 'rb').read())
        self.assertEqual(self.non_utf_bytes, open(res.stderr_filename, 'rb').read())

    def test_suite_setup_and_teardown_return_code_set(self, *args):
        self.ag_test_suite.validate_and_update(setup_suite_cmd='bash -c "exit 2"',
                                               teardown_suite_cmd='bash -c "exit 3"')
        tasks.grade_submission(self.submission.pk)
        res = ag_models.AGTestSuiteResult.objects.get(submission=self.submission)
        self.assertEqual(2, res.setup_return_code)
        self.assertEqual(3, res.teardown_return_code)

    def test_setup_and_teardown_time_out(self, *args):
        self.ag_test_suite.validate_and_update(setup_suite_cmd=self.timeout_cmd,
                                               teardown_suite_cmd=self.timeout_cmd)
        with mock.patch('autograder.core.constants.MAX_SUBPROCESS_TIMEOUT', new=1):
            tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestSuiteResult.objects.get(submission=self.submission)
        self.assertTrue(res.setup_timed_out)
        self.assertTrue(res.teardown_timed_out)

    def test_setup_and_teardown_print_a_lot_of_output(self, *args):
        self.ag_test_suite.validate_and_update(
            setup_suite_cmd='python3 ' + self.too_much_output_file.name,
            teardown_suite_cmd='python3 ' + self.too_much_output_file.name)
        tasks.grade_submission(self.submission.pk)
        res = ag_models.AGTestSuiteResult.objects.get(submission=self.submission)

        self.assertTrue(res.setup_stdout_truncated)
        self.assertTrue(res.setup_stderr_truncated)
        self.assertTrue(res.teardown_stdout_truncated)
        self.assertTrue(res.teardown_stderr_truncated)

        self.assertEqual(constants.MAX_OUTPUT_LENGTH, os.path.getsize(res.setup_stdout_filename))
        self.assertEqual(constants.MAX_OUTPUT_LENGTH, os.path.getsize(res.setup_stderr_filename))
        self.assertEqual(constants.MAX_OUTPUT_LENGTH,
                         os.path.getsize(res.teardown_stdout_filename))
        self.assertEqual(constants.MAX_OUTPUT_LENGTH,
                         os.path.getsize(res.teardown_stderr_filename))

    def test_setup_and_teardown_print_non_unicode_chars(self, *args):
        self.ag_test_suite.validate_and_update(
            setup_suite_cmd='python3 ' + self.non_utf_file.name,
            teardown_suite_cmd='python3 ' + self.non_utf_file.name)
        tasks.grade_submission(self.submission.pk)
        res = ag_models.AGTestSuiteResult.objects.get(submission=self.submission)

        self.assertEqual(self.non_utf_bytes, res.open_setup_stdout().read())
        self.assertEqual(self.non_utf_bytes, res.open_setup_stderr().read())
        self.assertEqual(self.non_utf_bytes, res.open_teardown_stdout().read())
        self.assertEqual(self.non_utf_bytes, res.open_teardown_stderr().read())

    def test_time_process_stack_and_virtual_mem_limits_passed_to_run_command(self, *args):
        self.ag_test_suite.validate_and_update(setup_suite_cmd='printf waluigi',
                                               teardown_suite_cmd='printf wuluigio')

        time_limit = random.randint(1, constants.MAX_SUBPROCESS_TIMEOUT)
        process_spawn_limit = random.randint(constants.DEFAULT_PROCESS_LIMIT + 1,
                                             constants.MAX_PROCESS_LIMIT)
        stack_size_limit = random.randint(constants.DEFAULT_STACK_SIZE_LIMIT,
                                          constants.MAX_STACK_SIZE_LIMIT)
        virtual_memory_limit = random.randint(constants.DEFAULT_VIRTUAL_MEM_LIMIT,
                                              constants.MAX_VIRTUAL_MEM_LIMIT)
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case, cmd='printf spam',
            time_limit=time_limit,
            process_spawn_limit=process_spawn_limit,
            stack_size_limit=stack_size_limit,
            virtual_memory_limit=virtual_memory_limit,
        )

        sandbox = AutograderSandbox()

        def make_run_command_ret_val(*args, **kwargs):
            return CompletedCommand(
                return_code=0, stdout=tempfile.NamedTemporaryFile(),
                stderr=tempfile.NamedTemporaryFile(), timed_out=False,
                stdout_truncated=False, stderr_truncated=False)

        run_command_mock = mock.Mock(side_effect=make_run_command_ret_val)
        sandbox.run_command = run_command_mock
        with mock.patch('autograder.grading_tasks.tasks.grade_ag_test.AutograderSandbox',
                        return_value=sandbox):
            tasks.grade_submission(self.submission.pk)

        expected_setup_and_teardown_resource_kwargs = {
            'timeout': constants.MAX_SUBPROCESS_TIMEOUT,
            'max_num_processes': constants.MAX_PROCESS_LIMIT,
            'max_stack_size': constants.MAX_STACK_SIZE_LIMIT,
            'max_virtual_memory': constants.MAX_VIRTUAL_MEM_LIMIT,
            'truncate_stdout': constants.MAX_OUTPUT_LENGTH,
            'truncate_stderr': constants.MAX_OUTPUT_LENGTH,
        }
        expected_cmd_args = {
            'timeout': time_limit,
            'max_num_processes': process_spawn_limit,
            'max_stack_size': stack_size_limit,
            'max_virtual_memory': virtual_memory_limit,
            'truncate_stdout': constants.MAX_OUTPUT_LENGTH,
            'truncate_stderr': constants.MAX_OUTPUT_LENGTH,
        }
        run_command_mock.assert_has_calls([
            mock.call(shlex.split(self.ag_test_suite.setup_suite_cmd),
                      stdin=None,
                      as_root=False, **expected_setup_and_teardown_resource_kwargs),
            mock.call(shlex.split(cmd.cmd), stdin=None, as_root=False, **expected_cmd_args),
            mock.call(shlex.split(self.ag_test_suite.teardown_suite_cmd),
                      stdin=None,
                      as_root=False, **expected_setup_and_teardown_resource_kwargs)
        ])


@tag('slow', 'sandbox')
@mock.patch('autograder.grading_tasks.tasks.utils.time.sleep')
class AGTestSuiteRerunTestCase(UnitTestBase):
    def setUp(self):
        # 1. Create an AGTestSuite with 2 test cases (one command per test).
        # 2. Each test case should be configured to fail when they are run.
        # 3. Grade the AGTestSuite, letting both tests fail.
        # 4. Update the test cases so that they will pass when they are rerun.

        super().setUp()
        self.submission = obj_build.build_submission()
        self.project = self.submission.submission_group.project
        self.ag_test_suite = obj_build.make_ag_test_suite(self.project)

        self.ag_test_case_1 = obj_build.make_ag_test_case(self.ag_test_suite)
        self.ag_test_cmd_1 = ag_models.AGTestCommand.objects.validate_and_create(
            ag_test_case=self.ag_test_case_1,
            name='cmd1',
            cmd='false',  # Always exits nonzero
            expected_return_code=ag_models.ExpectedReturnCode.zero
        )  # type: ag_models.AGTestCommand
        self.ag_test_case_2 = obj_build.make_ag_test_case(self.ag_test_suite)
        self.ag_test_cmd_2 = ag_models.AGTestCommand.objects.validate_and_create(
            ag_test_case=self.ag_test_case_2,
            name='cmd2',
            cmd='false',
            expected_return_code=ag_models.ExpectedReturnCode.zero
        )  # type: ag_models.AGTestCommand

        # Reverse the order the test cases are run in so that the test cases
        # and test case results don't have the same pk's
        self.ag_test_suite.set_agtestcase_order(self.ag_test_suite.get_agtestcase_order()[::-1])

        tasks.grade_ag_test_suite_impl(self.ag_test_suite, self.submission)

        results = ag_models.AGTestCommandResult.objects.all()
        self.assertEqual(2, results.count())
        for res in results:
            self.assertFalse(res.return_code_correct)

        self.ag_test_cmd_1.validate_and_update(cmd='true')  # Always exits zero
        self.ag_test_cmd_2.validate_and_update(cmd='true')

    def test_rerun_all_tests_in_suite_no_star_args_passed(self, *args):
        tasks.grade_ag_test_suite_impl(self.ag_test_suite, self.submission)

        results = ag_models.AGTestCommandResult.objects.all()
        self.assertEqual(2, results.count())
        for res in results:
            self.assertTrue(res.return_code_correct)

    def test_rerun_all_tests_in_suite_with_star_args_passed(self, *args):
        tasks.grade_ag_test_suite_impl(self.ag_test_suite, self.submission,
                                       self.ag_test_case_1, self.ag_test_case_2)

        results = ag_models.AGTestCommandResult.objects.all()
        self.assertEqual(2, results.count())
        for res in results:
            self.assertTrue(res.return_code_correct)

    def test_rerun_some_tests_in_suite(self, *args):
        tasks.grade_ag_test_suite_impl(self.ag_test_suite, self.submission, self.ag_test_case_1)

        rerun_result = self.ag_test_cmd_1.agtestcommandresult_set.first()
        self.assertTrue(rerun_result.return_code_correct)

        not_rerun_result = self.ag_test_cmd_2.agtestcommandresult_set.first()
        self.assertFalse(not_rerun_result.return_code_correct)
