import os
import random
import tempfile
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import tag

from autograder_sandbox import AutograderSandbox
from autograder_sandbox.autograder_sandbox import CompletedCommand
from autograder.grading_tasks.tasks.exceptions import SubmissionRejected
import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core import constants
from autograder.core.tests.test_submission_feedback.fdbk_getter_shortcuts import \
    get_submission_fdbk
from autograder.grading_tasks import tasks
from autograder.utils.testing import TransactionUnitTestBase, UnitTestBase


@tag('slow', 'sandbox')
@mock.patch('autograder.utils.retry.sleep')
class AGTestCommandCorrectnessTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.submission = obj_build.make_submission()
        self.project = self.submission.group.project
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
        tasks.grade_submission_task(self.submission.pk)
        self.submission.refresh_from_db()

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.stdout_correct)
        self.assertFalse(res.return_code_correct)

        self.assertEqual(
            2,
            get_submission_fdbk(self.submission, ag_models.FeedbackCategory.max).total_points)
        self.assertEqual(
            3,
            get_submission_fdbk(
                self.submission, ag_models.FeedbackCategory.max).total_points_possible)

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
        tasks.grade_submission_task(self.submission.pk)
        self.submission.refresh_from_db()

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.stdout_correct)
        self.assertTrue(res.stderr_correct)

        self.assertEqual(
            6,
            get_submission_fdbk(
                self.submission, ag_models.FeedbackCategory.max).total_points)

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
        tasks.grade_submission_task(self.submission.pk)
        self.submission.refresh_from_db()

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.stdout_correct)

        self.assertEqual(
            2,
            get_submission_fdbk(self.submission, ag_models.FeedbackCategory.max).total_points)

    def test_correct_expected_return_code_zero(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "exit 0"',
            expected_return_code=ag_models.ExpectedReturnCode.zero)
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.return_code_correct)

    def test_wrong_expected_return_code_zero(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "exit 1"',
            expected_return_code=ag_models.ExpectedReturnCode.zero)
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertFalse(res.return_code_correct)

    def test_correct_expected_return_code_nonzero(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "exit 1"',
            expected_return_code=ag_models.ExpectedReturnCode.nonzero)
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.return_code_correct)

    def test_wrong_expected_return_code_nonzero(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "exit 0"',
            expected_return_code=ag_models.ExpectedReturnCode.nonzero)
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertFalse(res.return_code_correct)

    def test_correct_expected_stdout_text(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='printf "hello"',
            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stdout_text='hello')
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.stdout_correct)

    def test_wrong_expected_stdout_text(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='printf "nope"',
            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stdout_text='hello')
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertFalse(res.stdout_correct)

    def test_correct_expected_stdout_instructor_file(self, *args):
        instructor_file = ag_models.InstructorFile.objects.validate_and_create(
            project=self.project, file_obj=SimpleUploadedFile('filey.txt', b'waluigi'))
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='printf "waluigi"',
            expected_stdout_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stdout_instructor_file=instructor_file)
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.stdout_correct)

    def test_wrong_expected_stdout_instructor_file(self, *args):
        instructor_file = ag_models.InstructorFile.objects.validate_and_create(
            project=self.project, file_obj=SimpleUploadedFile('filey.txt', b'waluigi'))
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='printf "nope"',
            expected_stdout_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stdout_instructor_file=instructor_file)
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertFalse(res.stdout_correct)

    def test_correct_expected_stderr_text(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "printf hello >&2"',
            expected_stderr_source=ag_models.ExpectedOutputSource.text,
            expected_stderr_text='hello')
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.stderr_correct)

    def test_wrong_expected_stderr_text(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "printf nopers >&2"',
            expected_stderr_source=ag_models.ExpectedOutputSource.text,
            expected_stderr_text='hello')
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertFalse(res.stderr_correct)

    def test_correct_expected_stderr_instructor_file(self, *args):
        instructor_file = ag_models.InstructorFile.objects.validate_and_create(
            project=self.project, file_obj=SimpleUploadedFile('filey.txt', b'waluigi'))
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "printf waluigi >&2"',
            expected_stderr_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stderr_instructor_file=instructor_file)
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.stderr_correct)

    def test_wrong_expected_stderr_instructor_file(self, *args):
        instructor_file = ag_models.InstructorFile.objects.validate_and_create(
            project=self.project, file_obj=SimpleUploadedFile('filey.txt', b'waluigi'))
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "printf norp >&2"',
            expected_stderr_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stderr_instructor_file=instructor_file)
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertFalse(res.stderr_correct)


