import random
import shlex
from unittest import mock  # type: ignore

import subprocess
from autograder_sandbox import AutograderSandbox
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.test import tag

from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
from autograder.core import constants
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase, sleeper_subtest

from . import tasks


class _MockException(Exception):
    pass


class RetryDecoratorTestCase(UnitTestBase):
    def test_retry_and_succeed(self):
        arg_val = 42
        kwarg_val = "cheese"
        return_val = "winzorz!"

        should_throw = True

        @tasks.retry(max_num_retries=1, retry_delay_start=0, retry_delay_end=0)
        def func_to_retry(test_case, arg, kwarg=None):
            test_case.assertEqual(arg_val, arg)
            test_case.assertEqual(kwarg_val, kwarg)

            nonlocal should_throw
            if should_throw:
                should_throw = False
                raise Exception('Throooooow')

            return return_val

        self.assertEqual(return_val, func_to_retry(self, arg_val, kwarg_val))

    def test_max_retries_exceeded(self):
        @tasks.retry(max_num_retries=10, retry_delay_start=0, retry_delay_end=0)
        def func_to_retry():
            raise Exception('Errrrror')

        with self.assertRaises(tasks.MaxRetriesExceeded):
            func_to_retry()

    @mock.patch('autograder.grading_tasks.tasks.time.sleep')
    def test_retry_delay(self, mocked_sleep):
        max_num_retries = 3
        min_delay = 2
        max_delay = 6
        delay_step = 2

        @tasks.retry(max_num_retries=max_num_retries,
                     retry_delay_start=min_delay, retry_delay_end=max_delay,
                     retry_delay_step=delay_step)
        def func_to_retry():
            raise Exception

        with self.assertRaises(tasks.MaxRetriesExceeded):
            func_to_retry()

        mocked_sleep.assert_has_calls(
            [mock.call(delay) for delay in range(min_delay, max_delay, delay_step)])

    @mock.patch('autograder.grading_tasks.tasks.time.sleep')
    def test_retry_zero_delay(self, mocked_sleep):
        max_num_retries = 1

        @tasks.retry(max_num_retries=max_num_retries,
                     retry_delay_start=0, retry_delay_end=0)
        def func_to_retry():
            raise Exception

        with self.assertRaises(tasks.MaxRetriesExceeded):
            func_to_retry()

        mocked_sleep.assert_has_calls([mock.call(0) for i in range(max_num_retries)])


def _make_mock_grade_ag_test_cmd_fail_then_succeed(num_times_to_fail):
    def side_effect(*args):
        nonlocal num_times_to_fail
        if num_times_to_fail is None:
            raise _MockException('retry me i am error')

        if num_times_to_fail:
            num_times_to_fail -= 1
            raise _MockException('retry me i am error')

    return mock.Mock(wraps=tasks.grade_ag_test_command_impl, side_effect=side_effect)


