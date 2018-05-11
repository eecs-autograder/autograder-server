from unittest import mock

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import tag

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core import constants
from autograder.grading_tasks import tasks
from autograder.utils.testing import UnitTestBase


class _MockException(Exception):
    pass


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
@mock.patch('autograder.grading_tasks.tasks.utils.time.sleep')
class GradeSubmissionTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.submission = obj_build.make_submission()
        self.project = self.submission.group.project

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
        with open(cmd_result.stderr_filename) as f:
            output = f.read()
        print(output)
        self.assertEqual(0, cmd_result.return_code, msg=output)
        self.assertEqual('hello', open(cmd_result.stdout_filename).read())
        self.assertEqual('whoops', open(cmd_result.stderr_filename).read())
        self.assertTrue(cmd_result.stdout_correct)
        self.assertTrue(cmd_result.stderr_correct)

        self.assertEqual(
            6, self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points_possible)
        self.assertEqual(6, self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points)
        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

    def test_one_ag_suite_one_non_deferred_student_suite_one_deferred_student_suite(self, *args):
        ag_suite = obj_build.make_ag_test_suite(self.project)
        ag_case = obj_build.make_ag_test_case(ag_suite)
        print_to_stdout_and_stderr = "bash -c 'printf hello; printf whoops >&2'"
        ag_cmd = obj_build.make_full_ag_test_command(ag_case, cmd=print_to_stdout_and_stderr)

        student_suite = ag_models.StudentTestSuite.objects.validate_and_create(
            name='mnkfoae',
            project=self.project)

        deferred_student_suite = ag_models.StudentTestSuite.objects.validate_and_create(
            name='deferryyyy',
            project=self.project,
            deferred=True)

        tasks.grade_submission(self.submission.pk)
        cmd_result = ag_models.AGTestCommandResult.objects.get(
            ag_test_command=ag_cmd,
            ag_test_case_result__ag_test_suite_result__submission=self.submission)

        student_suite_result = ag_models.StudentTestSuiteResult.objects.get(
            submission=self.submission,
            student_test_suite=student_suite)

        deferred_student_suite_result = ag_models.StudentTestSuiteResult.objects.get(
            submission=self.submission,
            student_test_suite=deferred_student_suite)

    def test_non_default_docker_image(self, *args):
        suite = obj_build.make_ag_test_suite(
            self.project, docker_image_to_use=constants.SupportedImages.eecs490)
        case = obj_build.make_ag_test_case(suite)
        cmd = obj_build.make_full_ag_test_command(
            case,
            cmd='racket --version',
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False,
            points_for_correct_return_code=3,
            expected_return_code=ag_models.ExpectedReturnCode.zero)
        tasks.grade_submission(self.submission.pk)

        cmd_result = ag_models.AGTestCommandResult.objects.get(
            ag_test_command=cmd,
            ag_test_case_result__ag_test_suite_result__submission=self.submission)
        self.assertEqual(0, cmd_result.return_code)

        self.assertEqual(
            3, self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points_possible)
        self.assertEqual(3, self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points)
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
            self.assertEqual('hello', open(res.stdout_filename).read())
            self.assertEqual('whoops', open(res.stderr_filename).read())
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
        cpp_pattern = ag_models.ExpectedStudentFile.objects.validate_and_create(
            project=self.project,
            pattern='*.cpp', max_num_matches=5)
        h_pattern = ag_models.ExpectedStudentFile.objects.validate_and_create(
            project=self.project,
            pattern='*.h', max_num_matches=5)

        uploaded_makefile = ag_models.InstructorFile.objects.validate_and_create(
            project=self.project,
            file_obj=SimpleUploadedFile('Makefile', makefile.encode()))

        suite = obj_build.make_ag_test_suite(self.project, setup_suite_cmd='make')
        suite.instructor_files_needed.add(uploaded_makefile)
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
            group=self.submission.group)
        tasks.grade_submission(submission.pk)

        cmd_res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        suite_res = cmd_res.ag_test_case_result.ag_test_suite_result
        print(suite_res.setup_stdout)
        print(suite_res.setup_stderr)
        self.assertEqual(0, suite_res.setup_return_code)
        self.assertTrue(cmd_res.stdout_correct)

    def test_run_grade_submission_on_already_graded_submission(self, *args):
        suite = obj_build.make_ag_test_suite(self.project)
        case = obj_build.make_ag_test_case(suite)
        cmd = obj_build.make_full_ag_test_command(case, cmd='printf hello')

        tasks.grade_submission(self.submission.pk)
        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual('hello', open(res.stdout_filename).read())

        cmd.cmd = 'printf weee'
        cmd.save()
        tasks.grade_submission(self.submission.pk)
        res = ag_models.AGTestCommandResult.objects.get(ag_test_command=cmd)
        self.assertEqual('weee', open(res.stdout_filename).read())

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
        self.assertEqual(' '.join(self.submission.group.member_names),
                         open(res.stdout_filename).read())

    def test_one_ag_suite_deferred_one_student_suite_deferred(self, *args):
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

        deferred_student_suite = ag_models.StudentTestSuite.objects.validate_and_create(
            name='deferryyyy',
            project=self.project,
            deferred=True)

        tasks.grade_submission(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(3, self.submission.get_fdbk(ag_models.FeedbackCategory.max).total_points)
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

        deferred_student_suite_result = ag_models.StudentTestSuiteResult.objects.get(
            submission=self.submission,
            student_test_suite=deferred_student_suite)

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

    @mock.patch('autograder.grading_tasks.tasks.grade_ag_test.grade_ag_test_command_impl',
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

    @mock.patch('autograder.grading_tasks.tasks.grade_ag_test.retry_should_recover',
                new=tasks.retry(max_num_retries=2))
    @mock.patch('autograder.grading_tasks.tasks.grade_ag_test.grade_ag_test_command_impl',
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