@mock.patch('autograder.utils.retry.sleep')
class AGTestCommandStdinSourceTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.submission = obj_build.make_submission()
        self.project = self.submission.group.project
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
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(text, open(res.stdout_filename).read())

    def test_stdin_source_instructor_file(self, *args):
        text = ',vnaejfal;skjdf;lakjsdfklajsl;dkjf;'
        instructor_file = ag_models.InstructorFile.objects.validate_and_create(
            project=self.project,
            file_obj=SimpleUploadedFile('filey.txt', text.encode()))
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='cat',
            stdin_source=ag_models.StdinSource.instructor_file,
            stdin_instructor_file=instructor_file)
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(text, open(res.stdout_filename).read())

    def test_stdin_source_setup_stdout(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='cat',
            stdin_source=ag_models.StdinSource.setup_stdout)
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(self.setup_stdout, open(res.stdout_filename).read())

    def test_stdin_source_setup_stderr(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='cat',
            stdin_source=ag_models.StdinSource.setup_stderr)
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(self.setup_stderr, open(res.stdout_filename).read())


@mock.patch('autograder.utils.retry.sleep')
class InstructorFilePermissionsTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        instructor_filename = 'filey.txt'
        self.retcode_points = 42
        self.cmd = obj_build.make_full_ag_test_command(
            set_arbitrary_expected_vals=False, set_arbitrary_points=False,
            cmd='touch {}'.format(instructor_filename),
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            points_for_correct_return_code=self.retcode_points)

        self.ag_suite = self.cmd.ag_test_case.ag_test_suite
        self.project = self.ag_suite.project
        self.instructor_file = ag_models.InstructorFile.objects.validate_and_create(
            project=self.project, file_obj=SimpleUploadedFile(instructor_filename, b'asdkfasdjkf'))
        self.group = obj_build.make_group(project=self.project)
        self.ag_suite.instructor_files_needed.add(self.instructor_file)
        self.submission = obj_build.make_submission(group=self.group)

    def test_instructor_files_read_only(self, *args):
        self.assertTrue(self.ag_suite.read_only_instructor_files)
        tasks.grade_submission_task(self.submission.pk)
        self.submission.refresh_from_db()
        self.assertEqual(
            0,
            get_submission_fdbk(self.submission, ag_models.FeedbackCategory.max).total_points)
        self.assertEqual(
            self.retcode_points,
            get_submission_fdbk(
                self.submission, ag_models.FeedbackCategory.max).total_points_possible)

    def test_instructor_files_not_read_only(self, *args):
        self.ag_suite.validate_and_update(read_only_instructor_files=False)
        tasks.grade_submission_task(self.submission.pk)
        self.submission.refresh_from_db()
        self.assertEqual(
            self.retcode_points,
            get_submission_fdbk(self.submission, ag_models.FeedbackCategory.max).total_points)
        self.assertEqual(
            self.retcode_points,
            get_submission_fdbk(
                self.submission, ag_models.FeedbackCategory.max).total_points_possible)