@tag('slow', 'sandbox')
@mock.patch('autograder.grading_tasks.tasks.time.sleep')
class GradeSubmissionBasicIntegrationTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.submission = obj_build.build_submission()
        self.project = self.submission.submission_group.project

    def test_one_suite_one_case_one_cmd(self, *args):
        suite = obj_build.make_ag_test_suite(self.project)
        case = obj_build.make_ag_test_case(suite)
        print_to_stdout_and_stderr = "bash -c 'printf hello; printf whoops >&2'"
        cmd = obj_build.make_full_ag_test_command(
            case,
            cmd=print_to_stdout_and_stderr,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            points_for_correct_return_code=4,
            points_for_correct_stdout=1,
            points_for_correct_stderr=1,
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stdout_text="hello",
            expected_stderr_source=ag_models.ExpectedOutputSource.text,
            expected_stderr_text="whoops")
        tasks.grade_submission(self.submission.pk)

        cmd_result = ag_models.AGTestCommandResult.objects.get(
            ag_test_command=cmd,
            ag_test_case_result__ag_test_suite_result__submission=self.submission)
        self.assertEqual(0, cmd_result.return_code)
        self.assertEqual('hello', cmd_result.stdout)
        self.assertEqual('whoops', cmd_result.stderr)
        self.assertTrue(cmd_result.stdout_correct)
        self.assertTrue(cmd_result.stderr_correct)

        self.assertEqual(
            6, self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points_possible)
        self.assertEqual(6, self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points)
        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

    def test_multiple_suites_cases_and_cmds(self, *args):
        suite1 = obj_build.make_ag_test_suite(self.project)
        case1 = obj_build.make_ag_test_case(suite1)
        case2 = obj_build.make_ag_test_case(suite1)

        suite2 = obj_build.make_ag_test_suite(self.project)
        case3 = obj_build.make_ag_test_case(suite2)
        case4 = obj_build.make_ag_test_case(suite2)

        print_to_stdout_and_stderr = "bash -c 'printf hello; printf whoops >&2'"
        for case in case1, case2, case3, case4:
            for i in range(2):
                obj_build.make_full_ag_test_command(
                    ag_test_case=case,
                    cmd=print_to_stdout_and_stderr,
                    set_arbitrary_points=False,
                    set_arbitrary_expected_vals=False,
                    points_for_correct_return_code=4,
                    points_for_correct_stdout=1,
                    points_for_correct_stderr=1,
                    expected_return_code=ag_models.ExpectedReturnCode.zero,
                    expected_stdout_source=ag_models.ExpectedOutputSource.text,
                    expected_stdout_text="hello",
                    expected_stderr_source=ag_models.ExpectedOutputSource.text,
                    expected_stderr_text="whoops")

        tasks.grade_submission(self.submission.pk)

        cmd_results = ag_models.AGTestCommandResult.objects.filter(
            ag_test_case_result__ag_test_suite_result__submission=self.submission)

        for res in cmd_results:
            self.assertEqual(0, res.return_code)
            self.assertEqual('hello', res.stdout)
            self.assertEqual('whoops', res.stderr)
            self.assertTrue(res.stdout_correct)
            self.assertTrue(res.stderr_correct)

        self.assertEqual(48, self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points)
        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

    def test_sample_cpp_prog_test_with_student_patterns_and_project_makefile(self, *args):
        makefile = """
cpps = $(wildcard *.cpp)

program: $(cpps)
\tg++ -Wall -Wextra -pedantic -O1 $^ -o prog.exe
"""
        main_cpp = """
#include "file1.h"
#include "file2.h"

int main() {
    file1();
    file2();
    return 0;
}
"""
        file1_h = """
#ifndef FILE1_H
#define FILE1_H
    void file1();
#endif
"""
        file1_cpp = """
#include "file1.h"
#include <iostream>
using namespace std;
void file1() {
    cout << "file1" << endl;
}
"""
        file2_h = """
#ifndef FILE2_H
#define FILE2_H
    void file2();
#endif
"""
        file2_cpp = """
#include "file2.h"
#include <iostream>
using namespace std;
void file2() {
    cout << "file2" << endl;
}
"""
        cpp_pattern = ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            project=self.project,
            pattern='*.cpp', max_num_matches=5)
        h_pattern = ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            project=self.project,
            pattern='*.h', max_num_matches=5)

        uploaded_makefile = ag_models.UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=SimpleUploadedFile('Makefile', makefile.encode()))

        suite = obj_build.make_ag_test_suite(self.project, setup_suite_cmd='make')
        suite.project_files_needed.add(uploaded_makefile)
        suite.student_files_needed.add(cpp_pattern, h_pattern)
        case = obj_build.make_ag_test_case(suite)
        cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name='run program',
            ag_test_case=case,
            cmd='./prog.exe',
            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stdout_text='file1\nfile2\n')

        submission = ag_models.Submission.objects.validate_and_create(
            [SimpleUploadedFile('main.cpp', main_cpp.encode()),
             SimpleUploadedFile('file1.h', file1_h.encode()),
             SimpleUploadedFile('file1.cpp', file1_cpp.encode()),
             SimpleUploadedFile('file2.h', file2_h.encode()),
             SimpleUploadedFile('file2.cpp', file2_cpp.encode())],
            submission_group=self.submission.submission_group)
        tasks.grade_submission(submission.pk)

        cmd_res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        suite_res = cmd_res.ag_test_case_result.ag_test_suite_result
        print(suite_res.setup_stdout)
        print(suite_res.setup_stderr)
        self.assertEqual(0, suite_res.setup_return_code)
        self.assertTrue(cmd_res.stdout_correct)

    def test_regrade_submission(self, *args):
        suite = obj_build.make_ag_test_suite(self.project)
        case = obj_build.make_ag_test_case(suite)
        cmd = obj_build.make_full_ag_test_command(case, cmd='printf hello')

        tasks.grade_submission(self.submission.pk)
        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual('hello', res.stdout)

        cmd.cmd = 'printf weee'
        cmd.save()
        tasks.grade_submission(self.submission.pk)
        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual('weee', res.stdout)

    def test_shell_injection_doesnt_work(self, *args):
        suite = obj_build.make_ag_test_suite(self.project)
        case = obj_build.make_ag_test_case(suite)
        bad_cmd = 'echo "haxorz"; sleep 20'
        cmd = obj_build.make_full_ag_test_command(
            case,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            cmd=bad_cmd)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(' '.join(shlex.split(bad_cmd)[1:]) + '\n', res.stdout)

    def test_network_access_allowed_in_suite(self, *args):
        suite1 = obj_build.make_ag_test_suite(self.project, allow_network_access=True)
        case1 = obj_build.make_ag_test_case(suite1)
        cmd = obj_build.make_full_ag_test_command(
            case1, cmd='ping -c 2 www.google.com',
            expected_return_code=ag_models.ExpectedReturnCode.zero)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.return_code_correct)

    def test_group_member_names_in_environment(self, *args):
        suite = obj_build.make_ag_test_suite(self.project)
        case = obj_build.make_ag_test_case(suite)
        cmd = obj_build.make_full_ag_test_command(case, cmd='bash -c "printf $usernames"')
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(' '.join(self.submission.submission_group.member_names), res.stdout)

    def test_one_suite_deferred(self, *args):
        suite1 = obj_build.make_ag_test_suite(self.project, deferred=False)
        case1 = obj_build.make_ag_test_case(suite1)
        cmd1 = obj_build.make_full_ag_test_command(
            case1,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            points_for_correct_return_code=1)
        suite2 = obj_build.make_ag_test_suite(self.project, deferred=True)
        case2 = obj_build.make_ag_test_case(suite2)
        cmd2 = obj_build.make_full_ag_test_command(
            case2,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            points_for_correct_return_code=2)
        tasks.grade_submission(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(3, self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points)
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

    def test_all_suites_deferred(self, *args):
        suite1 = obj_build.make_ag_test_suite(self.project, deferred=True)
        case1 = obj_build.make_ag_test_case(suite1)
        cmd1 = obj_build.make_full_ag_test_command(
            case1,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            points_for_correct_return_code=1)
        suite2 = obj_build.make_ag_test_suite(self.project, deferred=True)
        case2 = obj_build.make_ag_test_case(suite2)
        cmd2 = obj_build.make_full_ag_test_command(
            case2,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            points_for_correct_return_code=2)
        tasks.grade_submission(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(3, self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points)
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

    def test_submission_removed_from_queue(self, *args):
        suite = obj_build.make_ag_test_suite(self.project, deferred=True)
        case = obj_build.make_ag_test_case(suite)
        cmd = obj_build.make_full_ag_test_command(case)
        self.submission.status = ag_models.Submission.GradingStatus.removed_from_queue
        self.submission.save()
        tasks.grade_submission(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.removed_from_queue,
                         self.submission.status)

    @mock.patch('autograder.grading_tasks.tasks.grade_ag_test_command_impl',
                new=_make_mock_grade_ag_test_cmd_fail_then_succeed(1))
    def test_non_deferred_retry_on_error(self, *args):
        suite = obj_build.make_ag_test_suite(self.project)
        case = obj_build.make_ag_test_case(suite)
        cmd = obj_build.make_full_ag_test_command(
            case,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            points_for_correct_return_code=3)
        tasks.grade_submission(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)
        self.assertEqual(3, self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points)

    @mock.patch('autograder.grading_tasks.tasks.grade_ag_test_command_impl',
                new=_make_mock_grade_ag_test_cmd_fail_then_succeed(
                    settings.AG_TEST_MAX_RETRIES + 1))
    def test_non_deferred_max_num_retries_exceeded(self, impl_mock, *args):
        suite = obj_build.make_ag_test_suite(self.project)
        case = obj_build.make_ag_test_case(suite)
        cmd = obj_build.make_full_ag_test_command(
            case,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            points_for_correct_return_code=3)

        with self.assertRaises(tasks.MaxRetriesExceeded):
            tasks.grade_submission(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.error,
                         self.submission.status)
        self.assertTrue(self.submission.error_msg.find('MaxRetriesExceeded') != -1)

    @mock.patch('autograder.grading_tasks.tasks.grade_ag_test_command_impl',
                new=_make_mock_grade_ag_test_cmd_fail_then_succeed(
                    settings.AG_TEST_MAX_RETRIES * 4))
    def test_deferred_retry_on_error(self, impl_mock, *args):
        suite = obj_build.make_ag_test_suite(self.project, deferred=True)
        case = obj_build.make_ag_test_case(suite)
        cmd = obj_build.make_full_ag_test_command(
            case,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            points_for_correct_return_code=3)

        tasks.grade_submission(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(0, res.return_code)
        self.assertTrue(res.return_code_correct)

        self.assertEqual(3, self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points)

    @mock.patch('autograder.grading_tasks.tasks.retry_should_recover',
                new=tasks.retry(max_num_retries=2))
    @mock.patch('autograder.grading_tasks.tasks.grade_ag_test_command_impl',
                new=_make_mock_grade_ag_test_cmd_fail_then_succeed(None))
    def test_deferred_ag_test_error(self, *args):
        suite = obj_build.make_ag_test_suite(self.project, deferred=True)
        case = obj_build.make_ag_test_case(suite)
        cmd = obj_build.make_full_ag_test_command(
            case,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            points_for_correct_return_code=3)

        with self.assertRaises(tasks.MaxRetriesExceeded):
            tasks.grade_submission(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.error,
                         self.submission.status)
        self.assertTrue(self.submission.error_msg.find('MaxRetriesExceeded') != -1)


@tag('slow', 'sandbox')
class AGTestCommandCorrectnessTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.submission = obj_build.build_submission()
        self.project = self.submission.submission_group.project
        self.ag_test_suite = obj_build.make_ag_test_suite(self.project)
        self.ag_test_case = obj_build.make_ag_test_case(self.ag_test_suite)

    def test_points_awarded_and_deducted(self):
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

    def test_diff_ignore_case_whitespace_changes_and_blank_lines(self):
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

    def test_diff_ignore_whitespace(self):
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

    def test_correct_expected_return_code_zero(self):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "exit 0"',
            expected_return_code=ag_models.ExpectedReturnCode.zero)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.return_code_correct)

    def test_wrong_expected_return_code_zero(self):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "exit 1"',
            expected_return_code=ag_models.ExpectedReturnCode.zero)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertFalse(res.return_code_correct)

    def test_correct_expected_return_code_nonzero(self):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "exit 1"',
            expected_return_code=ag_models.ExpectedReturnCode.nonzero)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.return_code_correct)

    def test_wrong_expected_return_code_nonzero(self):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "exit 0"',
            expected_return_code=ag_models.ExpectedReturnCode.nonzero)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertFalse(res.return_code_correct)

    def test_correct_expected_stdout_text(self):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='printf "hello"',
            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stdout_text='hello')
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.stdout_correct)

    def test_wrong_expected_stdout_text(self):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='printf "nope"',
            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stdout_text='hello')
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertFalse(res.stdout_correct)

    def test_correct_expected_stdout_proj_file(self):
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

    def test_wrong_expected_stdout_proj_file(self):
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

    def test_correct_expected_stderr_text(self):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "printf hello >&2"',
            expected_stderr_source=ag_models.ExpectedOutputSource.text,
            expected_stderr_text='hello')
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.stderr_correct)

    def test_wrong_expected_stderr_text(self):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='bash -c "printf nopers >&2"',
            expected_stderr_source=ag_models.ExpectedOutputSource.text,
            expected_stderr_text='hello')
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertFalse(res.stderr_correct)

    def test_correct_expected_stderr_proj_file(self):
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

    def test_wrong_expected_stderr_proj_file(self):
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

    def test_stdin_source_text(self):
        text = 'wuluigio'
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='cat',
            stdin_source=ag_models.StdinSource.text,
            stdin_text=text)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(text, res.stdout)

    def test_stdin_source_proj_file(self):
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
        self.assertEqual(text, res.stdout)

    def test_stdin_source_setup_stdout(self):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='cat',
            stdin_source=ag_models.StdinSource.setup_stdout)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(self.setup_stdout, res.stdout)

    def test_stdin_source_setup_stderr(self):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            cmd='cat',
            stdin_source=ag_models.StdinSource.setup_stderr)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual(self.setup_stderr, res.stdout)


