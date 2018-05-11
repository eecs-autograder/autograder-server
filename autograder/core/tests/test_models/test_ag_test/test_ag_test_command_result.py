import os
import tempfile
from io import FileIO
from typing import Callable, Union
from unittest import mock

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase


class AGTestCommandResultTestCase(UnitTestBase):
    def setUp(self):
        submission = obj_build.make_submission()
        self.project = submission.group.project
        suite = ag_models.AGTestSuite.objects.validate_and_create(
            name='kajsdhf', project=self.project)
        self.ag_test_case = ag_models.AGTestCase.objects.validate_and_create(
            name='aksdbva', ag_test_suite=suite)
        suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            submission=submission, ag_test_suite=suite)
        self.ag_test_case_result = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=self.ag_test_case, ag_test_suite_result=suite_result)

        # Set normal feedback to max
        self.ag_test_command = obj_build.make_full_ag_test_command(
            self.ag_test_case,
            normal_fdbk_config={
                'return_code_fdbk_level': ag_models.ValueFeedbackLevel.get_max(),
                'stdout_fdbk_level': ag_models.ValueFeedbackLevel.get_max(),
                'stderr_fdbk_level': ag_models.ValueFeedbackLevel.get_max(),
                'show_points': True,
                'show_actual_return_code': True,
                'show_actual_stdout': True,
                'show_actual_stderr': True,
                'show_whether_timed_out': True
            }
        )
        self.max_points_possible = (self.ag_test_command.points_for_correct_return_code
                                    + self.ag_test_command.points_for_correct_stdout
                                    + self.ag_test_command.points_for_correct_stderr)
        self.min_points_possible = (self.ag_test_command.deduction_for_wrong_return_code
                                    + self.ag_test_command.deduction_for_wrong_stdout
                                    + self.ag_test_command.deduction_for_wrong_stderr)

    def make_correct_result(self) -> ag_models.AGTestCommandResult:
        return obj_build.make_correct_ag_test_command_result(
            ag_test_command=self.ag_test_command,
            ag_test_case_result=self.ag_test_case_result)

    def make_incorrect_result(self) -> ag_models.AGTestCommandResult:
        return obj_build.make_incorrect_ag_test_command_result(
            ag_test_command=self.ag_test_command,
            ag_test_case_result=self.ag_test_case_result,
            timed_out=True)

    def test_output_filenames(self):
        result = self.make_correct_result()
        expected_stdout_name = os.path.join(
            core_ut.get_result_output_dir(
                result.ag_test_case_result.ag_test_suite_result.submission),
            'cmd_result_' + str(result.pk) + '_stdout')
        self.assertEqual(expected_stdout_name, result.stdout_filename)

        expected_stderr_name = os.path.join(
            core_ut.get_result_output_dir(
                result.ag_test_case_result.ag_test_suite_result.submission),
            'cmd_result_' + str(result.pk) + '_stderr')
        self.assertEqual(expected_stderr_name, result.stderr_filename)

    def test_feedback_calculator_factory_method(self):
        # check against the actual objects (their pks)
        result = self.make_correct_result()
        self.assertEqual(self.ag_test_command.normal_fdbk_config,
                         result.get_fdbk(ag_models.FeedbackCategory.normal).fdbk_conf)
        self.assertEqual(self.ag_test_command.ultimate_submission_fdbk_config,
                         result.get_fdbk(ag_models.FeedbackCategory.ultimate_submission).fdbk_conf)
        self.assertEqual(self.ag_test_command.past_limit_submission_fdbk_config,
                         result.get_fdbk(
                             ag_models.FeedbackCategory.past_limit_submission).fdbk_conf)
        self.assertEqual(self.ag_test_command.staff_viewer_fdbk_config,
                         result.get_fdbk(ag_models.FeedbackCategory.staff_viewer).fdbk_conf)

        max_fdbk = result.get_fdbk(ag_models.FeedbackCategory.max).fdbk_conf
        self.assertEqual(ag_models.ValueFeedbackLevel.get_max(), max_fdbk.return_code_fdbk_level)
        self.assertEqual(ag_models.ValueFeedbackLevel.get_max(), max_fdbk.stdout_fdbk_level)
        self.assertEqual(ag_models.ValueFeedbackLevel.get_max(), max_fdbk.stderr_fdbk_level)
        self.assertTrue(max_fdbk.show_points)
        self.assertTrue(max_fdbk.show_actual_return_code)
        self.assertTrue(max_fdbk.show_actual_stdout)
        self.assertTrue(max_fdbk.show_actual_stderr)
        self.assertTrue(max_fdbk.show_whether_timed_out)

    def test_points_everything_correct_max_fdbk(self):
        cmd_result = self.make_correct_result()
        fdbk = cmd_result.get_fdbk(ag_models.FeedbackCategory.max)

        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points_possible)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points_possible)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points_possible)

        self.assertEqual(self.max_points_possible, fdbk.total_points)
        self.assertEqual(self.max_points_possible, fdbk.total_points_possible)

    def test_points_everything_incorrect_max_fdbk(self):
        cmd_result = self.make_incorrect_result()
        fdbk = cmd_result.get_fdbk(ag_models.FeedbackCategory.max)

        self.assertEqual(self.ag_test_command.deduction_for_wrong_return_code,
                         fdbk.return_code_points)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points_possible)
        self.assertEqual(self.ag_test_command.deduction_for_wrong_stdout,
                         fdbk.stdout_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points_possible)
        self.assertEqual(self.ag_test_command.deduction_for_wrong_stderr,
                         fdbk.stderr_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points_possible)

        self.assertEqual(self.min_points_possible, fdbk.total_points)
        self.assertEqual(self.max_points_possible, fdbk.total_points_possible)

    def test_return_code_not_checked(self):
        self.ag_test_command.validate_and_update(
            expected_return_code=ag_models.ExpectedReturnCode.none)

        correct_cmd_result = self.make_correct_result()
        fdbk = correct_cmd_result.get_fdbk(ag_models.FeedbackCategory.max)
        self.assertEqual(ag_models.ExpectedReturnCode.none, fdbk.expected_return_code)
        self.assertIsNone(fdbk.return_code_correct)
        self.assertEqual(0, fdbk.return_code_points)
        self.assertEqual(0, fdbk.return_code_points_possible)

        expected_total_pts = (self.ag_test_command.points_for_correct_stdout
                              + self.ag_test_command.points_for_correct_stderr)
        self.assertEqual(expected_total_pts, fdbk.total_points)
        expected_total_pts_possible = expected_total_pts
        self.assertEqual(expected_total_pts_possible, fdbk.total_points_possible)

        correct_cmd_result.delete()

        incorrect_cmd_result = self.make_incorrect_result()
        fdbk = incorrect_cmd_result.get_fdbk(ag_models.FeedbackCategory.max)
        self.assertIsNone(fdbk.return_code_correct)
        self.assertEqual(0, fdbk.return_code_points)
        self.assertEqual(0, fdbk.return_code_points_possible)

        expected_total_pts = (self.ag_test_command.deduction_for_wrong_stdout
                              + self.ag_test_command.deduction_for_wrong_stderr)
        self.assertEqual(expected_total_pts, fdbk.total_points)
        self.assertEqual(expected_total_pts_possible, fdbk.total_points_possible)

    def test_stdout_not_checked(self):
        self.ag_test_command.validate_and_update(
            expected_stdout_source=ag_models.ExpectedOutputSource.none)

        correct_cmd_result = self.make_correct_result()
        fdbk = correct_cmd_result.get_fdbk(ag_models.FeedbackCategory.max)
        self.assertIsNone(fdbk.stdout_correct)
        self.assertIsNone(fdbk.stdout_diff)
        self.assertEqual(_stdout_text(correct_cmd_result), _stdout_text(fdbk))
        self.assertEqual(0, fdbk.stdout_points)
        self.assertEqual(0, fdbk.stdout_points_possible)

        expected_total_pts = (self.ag_test_command.points_for_correct_return_code
                              + self.ag_test_command.points_for_correct_stderr)
        expected_total_pts_possible = expected_total_pts
        self.assertEqual(expected_total_pts, fdbk.total_points)
        self.assertEqual(expected_total_pts_possible, fdbk.total_points_possible)

        correct_cmd_result.delete()

        incorrect_cmd_result = self.make_incorrect_result()
        fdbk = incorrect_cmd_result.get_fdbk(ag_models.FeedbackCategory.max)
        self.assertIsNone(fdbk.stdout_correct)
        self.assertEqual(0, fdbk.stdout_points)
        self.assertEqual(0, fdbk.stdout_points_possible)

        expected_total_pts = (self.ag_test_command.deduction_for_wrong_return_code
                              + self.ag_test_command.deduction_for_wrong_stderr)
        self.assertEqual(expected_total_pts, fdbk.total_points)
        self.assertEqual(expected_total_pts_possible, fdbk.total_points_possible)

    def test_stderr_not_checked(self):
        self.ag_test_command.validate_and_update(
            expected_stderr_source=ag_models.ExpectedOutputSource.none)

        correct_cmd_result = self.make_correct_result()
        fdbk = correct_cmd_result.get_fdbk(ag_models.FeedbackCategory.max)
        self.assertIsNone(fdbk.stderr_correct)
        self.assertIsNone(fdbk.stderr_diff)
        self.assertEqual(_stderr_text(correct_cmd_result), _stderr_text(fdbk))
        self.assertEqual(0, fdbk.stderr_points)
        self.assertEqual(0, fdbk.stderr_points_possible)

        expected_total_pts = (self.ag_test_command.points_for_correct_return_code
                              + self.ag_test_command.points_for_correct_stdout)
        expected_total_pts_possible = expected_total_pts
        self.assertEqual(expected_total_pts, fdbk.total_points)
        self.assertEqual(expected_total_pts_possible, fdbk.total_points_possible)

        correct_cmd_result.delete()

        incorrect_cmd_result = self.make_incorrect_result()
        fdbk = incorrect_cmd_result.get_fdbk(ag_models.FeedbackCategory.max)
        self.assertIsNone(fdbk.stderr_correct)
        self.assertEqual(0, fdbk.stderr_points)
        self.assertEqual(0, fdbk.stderr_points_possible)

        expected_total_pts = (self.ag_test_command.deduction_for_wrong_return_code
                              + self.ag_test_command.deduction_for_wrong_stdout)
        self.assertEqual(expected_total_pts, fdbk.total_points)
        self.assertEqual(expected_total_pts_possible, fdbk.total_points_possible)

    def test_return_code_correctness_hidden(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            return_code_fdbk_level=ag_models.ValueFeedbackLevel.no_feedback)

        correct_result = self.make_correct_result()
        fdbk = correct_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.return_code_correct)
        self.assertEqual(0, fdbk.return_code_points)
        self.assertEqual(0, fdbk.return_code_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.return_code_correct)
        self.assertEqual(0, fdbk.return_code_points)
        self.assertEqual(0, fdbk.return_code_points_possible)

    def test_return_code_correctness_show_correct_or_incorrect(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            return_code_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect)

        correct_result = self.make_correct_result()
        fdbk = correct_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertTrue(fdbk.return_code_correct)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertFalse(fdbk.return_code_correct)
        self.assertEqual(self.ag_test_command.deduction_for_wrong_return_code,
                         fdbk.return_code_points)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points_possible)

    def test_return_code_correctness_show_expected_and_actual(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            return_code_fdbk_level=ag_models.ValueFeedbackLevel.expected_and_actual)

        correct_result = self.make_correct_result()
        fdbk = correct_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertTrue(fdbk.return_code_correct)
        self.assertEqual(self.ag_test_command.expected_return_code, fdbk.expected_return_code)
        self.assertEqual(correct_result.return_code, fdbk.actual_return_code)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertFalse(fdbk.return_code_correct)
        self.assertEqual(self.ag_test_command.expected_return_code, fdbk.expected_return_code)
        self.assertEqual(incorrect_result.return_code, fdbk.actual_return_code)
        self.assertEqual(self.ag_test_command.deduction_for_wrong_return_code,
                         fdbk.return_code_points)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points_possible)

    def test_return_code_show_actual(self):
        # Show actual return code, but not expected return code or points.
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            return_code_fdbk_level=ag_models.ValueFeedbackLevel.no_feedback,
            show_actual_return_code=True)
        result = self.make_correct_result()
        fdbk = result.get_fdbk(ag_models.FeedbackCategory.normal)

        self.assertEqual(result.return_code, fdbk.actual_return_code)
        self.assertIsNone(fdbk.return_code_correct)
        self.assertEqual(0, fdbk.return_code_points)
        self.assertEqual(0, fdbk.return_code_points_possible)

    def test_return_code_show_correctness_but_not_actual(self):
        # Show return code correctness and points, but not actual return code.
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            return_code_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            show_actual_return_code=False)
        result = self.make_correct_result()
        fdbk = result.get_fdbk(ag_models.FeedbackCategory.normal)

        self.assertIsNone(fdbk.actual_return_code)
        self.assertIsNone(fdbk.expected_return_code)
        self.assertTrue(fdbk.return_code_correct)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points_possible)

    def test_return_code_show_expected_and_actual_overrides_show_actual(self):
        # Show expected and actual return code (overrides show_actual_return_code setting).
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            return_code_fdbk_level=ag_models.ValueFeedbackLevel.expected_and_actual,
            show_actual_return_code=False)
        result = self.make_correct_result()
        fdbk = result.get_fdbk(ag_models.FeedbackCategory.normal)

        self.assertIsNotNone(fdbk.actual_return_code)
        self.assertIsNotNone(fdbk.expected_return_code)
        self.assertTrue(fdbk.return_code_correct)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points)

    def test_show_timed_out(self):
        result = self.make_correct_result()
        self.assertFalse(result.get_fdbk(ag_models.FeedbackCategory.normal).timed_out)

        result.delete()

        result = self.make_incorrect_result()
        self.assertTrue(result.get_fdbk(ag_models.FeedbackCategory.normal).timed_out)

    def test_hide_timed_out(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            show_whether_timed_out=False)

        result = self.make_correct_result()
        self.assertIsNone(result.get_fdbk(ag_models.FeedbackCategory.normal).timed_out)

        result.delete()

        result = self.make_incorrect_result()
        self.assertIsNone(result.get_fdbk(ag_models.FeedbackCategory.normal).timed_out)

    def test_timed_out_with_return_code_stdout_and_stderr_None_count_as_wrong(self):
        result = ag_models.AGTestCommandResult.objects.validate_and_create(
            ag_test_command=self.ag_test_command,
            ag_test_case_result=self.ag_test_case_result,
            timed_out=True)
        fdbk = result.get_fdbk(ag_models.FeedbackCategory.max)
        self.assertFalse(fdbk.return_code_correct)
        self.assertFalse(fdbk.stdout_correct)
        self.assertFalse(fdbk.stderr_correct)

    def test_stdout_correctness_hidden(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stdout_fdbk_level=ag_models.ValueFeedbackLevel.no_feedback)
        correct_result = self.make_correct_result()
        fdbk = correct_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.stdout_correct)
        self.assertIsNone(fdbk.stdout_diff)
        self.assertEqual(0, fdbk.stdout_points)
        self.assertEqual(0, fdbk.stdout_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.stdout_correct)
        self.assertIsNone(fdbk.stdout_diff)
        self.assertEqual(0, fdbk.stdout_points)
        self.assertEqual(0, fdbk.stdout_points_possible)

    def test_stdout_correctness_show_correct_or_incorrect(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stdout_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect)

        correct_result = self.make_correct_result()
        fdbk = correct_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertTrue(fdbk.stdout_correct)
        self.assertIsNone(fdbk.stdout_diff)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertFalse(fdbk.stdout_correct)
        self.assertEqual(self.ag_test_command.deduction_for_wrong_stdout,
                         fdbk.stdout_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points_possible)

    def test_stdout_correctness_show_diff_from_text(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stdout_fdbk_level=ag_models.ValueFeedbackLevel.expected_and_actual)

        correct_result = self.make_correct_result()
        fdbk = correct_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertTrue(fdbk.stdout_correct)
        diff = _get_expected_diff(self.ag_test_command.expected_stdout_text,
                                  correct_result.stdout_filename)
        self.assertEqual(diff.diff_content, fdbk.stdout_diff.diff_content)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertFalse(fdbk.stdout_correct)
        diff = _get_expected_diff(self.ag_test_command.expected_stdout_text,
                                  incorrect_result.stdout_filename)
        self.assertEqual(diff.diff_content, fdbk.stdout_diff.diff_content)
        self.assertEqual(self.ag_test_command.deduction_for_wrong_stdout,
                         fdbk.stdout_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points_possible)

    def test_stdout_correctness_show_diff_from_file(self):
        instructor_file = obj_build.make_instructor_file(self.project)
        self.ag_test_command.expected_stdout_source = (
            ag_models.ExpectedOutputSource.instructor_file)
        self.ag_test_command.expected_stdout_instructor_file = instructor_file
        self.ag_test_command.save()

        result = self.make_correct_result()
        with instructor_file.open() as f:
            expected_stdout = f.read()
        result.stdout = expected_stdout
        result.save()
        diff = _get_expected_diff(expected_stdout, result.stdout_filename)
        self.assertEqual(
            diff.diff_content,
            result.get_fdbk(ag_models.FeedbackCategory.normal).stdout_diff.diff_content)

        result.stdout = 'the wrong stdout'
        result.save()
        diff = _get_expected_diff(expected_stdout, result.stdout_filename)
        self.assertEqual(
            diff.diff_content,
            result.get_fdbk(ag_models.FeedbackCategory.normal).stdout_diff.diff_content)

    def test_stdout_show_actual(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stdout_fdbk_level=ag_models.ValueFeedbackLevel.no_feedback,
            show_actual_stdout=True)
        result = self.make_correct_result()
        fdbk = result.get_fdbk(ag_models.FeedbackCategory.normal)

        self.assertEqual(_stdout_text(result), _stdout_text(fdbk))
        self.assertIsNone(fdbk.stdout_correct)
        self.assertEqual(0, fdbk.stdout_points)
        self.assertEqual(0, fdbk.stdout_points_possible)

    def test_stdout_show_correctness_but_not_actual(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stdout_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            show_actual_stdout=False)
        result = self.make_correct_result()
        fdbk = result.get_fdbk(ag_models.FeedbackCategory.normal)

        self.assertIsNone(fdbk.stdout)
        self.assertTrue(fdbk.stdout_correct)
        self.assertIsNone(fdbk.stdout_diff)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points_possible)

    def test_stdout_show_expected_and_actual_overrides_show_actual(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stdout_fdbk_level=ag_models.ValueFeedbackLevel.expected_and_actual,
            show_actual_stdout=False)
        result = self.make_correct_result()
        fdbk = result.get_fdbk(ag_models.FeedbackCategory.normal)

        self.assertIsNotNone(fdbk.stdout_diff)
        self.assertIsNotNone(fdbk.stdout)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points)

    def test_stderr_correctness_hidden(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stderr_fdbk_level=ag_models.ValueFeedbackLevel.no_feedback)
        correct_result = self.make_correct_result()
        fdbk = correct_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.stderr_correct)
        self.assertIsNone(fdbk.stderr_diff)
        self.assertEqual(0, fdbk.stderr_points)
        self.assertEqual(0, fdbk.stderr_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.stderr_correct)
        self.assertIsNone(fdbk.stderr_diff)
        self.assertEqual(0, fdbk.stderr_points)
        self.assertEqual(0, fdbk.stderr_points_possible)

    def test_stderr_correctness_show_correct_or_incorrect(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stderr_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect)

        correct_result = self.make_correct_result()
        fdbk = correct_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertTrue(fdbk.stderr_correct)
        self.assertIsNone(fdbk.stderr_diff)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertFalse(fdbk.stderr_correct)
        self.assertEqual(self.ag_test_command.deduction_for_wrong_stderr,
                         fdbk.stderr_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points_possible)

    def test_stderr_correctness_show_expected_and_actual(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stderr_fdbk_level=ag_models.ValueFeedbackLevel.expected_and_actual)

        correct_result = self.make_correct_result()
        fdbk = correct_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertTrue(fdbk.stderr_correct)
        diff = _get_expected_diff(self.ag_test_command.expected_stderr_text,
                                  correct_result.stderr_filename)
        self.assertEqual(diff.diff_content, fdbk.stderr_diff.diff_content)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertFalse(fdbk.stderr_correct)
        diff = _get_expected_diff(self.ag_test_command.expected_stderr_text,
                                  incorrect_result.stderr_filename)
        self.assertEqual(diff.diff_content, fdbk.stderr_diff.diff_content)
        self.assertEqual(self.ag_test_command.deduction_for_wrong_stderr,
                         fdbk.stderr_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points_possible)

    def test_stderr_correctness_show_diff_from_file(self):
        instructor_file = obj_build.make_instructor_file(self.project)
        self.ag_test_command.expected_stderr_source = (
            ag_models.ExpectedOutputSource.instructor_file)
        self.ag_test_command.expected_stderr_instructor_file = instructor_file
        self.ag_test_command.save()

        result = self.make_correct_result()
        with instructor_file.open() as f:
            expected_stderr = f.read()
        result.stderr = expected_stderr
        result.save()
        diff = _get_expected_diff(expected_stderr, result.stderr_filename)
        self.assertEqual(
            diff.diff_content,
            result.get_fdbk(ag_models.FeedbackCategory.normal).stderr_diff.diff_content)

        result.stderr = 'the wrong stderr'
        result.save()
        diff = _get_expected_diff(expected_stderr, result.stderr_filename)
        self.assertEqual(
            diff.diff_content,
            result.get_fdbk(ag_models.FeedbackCategory.normal).stderr_diff.diff_content)

    def test_stderr_show_actual(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stderr_fdbk_level=ag_models.ValueFeedbackLevel.no_feedback,
            show_actual_stderr=True)
        result = self.make_correct_result()
        fdbk = result.get_fdbk(ag_models.FeedbackCategory.normal)

        self.assertEqual(_stderr_text(result), _stderr_text(fdbk))
        self.assertIsNone(fdbk.stderr_correct)
        self.assertEqual(0, fdbk.stderr_points)
        self.assertEqual(0, fdbk.stderr_points_possible)

    def test_stderr_show_correctness_but_not_actual(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stderr_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            show_actual_stderr=False)
        result = self.make_correct_result()
        fdbk = result.get_fdbk(ag_models.FeedbackCategory.normal)

        self.assertIsNone(fdbk.stderr)
        self.assertTrue(fdbk.stderr_correct)
        self.assertIsNone(fdbk.stderr_diff)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points_possible)

    def test_stderr_show_expected_and_actual_overrides_show_actual(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stderr_fdbk_level=ag_models.ValueFeedbackLevel.expected_and_actual,
            show_actual_stderr=False)
        result = self.make_correct_result()
        fdbk = result.get_fdbk(ag_models.FeedbackCategory.normal)

        self.assertIsNotNone(fdbk.stderr_diff)
        self.assertIsNotNone(fdbk.stderr)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points)

    def test_points_visibility(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(show_points=False)

        correct_result = self.make_correct_result()
        fdbk = correct_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertEqual(0, fdbk.total_points)
        self.assertEqual(0, fdbk.total_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertEqual(0, fdbk.total_points)
        self.assertEqual(0, fdbk.total_points_possible)

    def test_all_diff_options_false_stdout_correct_stderr_incorrect(self):
        self.do_diff_options_test(
            expected_stdout='spam', actual_stdout='spam',
            expected_stderr='yes', actual_stderr='no',
            expect_stdout_correct=True,
            expect_stderr_correct=False,
            **self._get_diff_options(False))

    def test_all_diff_options_false_stderr_correct_stdout_incorrect(self):
        self.do_diff_options_test(
            expected_stdout='yes', actual_stdout='no',
            expected_stderr='egg', actual_stderr='egg',
            expect_stdout_correct=False,
            expect_stderr_correct=True,
            **self._get_diff_options(False))

    def test_all_diff_options_true_stdout_correct_stderr_incorrect(self):
        self.do_diff_options_test(
            expected_stdout='SPAM', actual_stdout='spam',
            expected_stderr='yes', actual_stderr='no',
            expect_stdout_correct=True,
            expect_stderr_correct=False,
            **self._get_diff_options(True))

    def test_all_diff_options_true_stderr_correct_stdout_incorrect(self):
        self.do_diff_options_test(
            expected_stdout='yes', actual_stdout='no',
            expected_stderr='egg', actual_stderr='EGG',
            expect_stdout_correct=False,
            expect_stderr_correct=True,
            **self._get_diff_options(True))

    def do_diff_options_test(self, expected_stdout='', actual_stdout='',
                             expected_stderr='', actual_stderr='',
                             expect_stdout_correct=True,
                             expect_stderr_correct=True,
                             **diff_options):
        self.ag_test_command.validate_and_update(
            expected_stdout_text=expected_stdout,
            expected_stderr_text=expected_stderr,
            **diff_options)

        result = self.make_correct_result()
        with open(result.stdout_filename, 'w') as f:
            f.write(actual_stdout)
            actual_stdout_filename = f.name
        with open(result.stderr_filename, 'w') as f:
            f.write(actual_stderr)
            actual_stderr_filename = f.name

        mock_path = 'autograder.core.utils.get_diff'
        with mock.patch(mock_path) as mock_differ_cls:
            diff = result.get_fdbk(ag_models.FeedbackCategory.max).stdout_diff
            mock_differ_cls.assert_called_with(mock.ANY, actual_stdout_filename,
                                               **diff_options)

        with mock.patch(mock_path) as mock_differ_cls:
            diff = result.get_fdbk(ag_models.FeedbackCategory.max).stderr_diff
            mock_differ_cls.assert_called_with(mock.ANY, actual_stderr_filename,
                                               **diff_options)

        if expect_stdout_correct:
            diff = result.get_fdbk(ag_models.FeedbackCategory.max).stdout_diff
            self.assertTrue(diff.diff_pass, msg=diff.diff_content)
        else:
            self.assertFalse(result.get_fdbk(ag_models.FeedbackCategory.max).stdout_diff.diff_pass)

        if expect_stderr_correct:
            self.assertTrue(result.get_fdbk(ag_models.FeedbackCategory.max).stderr_diff.diff_pass)
        else:
            self.assertFalse(result.get_fdbk(ag_models.FeedbackCategory.max).stderr_diff.diff_pass)

    def _get_diff_options(self, options_value):
        return {
            'ignore_case': options_value,
            'ignore_whitespace': options_value,
            'ignore_whitespace_changes': options_value,
            'ignore_blank_lines': options_value
        }

    def test_fdbk_to_dict(self):
        result = obj_build.make_correct_ag_test_command_result(
            ag_test_command=self.ag_test_command,
            ag_test_case_result=self.ag_test_case_result)

        expected_keys = [
            'pk',
            'ag_test_command_name',
            'ag_test_command_pk',
            'fdbk_settings',

            'timed_out',

            'return_code_correct',
            'expected_return_code',
            'actual_return_code',
            'return_code_points',
            'return_code_points_possible',

            'stdout_correct',
            'stdout_points',
            'stdout_points_possible',

            'stderr_correct',
            'stderr_points',
            'stderr_points_possible',

            'total_points',
            'total_points_possible',
        ]

        self.assertCountEqual(expected_keys,
                              result.get_fdbk(ag_models.FeedbackCategory.max).to_dict().keys())


def _stdout_text(result_or_fdbk: Union[ag_models.AGTestCommandResult,
                                       ag_models.AGTestCommandResult.FeedbackCalculator]) -> str:
    if isinstance(result_or_fdbk, ag_models.AGTestCommandResult):
        with open(result_or_fdbk.stdout_filename) as f:
            return f.read()
    elif isinstance(result_or_fdbk, ag_models.AGTestCommandResult.FeedbackCalculator):
        return result_or_fdbk.stdout.read().decode()


def _stderr_text(result_or_fdbk: Union[ag_models.AGTestCommandResult,
                                       ag_models.AGTestCommandResult.FeedbackCalculator]) -> str:
    if isinstance(result_or_fdbk, ag_models.AGTestCommandResult):
        with open(result_or_fdbk.stdout_filename) as f:
            return f.read()
    elif isinstance(result_or_fdbk, ag_models.AGTestCommandResult.FeedbackCalculator):
        return result_or_fdbk.stdout.read().decode()


def _write_stdout(result, stdout):
    with open(result.stdout_filename, 'w') as f:
        f.write(stdout)


def _write_stderr(result, stderr):
    with open(result.stderr_filename, 'w') as f:
        f.write(stderr)


def _get_expected_diff(expected_text: str, actual_output_filename: str):
    with tempfile.NamedTemporaryFile('w') as f:
        f.write(expected_text)
        f.flush()
        return core_ut.get_diff(f.name, actual_output_filename)