@tag('slow', 'sandbox')
@mock.patch('autograder.utils.retry.sleep')
class ResourceLimitsExceededTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.submission = obj_build.make_submission()
        self.project = self.submission.group.project
        self.ag_test_suite = obj_build.make_ag_test_suite(self.project)
        self.ag_test_case = obj_build.make_ag_test_case(self.ag_test_suite)

        self.too_much_output_size = 20000000  # 20 MB
        too_much_output_prog = """
import sys
print('a' * {0}, end='')
print('b' * {0}, file=sys.stderr, end='')
        """.format(self.too_much_output_size)

        self.too_much_output_file = ag_models.InstructorFile.objects.validate_and_create(
            project=self.project,
            file_obj=SimpleUploadedFile('too_long.py', too_much_output_prog.encode())
        )  # type: ag_models.InstructorFile

        self.timeout_cmd = "sleep 10"

        self.ag_test_suite.instructor_files_needed.add(self.too_much_output_file)

        self.non_utf_bytes = b'\x80 and some other stuff just because\n'
        non_utf_prog = """
import sys
sys.stdout.buffer.write({0})
sys.stdout.flush()
sys.stderr.buffer.write({0})
sys.stderr.flush()
        """.format(self.non_utf_bytes)

        self.non_utf_file = ag_models.InstructorFile.objects.validate_and_create(
            project=self.project,
            file_obj=SimpleUploadedFile('non_utf.py', non_utf_prog.encode()))

        self.ag_test_suite.instructor_files_needed.add(self.non_utf_file)

    def test_program_times_out(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            cmd=self.timeout_cmd,
            time_limit=1)
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.timed_out)

    def test_program_prints_a_lot_of_output(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            cmd='python3 ' + self.too_much_output_file.name,
            time_limit=30)
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(0, res.return_code)
        self.assertFalse(res.timed_out)
        self.assertTrue(res.stdout_truncated)
        self.assertTrue(res.stderr_truncated)
        self.assertEqual(
            constants.MAX_RECORDED_OUTPUT_LENGTH, os.path.getsize(res.stdout_filename))
        self.assertEqual(
            constants.MAX_RECORDED_OUTPUT_LENGTH, os.path.getsize(res.stderr_filename))

    def test_program_prints_non_unicode_chars(self, *args):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            cmd='python3 ' + self.non_utf_file.name)
        tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(0, res.return_code)
        self.assertEqual(self.non_utf_bytes, open(res.stdout_filename, 'rb').read())
        self.assertEqual(self.non_utf_bytes, open(res.stderr_filename, 'rb').read())

    def test_suite_setup_return_code_set(self, *args):
        self.ag_test_suite.validate_and_update(setup_suite_cmd='bash -c "exit 2"')
        tasks.grade_submission_task(self.submission.pk)
        res = ag_models.AGTestSuiteResult.objects.get(submission=self.submission)
        self.assertEqual(2, res.setup_return_code)

    def test_setup_time_out(self, *args):
        self.ag_test_suite.validate_and_update(setup_suite_cmd=self.timeout_cmd)
        with mock.patch('autograder.core.constants.MAX_SUBPROCESS_TIMEOUT', new=1):
            tasks.grade_submission_task(self.submission.pk)

        res = ag_models.AGTestSuiteResult.objects.get(submission=self.submission)
        self.assertTrue(res.setup_timed_out)

    def test_setup_print_a_lot_of_output(self, *args):
        self.ag_test_suite.validate_and_update(
            setup_suite_cmd='python3 ' + self.too_much_output_file.name)
        tasks.grade_submission_task(self.submission.pk)
        res = ag_models.AGTestSuiteResult.objects.get(submission=self.submission)

        self.assertTrue(res.setup_stdout_truncated)
        self.assertTrue(res.setup_stderr_truncated)

        self.assertEqual(
            constants.MAX_RECORDED_OUTPUT_LENGTH, os.path.getsize(res.setup_stdout_filename))
        self.assertEqual(
            constants.MAX_RECORDED_OUTPUT_LENGTH, os.path.getsize(res.setup_stderr_filename))

    def test_setup_print_non_unicode_chars(self, *args):
        self.ag_test_suite.validate_and_update(
            setup_suite_cmd='python3 ' + self.non_utf_file.name)
        tasks.grade_submission_task(self.submission.pk)
        res = ag_models.AGTestSuiteResult.objects.get(submission=self.submission)

        self.assertEqual(self.non_utf_bytes, res.open_setup_stdout().read())
        self.assertEqual(self.non_utf_bytes, res.open_setup_stderr().read())

    # Remove process and stack limit tests in version 5.0.0
    def test_time_process_stack_and_virtual_mem_limits_passed_to_run_command(self, *args):
        self.ag_test_suite.validate_and_update(setup_suite_cmd='printf waluigi')

        time_limit = random.randint(1, constants.MAX_SUBPROCESS_TIMEOUT)
        virtual_memory_limit = random.randint(
            constants.DEFAULT_VIRTUAL_MEM_LIMIT, constants.DEFAULT_VIRTUAL_MEM_LIMIT * 100)
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case, cmd='printf spam',
            time_limit=time_limit,
            block_process_spawn=True,
            use_virtual_memory_limit=True,
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
            tasks.grade_submission_task(self.submission.pk)

        expected_setup_resource_kwargs = {
            'timeout': constants.MAX_SUBPROCESS_TIMEOUT,
            'block_process_spawn': False,
            'max_virtual_memory': None,
            'truncate_stdout': constants.MAX_RECORDED_OUTPUT_LENGTH,
            'truncate_stderr': constants.MAX_RECORDED_OUTPUT_LENGTH,
        }
        expected_cmd_args = {
            'timeout': time_limit,
            'block_process_spawn': True,
            'max_virtual_memory': virtual_memory_limit,
            'truncate_stdout': constants.MAX_RECORDED_OUTPUT_LENGTH,
            'truncate_stderr': constants.MAX_RECORDED_OUTPUT_LENGTH,
        }
        run_command_mock.assert_has_calls([
            mock.call(['bash', '-c', self.ag_test_suite.setup_suite_cmd],
                      stdin=None,
                      as_root=False, **expected_setup_resource_kwargs),
            mock.call(['bash', '-c', cmd.cmd], stdin=None, as_root=False, **expected_cmd_args),
        ])

    def test_use_virtual_memory_limit_false_no_limit_applied(self, *args) -> None:
        self.ag_test_suite.validate_and_update(setup_suite_cmd='')

        time_limit = 5
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case, cmd='printf spam',
            use_virtual_memory_limit=False,
            time_limit=time_limit,
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
            tasks.grade_submission_task(self.submission.pk)

        expected_cmd_args = {
            'timeout': time_limit,
            'max_virtual_memory': None,
            'block_process_spawn': False,
            'truncate_stdout': constants.MAX_RECORDED_OUTPUT_LENGTH,
            'truncate_stderr': constants.MAX_RECORDED_OUTPUT_LENGTH,
        }
        run_command_mock.assert_has_calls([
            mock.call(['bash', '-c', cmd.cmd], stdin=None, as_root=False, **expected_cmd_args),
        ])