@tag('slow', 'sandbox')
class ResourceLimitsExceededTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.submission = obj_build.build_submission()
        self.project = self.submission.submission_group.project
        self.ag_test_suite = obj_build.make_ag_test_suite(self.project)
        self.ag_test_case = obj_build.make_ag_test_case(self.ag_test_suite)

        self.too_much_output_size = constants.MAX_OUTPUT_LENGTH * 10
        too_much_output_prog = """
import sys
print('a' * {0})
print('b' * {0}, file=sys.stderr)
        """.format(self.too_much_output_size)
        self.too_much_output_file = ag_models.UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=SimpleUploadedFile('too_long.py', too_much_output_prog.encode())
        )  # type: ag_models.UploadedFile

        self.timeout_cmd = "sleep 10"

        self.ag_test_suite.project_files_needed.add(self.too_much_output_file)

    def test_program_times_out(self):
        cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            cmd=self.timeout_cmd,
            time_limit=1)
        tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertTrue(res.timed_out)

    def test_program_prints_too_much_output(self):
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
        print(len(res.stdout))
        # Rather than checking again for the specific truncation message
        # appended to the output, we'll just assert that the resulting
        # output length is less than the max + 30 chars or so.
        self.assertGreater(len(res.stdout), constants.MAX_OUTPUT_LENGTH)
        self.assertLess(len(res.stdout), constants.MAX_OUTPUT_LENGTH + 30)
        print(len(res.stderr))
        self.assertGreater(len(res.stderr), constants.MAX_OUTPUT_LENGTH)
        self.assertLess(len(res.stderr), constants.MAX_OUTPUT_LENGTH + 30)

    def test_suite_setup_and_teardown_return_code_set(self):
        self.ag_test_suite.validate_and_update(setup_suite_cmd='bash -c "exit 2"',
                                               teardown_suite_cmd='bash -c "exit 3"')
        tasks.grade_submission(self.submission.pk)
        res = ag_models.AGTestSuiteResult.objects.get(submission=self.submission)
        self.assertEqual(2, res.setup_return_code)
        self.assertEqual(3, res.teardown_return_code)

    def test_setup_and_teardown_time_out(self):
        self.ag_test_suite.validate_and_update(setup_suite_cmd=self.timeout_cmd,
                                               teardown_suite_cmd=self.timeout_cmd)
        with mock.patch('autograder.core.constants.MAX_SUBPROCESS_TIMEOUT', new=1):
            tasks.grade_submission(self.submission.pk)

        res = ag_models.AGTestSuiteResult.objects.get(submission=self.submission)
        self.assertTrue(res.setup_timed_out)
        self.assertTrue(res.teardown_timed_out)

    def test_setup_and_teardown_print_too_much_output(self):
        self.ag_test_suite.validate_and_update(
            setup_suite_cmd='python3 ' + self.too_much_output_file.name,
            teardown_suite_cmd='python3 ' + self.too_much_output_file.name)
        tasks.grade_submission(self.submission.pk)
        res = ag_models.AGTestSuiteResult.objects.get(submission=self.submission)

        print(len(res.setup_stdout))
        # Rather than checking again for the specific truncation message
        # appended to the output, we'll just assert that the resulting
        # output length is less than the max + 30 chars or so.
        self.assertGreater(len(res.setup_stdout), constants.MAX_OUTPUT_LENGTH)
        self.assertLess(len(res.setup_stdout), constants.MAX_OUTPUT_LENGTH + 30)
        print(len(res.setup_stderr))
        self.assertGreater(len(res.setup_stderr), constants.MAX_OUTPUT_LENGTH)
        self.assertLess(len(res.setup_stderr), constants.MAX_OUTPUT_LENGTH + 30)

        print(len(res.teardown_stdout))
        self.assertGreater(len(res.teardown_stdout), constants.MAX_OUTPUT_LENGTH)
        self.assertLess(len(res.teardown_stdout), constants.MAX_OUTPUT_LENGTH + 30)
        print(len(res.teardown_stderr))
        self.assertGreater(len(res.teardown_stderr), constants.MAX_OUTPUT_LENGTH)
        self.assertLess(len(res.teardown_stderr), constants.MAX_OUTPUT_LENGTH + 30)

    def test_time_process_stack_and_virtual_mem_limits_passed_to_run_command(self,):
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
        run_command_mock = mock.Mock(return_value=subprocess.CompletedProcess(
            ['asdf'], returncode=0, stdout='adflkjasdf', stderr='adklfjasdkfjasdj'))
        sandbox.run_command = run_command_mock
        with mock.patch('autograder.grading_tasks.tasks.AutograderSandbox', return_value=sandbox):
            tasks.grade_submission(self.submission.pk)

        expected_setup_and_teardown_resource_kwargs = {
            'timeout': constants.MAX_SUBPROCESS_TIMEOUT,
            'max_num_processes': constants.MAX_PROCESS_LIMIT,
            'max_stack_size': constants.MAX_STACK_SIZE_LIMIT,
            'max_virtual_memory': constants.MAX_VIRTUAL_MEM_LIMIT,
        }
        expected_cmd_args = {
            'timeout': time_limit,
            'max_num_processes': process_spawn_limit,
            'max_stack_size': stack_size_limit,
            'max_virtual_memory': virtual_memory_limit,
        }
        run_command_mock.assert_has_calls([
            mock.call(shlex.split(self.ag_test_suite.setup_suite_cmd),
                      as_root=False, **expected_setup_and_teardown_resource_kwargs),
            mock.call(shlex.split(cmd.cmd), input='', as_root=False, **expected_cmd_args),
            mock.call(shlex.split(self.ag_test_suite.teardown_suite_cmd),
                      as_root=False, **expected_setup_and_teardown_resource_kwargs)
        ])

# --------------------------------------------------------------------------------------


@tag('slow')
class RaceConditionTestCase(UnitTestBase):
    def test_remove_from_queue_when_being_marked_as_being_graded_race_condition_prevented(self):
        group = obj_build.make_group(members_role=ag_models.UserRole.admin)
        submission = obj_build.build_submission(submission_group=group)

        path = ('autograder.grading_tasks.tasks.ag_models'
                '.Submission.GradingStatus.removed_from_queue')

        @sleeper_subtest(
            path,
            new_callable=mock.PropertyMock,
            return_value=(ag_models.Submission.GradingStatus.removed_from_queue))
        def do_request_and_wait():
            tasks.grade_submission(submission.pk)

        subtest = do_request_and_wait()

        print('sending remove from queue request')
        client = APIClient()
        client.force_authenticate(
            submission.submission_group.members.first())
        response = client.post(reverse('submission-remove-from-queue',
                                       kwargs={'pk': submission.pk}))
        subtest.join()
        submission.refresh_from_db()
        self.assertNotEqual(
            ag_models.Submission.GradingStatus.removed_from_queue,
            submission.status)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         submission.status)
