import os
from unittest import mock

import autograder.core.models as ag_models
import autograder.core.constants as constants
import autograder.core.utils as core_ut

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class AGTestCommandResultTestCase(UnitTestBase):
    def setUp(self):
        # create an ag_test_command where normal feedback is set to max
        submission = obj_build.build_submission()
        self.project = submission.submission_group.project
        suite = ag_models.AGTestSuite.objects.validate_and_create(
            name='kajsdhf', project=self.project)
        self.ag_test_case = ag_models.AGTestCase.objects.validate_and_create(
            name='aksdbva', ag_test_suite=suite)
        suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            submission=submission, ag_test_suite=suite)
        self.ag_test_case_result = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=self.ag_test_case, ag_test_suite_result=suite_result)

        # Normal feedback is set to max
        self.ag_test_command = ag_models.AGTestCommand.objects.validate_and_create(
            name='madsnbvihq',
            ag_test_case=self.ag_test_case,
            cmd='aksdjhfalsdf',

            # These specific values don't matter, other than that
            # they should indicate that return code, stdout, and
            # stderr are checked. We'll be manually setting the
            # correctness fields on AGTestCommandResults.
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stdout_text='some text that is here because',
            expected_stderr_source=ag_models.ExpectedOutputSource.text,
            expected_stderr_text='some error stuff that wat',

            points_for_correct_return_code=1,
            points_for_correct_stdout=2,
            points_for_correct_stderr=3,
            deduction_for_wrong_return_code=-4,
            deduction_for_wrong_stdout=-2,
            deduction_for_wrong_stderr=-1,

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
        )  # type: ag_models.AGTestCommand
        self.max_points_possible = 6
        self.min_points_possible = -7

    def make_correct_result(self) -> ag_models.AGTestCommandResult:
        return ag_models.AGTestCommandResult.objects.validate_and_create(
            ag_test_command=self.ag_test_command,
            ag_test_case_result=self.ag_test_case_result,
            return_code=0,
            stdout=self.ag_test_command.expected_stdout_text,
            stderr=self.ag_test_command.expected_stderr_text,

            return_code_correct=True,
            stdout_correct=True,
            stderr_correct=True,
            timed_out=False
        )

    def make_incorrect_result(self) -> ag_models.AGTestCommandResult:
        return ag_models.AGTestCommandResult.objects.validate_and_create(
            ag_test_command=self.ag_test_command,
            ag_test_case_result=self.ag_test_case_result,
            return_code=42,
            stdout=self.ag_test_command.expected_stdout_text + 'abdashlfkahsdvnalkjc',
            stderr=self.ag_test_command.expected_stderr_text + 'amnbvalisuhlaksdhf',

            return_code_correct=False,
            stdout_correct=False,
            stderr_correct=False,
            timed_out=True
        )

    def test_feedback_calculator_named_ctors(self):
        # check against the actual objects (their pks)
        result = self.make_correct_result()
        self.assertEqual(self.ag_test_command.normal_fdbk_config,
                         result.get_normal_feedback().fdbk_conf)
        self.assertEqual(self.ag_test_command.ultimate_submission_fdbk_config,
                         result.get_ultimate_submission_feedback().fdbk_conf)
        self.assertEqual(self.ag_test_command.past_limit_submission_fdbk_config,
                         result.get_past_submission_limit_feedback().fdbk_conf)
        self.assertEqual(self.ag_test_command.staff_viewer_fdbk_config,
                         result.get_staff_viewer_feedback().fdbk_conf)

    def test_points_everything_correct_max_fdbk(self):
        cmd_result = self.make_correct_result()
        fdbk = cmd_result.get_max_feedback()

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
        fdbk = cmd_result.get_max_feedback()

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
        fdbk = correct_cmd_result.get_max_feedback()
        self.assertEqual(ag_models.ExpectedReturnCode.none, fdbk.expected_return_code)
        self.assertIsNone(fdbk.return_code_correct)
        self.assertEqual(0, fdbk.return_code_points)
        self.assertEqual(0, fdbk.return_code_points_possible)

        expected_total_pts = (self.ag_test_command.points_for_correct_stdout +
                              self.ag_test_command.points_for_correct_stderr)
        self.assertEqual(expected_total_pts, fdbk.total_points)
        expected_total_pts_possible = expected_total_pts
        self.assertEqual(expected_total_pts_possible, fdbk.total_points_possible)

        correct_cmd_result.delete()

        incorrect_cmd_result = self.make_incorrect_result()
        fdbk = incorrect_cmd_result.get_max_feedback()
        self.assertIsNone(fdbk.return_code_correct)
        self.assertEqual(0, fdbk.return_code_points)
        self.assertEqual(0, fdbk.return_code_points_possible)

        expected_total_pts = (self.ag_test_command.deduction_for_wrong_stdout +
                              self.ag_test_command.deduction_for_wrong_stderr)
        self.assertEqual(expected_total_pts, fdbk.total_points)
        self.assertEqual(expected_total_pts_possible, fdbk.total_points_possible)

    def test_stdout_not_checked(self):
        self.ag_test_command.validate_and_update(
            expected_stdout_source=ag_models.ExpectedOutputSource.none)

        correct_cmd_result = self.make_correct_result()
        fdbk = correct_cmd_result.get_max_feedback()
        self.assertIsNone(fdbk.stdout_correct)
        self.assertIsNone(fdbk.stdout_diff)
        self.assertEqual(correct_cmd_result.stdout, fdbk.stdout)
        self.assertEqual(0, fdbk.stdout_points)
        self.assertEqual(0, fdbk.stdout_points_possible)

        expected_total_pts = (self.ag_test_command.points_for_correct_return_code +
                              self.ag_test_command.points_for_correct_stderr)
        expected_total_pts_possible = expected_total_pts
        self.assertEqual(expected_total_pts, fdbk.total_points)
        self.assertEqual(expected_total_pts_possible, fdbk.total_points_possible)

        correct_cmd_result.delete()

        incorrect_cmd_result = self.make_incorrect_result()
        fdbk = incorrect_cmd_result.get_max_feedback()
        self.assertIsNone(fdbk.stdout_correct)
        self.assertEqual(0, fdbk.stdout_points)
        self.assertEqual(0, fdbk.stdout_points_possible)

        expected_total_pts = (self.ag_test_command.deduction_for_wrong_return_code +
                              self.ag_test_command.deduction_for_wrong_stderr)
        self.assertEqual(expected_total_pts, fdbk.total_points)
        self.assertEqual(expected_total_pts_possible, fdbk.total_points_possible)

    def test_stderr_not_checked(self):
        self.ag_test_command.validate_and_update(
            expected_stderr_source=ag_models.ExpectedOutputSource.none)

        correct_cmd_result = self.make_correct_result()
        fdbk = correct_cmd_result.get_max_feedback()
        self.assertIsNone(fdbk.stderr_correct)
        self.assertIsNone(fdbk.stderr_diff)
        self.assertEqual(correct_cmd_result.stderr, fdbk.stderr)
        self.assertEqual(0, fdbk.stderr_points)
        self.assertEqual(0, fdbk.stderr_points_possible)

        expected_total_pts = (self.ag_test_command.points_for_correct_return_code +
                              self.ag_test_command.points_for_correct_stdout)
        expected_total_pts_possible = expected_total_pts
        self.assertEqual(expected_total_pts, fdbk.total_points)
        self.assertEqual(expected_total_pts_possible, fdbk.total_points_possible)

        correct_cmd_result.delete()

        incorrect_cmd_result = self.make_incorrect_result()
        fdbk = incorrect_cmd_result.get_max_feedback()
        self.assertIsNone(fdbk.stderr_correct)
        self.assertEqual(0, fdbk.stderr_points)
        self.assertEqual(0, fdbk.stderr_points_possible)

        expected_total_pts = (self.ag_test_command.deduction_for_wrong_return_code +
                              self.ag_test_command.deduction_for_wrong_stdout)
        self.assertEqual(expected_total_pts, fdbk.total_points)
        self.assertEqual(expected_total_pts_possible, fdbk.total_points_possible)

    def test_return_code_correctness_hidden(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            return_code_fdbk_level=ag_models.ValueFeedbackLevel.no_feedback)

        correct_result = self.make_correct_result()
        fdbk = correct_result.get_normal_feedback()
        self.assertIsNone(fdbk.return_code_correct)
        self.assertEqual(0, fdbk.return_code_points)
        self.assertEqual(0, fdbk.return_code_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_normal_feedback()
        self.assertIsNone(fdbk.return_code_correct)
        self.assertEqual(0, fdbk.return_code_points)
        self.assertEqual(0, fdbk.return_code_points_possible)

    def test_return_code_correctness_show_correct_or_incorrect(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            return_code_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect)

        correct_result = self.make_correct_result()
        fdbk = correct_result.get_normal_feedback()
        self.assertTrue(fdbk.return_code_correct)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_normal_feedback()
        self.assertFalse(fdbk.return_code_correct)
        self.assertEqual(self.ag_test_command.deduction_for_wrong_return_code,
                         fdbk.return_code_points)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points_possible)

    def test_return_code_correctness_show_expected_and_actual(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            return_code_fdbk_level=ag_models.ValueFeedbackLevel.expected_and_actual)

        correct_result = self.make_correct_result()
        fdbk = correct_result.get_normal_feedback()
        self.assertTrue(fdbk.return_code_correct)
        self.assertEqual(self.ag_test_command.expected_return_code, fdbk.expected_return_code)
        self.assertEqual(correct_result.return_code, fdbk.actual_return_code)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_normal_feedback()
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
        fdbk = result.get_normal_feedback()

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
        fdbk = result.get_normal_feedback()

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
        fdbk = result.get_normal_feedback()

        self.assertIsNotNone(fdbk.actual_return_code)
        self.assertIsNotNone(fdbk.expected_return_code)
        self.assertTrue(fdbk.return_code_correct)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points)

    def test_show_timed_out(self):
        result = self.make_correct_result()
        self.assertFalse(result.get_normal_feedback().timed_out)

        result.delete()

        result = self.make_incorrect_result()
        self.assertTrue(result.get_normal_feedback().timed_out)

    def test_hide_timed_out(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            show_whether_timed_out=False)

        result = self.make_correct_result()
        self.assertIsNone(result.get_normal_feedback().timed_out)

        result.delete()

        result = self.make_incorrect_result()
        self.assertIsNone(result.get_normal_feedback().timed_out)

    def test_stdout_correctness_hidden(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stdout_fdbk_level=ag_models.ValueFeedbackLevel.no_feedback)
        correct_result = self.make_correct_result()
        fdbk = correct_result.get_normal_feedback()
        self.assertIsNone(fdbk.stdout_correct)
        self.assertIsNone(fdbk.stdout_diff)
        self.assertEqual(0, fdbk.stdout_points)
        self.assertEqual(0, fdbk.stdout_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_normal_feedback()
        self.assertIsNone(fdbk.stdout_correct)
        self.assertIsNone(fdbk.stdout_diff)
        self.assertEqual(0, fdbk.stdout_points)
        self.assertEqual(0, fdbk.stdout_points_possible)

    def test_stdout_correctness_show_correct_or_incorrect(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stdout_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect)

        correct_result = self.make_correct_result()
        fdbk = correct_result.get_normal_feedback()
        self.assertTrue(fdbk.stdout_correct)
        self.assertIsNone(fdbk.stdout_diff)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_normal_feedback()
        self.assertFalse(fdbk.stdout_correct)
        self.assertEqual(self.ag_test_command.deduction_for_wrong_stdout,
                         fdbk.stdout_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points_possible)

    def test_stdout_correctness_show_diff_from_text(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stdout_fdbk_level=ag_models.ValueFeedbackLevel.expected_and_actual)

        correct_result = self.make_correct_result()
        fdbk = correct_result.get_normal_feedback()
        self.assertTrue(fdbk.stdout_correct)
        diff = core_ut.get_diff(self.ag_test_command.expected_stdout_text, correct_result.stdout)
        self.assertEqual(diff, fdbk.stdout_diff)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_normal_feedback()
        self.assertFalse(fdbk.stdout_correct)
        diff = core_ut.get_diff(self.ag_test_command.expected_stdout_text, incorrect_result.stdout)
        self.assertEqual(diff, fdbk.stdout_diff)
        self.assertEqual(self.ag_test_command.deduction_for_wrong_stdout,
                         fdbk.stdout_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points_possible)

    def test_stdout_correctness_show_diff_from_file(self):
        proj_file = obj_build.make_uploaded_file(self.project)
        self.ag_test_command.expected_stdout_source = ag_models.ExpectedOutputSource.project_file
        self.ag_test_command.expected_stdout_project_file = proj_file
        self.ag_test_command.save()

        result = self.make_correct_result()
        with proj_file.open() as f:
            expected_stdout = f.read()
        result.stdout = expected_stdout
        result.save()
        diff = core_ut.get_diff(expected_stdout, result.stdout)
        self.assertEqual(diff, result.get_normal_feedback().stdout_diff)

        result.stdout = 'the wrong stdout'
        result.save()
        diff = core_ut.get_diff(expected_stdout, result.stdout)
        self.assertEqual(diff, result.get_normal_feedback().stdout_diff)

    def test_stdout_show_actual(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stdout_fdbk_level=ag_models.ValueFeedbackLevel.no_feedback,
            show_actual_stdout=True)
        result = self.make_correct_result()
        fdbk = result.get_normal_feedback()

        self.assertEqual(result.stdout, fdbk.stdout)
        self.assertIsNone(fdbk.stdout_correct)
        self.assertEqual(0, fdbk.stdout_points)
        self.assertEqual(0, fdbk.stdout_points_possible)

    def test_stdout_show_correctness_but_not_actual(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stdout_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            show_actual_stdout=False)
        result = self.make_correct_result()
        fdbk = result.get_normal_feedback()

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
        fdbk = result.get_normal_feedback()

        self.assertIsNotNone(fdbk.stdout_diff)
        self.assertIsNotNone(fdbk.stdout)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points)

    def test_stderr_correctness_hidden(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stderr_fdbk_level=ag_models.ValueFeedbackLevel.no_feedback)
        correct_result = self.make_correct_result()
        fdbk = correct_result.get_normal_feedback()
        self.assertIsNone(fdbk.stderr_correct)
        self.assertIsNone(fdbk.stderr_diff)
        self.assertEqual(0, fdbk.stderr_points)
        self.assertEqual(0, fdbk.stderr_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_normal_feedback()
        self.assertIsNone(fdbk.stderr_correct)
        self.assertIsNone(fdbk.stderr_diff)
        self.assertEqual(0, fdbk.stderr_points)
        self.assertEqual(0, fdbk.stderr_points_possible)

    def test_stderr_correctness_show_correct_or_incorrect(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stderr_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect)

        correct_result = self.make_correct_result()
        fdbk = correct_result.get_normal_feedback()
        self.assertTrue(fdbk.stderr_correct)
        self.assertIsNone(fdbk.stderr_diff)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_normal_feedback()
        self.assertFalse(fdbk.stderr_correct)
        self.assertEqual(self.ag_test_command.deduction_for_wrong_stderr,
                         fdbk.stderr_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points_possible)

    def test_stderr_correctness_show_expected_and_actual(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stderr_fdbk_level=ag_models.ValueFeedbackLevel.expected_and_actual)

        correct_result = self.make_correct_result()
        fdbk = correct_result.get_normal_feedback()
        self.assertTrue(fdbk.stderr_correct)
        diff = core_ut.get_diff(self.ag_test_command.expected_stderr_text, correct_result.stderr)
        self.assertEqual(diff, fdbk.stderr_diff)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_normal_feedback()
        self.assertFalse(fdbk.stderr_correct)
        diff = core_ut.get_diff(self.ag_test_command.expected_stderr_text, incorrect_result.stderr)
        self.assertEqual(diff, fdbk.stderr_diff)
        self.assertEqual(self.ag_test_command.deduction_for_wrong_stderr,
                         fdbk.stderr_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points_possible)

    def test_stderr_correctness_show_diff_from_file(self):
        proj_file = obj_build.make_uploaded_file(self.project)
        self.ag_test_command.expected_stderr_source = ag_models.ExpectedOutputSource.project_file
        self.ag_test_command.expected_stderr_project_file = proj_file
        self.ag_test_command.save()

        result = self.make_correct_result()
        with proj_file.open() as f:
            expected_stderr = f.read()
        result.stderr = expected_stderr
        result.save()
        diff = core_ut.get_diff(expected_stderr, result.stderr)
        self.assertEqual(diff, result.get_normal_feedback().stderr_diff)

        result.stderr = 'the wrong stderr'
        result.save()
        diff = core_ut.get_diff(expected_stderr, result.stderr)
        self.assertEqual(diff, result.get_normal_feedback().stderr_diff)

    def test_stderr_show_actual(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stderr_fdbk_level=ag_models.ValueFeedbackLevel.no_feedback,
            show_actual_stderr=True)
        result = self.make_correct_result()
        fdbk = result.get_normal_feedback()

        self.assertEqual(result.stderr, fdbk.stderr)
        self.assertIsNone(fdbk.stderr_correct)
        self.assertEqual(0, fdbk.stderr_points)
        self.assertEqual(0, fdbk.stderr_points_possible)

    def test_stderr_show_correctness_but_not_actual(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(
            stderr_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            show_actual_stderr=False)
        result = self.make_correct_result()
        fdbk = result.get_normal_feedback()

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
        fdbk = result.get_normal_feedback()

        self.assertIsNotNone(fdbk.stderr_diff)
        self.assertIsNotNone(fdbk.stderr)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points)

    def test_points_visibility(self):
        self.ag_test_command.normal_fdbk_config.validate_and_update(show_points=False)

        correct_result = self.make_correct_result()
        fdbk = correct_result.get_normal_feedback()
        self.assertEqual(0, fdbk.total_points)
        self.assertEqual(0, fdbk.total_points_possible)

        correct_result.delete()

        incorrect_result = self.make_incorrect_result()
        fdbk = incorrect_result.get_normal_feedback()
        self.assertEqual(0, fdbk.total_points)
        self.assertEqual(0, fdbk.total_points_possible)

    def test_very_large_output_truncated(self):
        stdout = 'a' * 3000000000
        stderr = 'b' * 3000000000

        cmd_result = ag_models.AGTestCommandResult.objects.validate_and_create(
            ag_test_command=self.ag_test_command,
            ag_test_case_result=self.ag_test_case_result,
            return_code=0,
            stdout=stdout,
            stderr=stderr
        )

        self.assertEqual(
            cmd_result.stdout,
            stdout[:constants.MAX_OUTPUT_LENGTH] + '\nOutput truncated')
        self.assertEqual(
            cmd_result.stderr,
            stderr[:constants.MAX_OUTPUT_LENGTH] + '\nOutput truncated')

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
        result.stdout = actual_stdout
        result.stderr = actual_stderr
        result.save()

        mock_path = 'autograder.core.utils.get_diff'
        with mock.patch(mock_path) as mock_differ_cls:
            result.get_max_feedback().stdout_diff
            mock_differ_cls.assert_called_with(expected_stdout, actual_stdout,
                                               **diff_options)

        with mock.patch(mock_path) as mock_differ_cls:
            result.get_max_feedback().stderr_diff
            mock_differ_cls.assert_called_with(expected_stderr, actual_stderr,
                                               **diff_options)

        if expect_stdout_correct:
            self.assertEqual([], result.get_max_feedback().stdout_diff)
        else:
            self.assertNotEqual([], result.get_max_feedback().stdout_diff)

        if expect_stderr_correct:
            self.assertEqual([], result.get_max_feedback().stderr_diff)
        else:
            self.assertNotEqual([], result.get_max_feedback().stderr_diff)

    def _get_diff_options(self, options_value):
        return {
            'ignore_case': options_value,
            'ignore_whitespace': options_value,
            'ignore_whitespace_changes': options_value,
            'ignore_blank_lines': options_value
        }