@tag('slow', 'sandbox')
@mock.patch('autograder.utils.retry.sleep')
class AGTestSuiteRerunTestCase(UnitTestBase):
    def setUp(self):
        # 1. Create an AGTestSuite with 2 test cases (one command per test).
        # 2. Each test case should be configured to fail when they are run.
        # 3. Grade the AGTestSuite, letting both tests fail.
        # 4. Update the test cases so that they will pass when they are rerun.

        super().setUp()
        self.submission = obj_build.make_submission()
        self.project = self.submission.group.project
        self.ag_test_suite = obj_build.make_ag_test_suite(
            self.project, setup_suite_cmd='echo "spaaaaam"; echo "eeeeeeegg" 1>&2')

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

    def test_rerun_with_setup_command_removed(self, *args) -> None:
        suite_result = ag_models.AGTestSuiteResult.objects.get(ag_test_suite=self.ag_test_suite)
        suite_result.setup_timed_out = True  # So that we know this value gets reset
        suite_result.save()
        with open(suite_result.setup_stdout_filename, 'r') as f:
            self.assertNotEqual('', f.read())
        with open(suite_result.setup_stderr_filename, 'r') as f:
            self.assertNotEqual('', f.read())

        self.assertEqual(0, suite_result.setup_return_code)
        self.assertTrue(suite_result.setup_timed_out)

        self.ag_test_suite.validate_and_update(setup_suite_cmd='')
        tasks.grade_ag_test_suite_impl(self.ag_test_suite, self.submission, self.ag_test_case_1)

        suite_result.refresh_from_db()
        with open(suite_result.setup_stdout_filename, 'r') as f:
            self.assertEqual('', f.read())
        with open(suite_result.setup_stderr_filename, 'r') as f:
            self.assertEqual('', f.read())

        self.assertIsNone(suite_result.setup_return_code)
        self.assertFalse(suite_result.setup_timed_out)


@mock.patch('autograder.utils.retry.sleep')
class NoRetryOnObjectNotFoundTestCase(TransactionUnitTestBase):
    def test_ag_test_suite_not_found_no_retry(self, sleep_mock) -> None:
        submission = obj_build.make_submission()
        ag_test_suite = obj_build.make_ag_test_suite()

        ag_models.AGTestSuite.objects.get(pk=ag_test_suite.pk).delete()

        tasks.grade_deferred_ag_test_suite(ag_test_suite.pk, submission.pk)
        tasks.grade_ag_test_suite_impl(ag_test_suite, submission)
        sleep_mock.assert_not_called()

    def test_ag_test_case_not_found_no_retry(self, sleep_mock) -> None:
        submission = obj_build.make_submission()
        ag_test_case = obj_build.make_ag_test_case()
        suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=ag_test_case.ag_test_suite,
            submission=submission
        )

        ag_models.AGTestCase.objects.get(pk=ag_test_case.pk).delete()
        tasks.grade_ag_test_case_impl(AutograderSandbox(), ag_test_case, suite_result)

        sleep_mock.assert_not_called()

    def test_suite_result_not_found_no_retry(self, sleep_mock) -> None:
        submission = obj_build.make_submission()
        ag_test_case = obj_build.make_ag_test_case()
        suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=ag_test_case.ag_test_suite,
            submission=submission
        )

        ag_models.AGTestSuiteResult.objects.get(pk=suite_result.pk).delete()
        tasks.grade_ag_test_case_impl(AutograderSandbox(), ag_test_case, suite_result)

        sleep_mock.assert_not_called()

    @tag('sandbox')
    def test_ag_test_command_not_found_no_retry(self, sleep_mock) -> None:
        submission = obj_build.make_submission()
        ag_test_command = obj_build.make_full_ag_test_command(
            set_arbitrary_points=False, set_arbitrary_expected_vals=False)
        ag_test_case = ag_test_command.ag_test_case

        suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=ag_test_case.ag_test_suite,
            submission=submission
        )
        test_result = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=ag_test_case,
            ag_test_suite_result=suite_result
        )

        ag_models.AGTestCommand.objects.get(pk=ag_test_command.pk).delete()
        with AutograderSandbox() as sandbox:
            tasks.grade_ag_test_command_impl(sandbox, ag_test_command, test_result)

        sleep_mock.assert_not_called()

    @tag('sandbox')
    def test_ag_test_case_result_not_found_no_retry(self, sleep_mock) -> None:
        submission = obj_build.make_submission()
        ag_test_command = obj_build.make_full_ag_test_command(
            set_arbitrary_points=False, set_arbitrary_expected_vals=False)
        ag_test_case = ag_test_command.ag_test_case

        suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=ag_test_case.ag_test_suite,
            submission=submission
        )
        test_result = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=ag_test_case,
            ag_test_suite_result=suite_result
        )

        ag_models.AGTestCaseResult.objects.get(pk=test_result.pk).delete()
        with AutograderSandbox() as sandbox:
            tasks.grade_ag_test_command_impl(sandbox, ag_test_command, test_result)

        sleep_mock.assert_not_called()


