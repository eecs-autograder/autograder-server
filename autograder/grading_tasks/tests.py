import subprocess
from typing import Iterable
from unittest import mock  # type: ignore

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.test import tag

from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
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
class GradeSubmissionTestCase(UnitTestBase):
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

    def test_one_suite_deferred(self, *args):
        suite1 = obj_build.make_ag_test_suite(self.project, deferred=False)
        case1 = obj_build.make_ag_test_case(suite1)
        cmd1 = obj_build.make_full_ag_test_command(
            case1,
            set_arbitrary_points=False,
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            points_for_correct_return_code=1)
        suite2 = obj_build.make_ag_test_suite(self.project, deferred=True)
        case2 = obj_build.make_ag_test_case(suite2)
        cmd2 = obj_build.make_full_ag_test_command(
            case2,
            set_arbitrary_points=False,
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
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            points_for_correct_return_code=1)
        suite2 = obj_build.make_ag_test_suite(self.project, deferred=True)
        case2 = obj_build.make_ag_test_case(suite2)
        cmd2 = obj_build.make_full_ag_test_command(
            case2,
            set_arbitrary_points=False,
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
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            points_for_correct_return_code=3)

        with self.assertRaises(tasks.MaxRetriesExceeded):
            tasks.grade_submission(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.error,
                         self.submission.status)
        self.assertTrue(self.submission.error_msg.find('MaxRetriesExceeded') != -1)


@tag('slow', 'sandbox')
class GradeAGTestCommandTestCase(UnitTestBase):
    def test_points_awarded_and_deducted(self):
        self.fail()

    def test_flexible_diff_settings_used(self):
        self.fail()

    def test_program_prints_too_much_output(self):
        self.fail()

    def test_shell_injection_doesnt_work(self):
        self.fail()

    def test_files_added_to_sandbox(self):
        self.fail()

    def test_patterns_expanded_to_student_files_in_cmd(self):
        self.fail()

    # 1 correct, 1 incorrect for these
    def test_expected_return_code_zero(self):
        self.fail()

    def test_expected_return_code_nonzero(self):
        self.fail()

    def test_expected_stdout_text(self):
        self.fail()

    def test_expected_stdout_proj_file(self):
        self.fail()

    def test_expected_stderr_text(self):
        self.fail()

    def test_expected_stderr_proj_file(self):
        self.fail()

    def test_stdin_source_text(self):
        self.fail()

    def test_stdin_source_proj_file(self):
        self.fail()

    def test_stdin_source_setup_stdout(self):
        self.fail()

    def test_stdin_source_setup_stderr(self):
        self.fail()

    def test_setup_prints_too_much_output(self):
        self.fail()

    def test_teardown_prints_too_much_output(self):
        self.fail()

    def test_setup_times_out(self):
        self.fail()

    def test_setup_exceeds_process_limit(self):
        self.fail()

    def test_setup_exceeds_stack_limit(self):
        self.fail()

    def test_setup_exceeds_virtual_mem_limit(self):
        self.fail()

    def test_teardown_times_out(self):
        self.fail()

    def test_teardown_exceeds_process_limit(self):
        self.fail()

    def test_teardown_exceeds_stack_limit(self):
        self.fail()

    def test_teardown_exceeds_virtual_mem_limit(self):
        self.fail()

    def test_program_times_out(self):
        self.fail()

    def test_program_exceeds_process_limit(self):
        self.fail()

    def test_program_exceeds_stack_limit(self):
        self.fail()

    def test_program_exceeds_virtual_mem_limit(self):
        self.fail()


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


# --------------------------------------------------------------------------------------

_NEEDS_FILES_TEST = b'''
import os
import fnmatch

def main():
    num_files = len(fnmatch.filter(os.listdir('.'), 'test*.cpp'))
    if num_files != 2:
        print('booooo')
        raise SystemExit(1)

    print('yay')


if __name__ == '__main__':
    main()
'''

_UNIT_TEST = b'''
#include "impl.h"

#include <iostream>
#include <cassert>

using namespace std;

int main()
{
    assert(spam() == 42);
    cout << "yay!" << endl;
}
'''

_IMPL_H = b'''
#ifndef IMPL_H
#define IMPL_H

int spam();

#endif
'''

_IMPL_CPP = b'''
#include "impl.h"

int spam()
{
    return 42;
}
'''

_TOO_MUCH_OUTPUT_IMPL_CPP = b'''
#include <iostream>
#include <string>
using namespace std;

int spam()
{
    while (true)
    {
        cout << string(1000000, 'x') << endl;
    }
    return 42;
}
'''