@mock.patch('autograder.utils.retry.sleep')
class GradeAGTestSuiteCallbacksTestCase(TransactionUnitTestBase):
    def setUp(self):
        super().setUp()
        self.submission = obj_build.make_submission()
        self.project = self.submission.group.project
        self.ag_test_suite = obj_build.make_ag_test_suite(
            self.project, setup_suite_cmd='false'  # "false" command exits nonzero
        )
        self.setup_finished_callback = mock.Mock()
        self.test_case_finished_callback = mock.Mock()

    def test_setup_finished_callback(self, *args) -> None:
        tasks.grade_ag_test_suite_impl(
            self.ag_test_suite,
            self.submission,
            on_suite_setup_finished=self.setup_finished_callback,
            on_test_case_finished=self.test_case_finished_callback
        )
        self._check_suite_setup_callback_args()

    def test_setup_finished_callback_submission_rejected(self, *args) -> None:
        self.ag_test_suite.validate_and_update(reject_submission_if_setup_fails=True)

        with self.assertRaises(SubmissionRejected):
            tasks.grade_ag_test_suite_impl(
                self.ag_test_suite,
                self.submission,
                on_suite_setup_finished=self.setup_finished_callback,
                on_test_case_finished=self.test_case_finished_callback
            )
        self._check_suite_setup_callback_args()

    def test_setup_finished_callback_no_setup_command(self, *args) -> None:
        self.ag_test_suite.validate_and_update(setup_suite_cmd='')

        tasks.grade_ag_test_suite_impl(
            self.ag_test_suite,
            self.submission,
            on_suite_setup_finished=self.setup_finished_callback,
            on_test_case_finished=self.test_case_finished_callback
        )
        self._check_suite_setup_callback_args()

    def _check_suite_setup_callback_args(self) -> None:
        self.assertEqual(1, self.setup_finished_callback.call_count)
        callback_args = self.setup_finished_callback.call_args.args
        self.assertEqual(1, len(callback_args))
        suite_result = callback_args[0]
        self.assertEqual(self.ag_test_suite, suite_result.ag_test_suite)
        self.assertEqual(self.submission, suite_result.submission)

        self.test_case_finished_callback.assert_not_called()

    def test_ag_test_case_finished_callback(self, *args) -> None:
        ag_test_case1 = obj_build.make_ag_test_case(self.ag_test_suite)
        ag_test_case2 = obj_build.make_ag_test_case(self.ag_test_suite)

        tasks.grade_ag_test_suite_impl(
            self.ag_test_suite,
            self.submission,
            on_suite_setup_finished=self.setup_finished_callback,
            on_test_case_finished=self.test_case_finished_callback
        )
        self.assertEqual(1, self.setup_finished_callback.call_count)

        self.assertEqual(2, self.test_case_finished_callback.call_count)
        call1 = self.test_case_finished_callback.call_args_list[0]
        self.assertEqual(1, len(call1.args))
        case_result = call1.args[0]
        self.assertEqual(ag_test_case1, case_result.ag_test_case)
        self.assertEqual(self.submission, case_result.ag_test_suite_result.submission)

        call2 = self.test_case_finished_callback.call_args_list[1]
        self.assertEqual(1, len(call2.args))
        case_result = call2.args[0]
        self.assertEqual(ag_test_case2, case_result.ag_test_case)
        self.assertEqual(self.submission, case_result.ag_test_suite_result.submission)
