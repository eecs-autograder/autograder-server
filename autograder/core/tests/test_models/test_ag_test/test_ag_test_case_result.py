import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class AGTestCaseResultTestCase(UnitTestBase):
    def setUp(self):
        submission = obj_build.build_submission()
        project = submission.submission_group.project
        suite = ag_models.AGTestSuite.objects.validate_and_create(
            name='kajsdhf', project=project)
        self.ag_test_case = ag_models.AGTestCase.objects.validate_and_create(
            name='aksdbva', ag_test_suite=suite
        )  # type: ag_models.AGTestCase
        suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            submission=submission, ag_test_suite=suite)
        self.ag_test_case_result = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=self.ag_test_case, ag_test_suite_result=suite_result
        )  # type: ag_models.AGTestCaseResult

        self.ag_test_cmd1 = obj_build.make_full_ag_test_command_with_max_normal_fdbk(
            self.ag_test_case, set_arbitrary_points=False)
        self.ag_test_cmd2 = obj_build.make_full_ag_test_command_with_max_normal_fdbk(
            self.ag_test_case, set_arbitrary_points=False)

    def test_feedback_calculator_named_ctors(self):
        self.assertEqual(
            self.ag_test_case.normal_fdbk_config,
            self.ag_test_case_result.get_fdbk(ag_models.FeedbackCategory.normal).fdbk_conf)
        self.assertEqual(
            self.ag_test_case.ultimate_submission_fdbk_config,
            self.ag_test_case_result.get_fdbk(
                ag_models.FeedbackCategory.ultimate_submission).fdbk_conf)
        self.assertEqual(
            self.ag_test_case.past_limit_submission_fdbk_config,
            self.ag_test_case_result.get_fdbk(
                ag_models.FeedbackCategory.past_limit_submission).fdbk_conf)
        self.assertEqual(
            self.ag_test_case.staff_viewer_fdbk_config,
            self.ag_test_case_result.get_fdbk(ag_models.FeedbackCategory.staff_viewer).fdbk_conf)

        max_config = self.ag_test_case_result.get_fdbk(ag_models.FeedbackCategory.max).fdbk_conf
        self.assertTrue(max_config.show_individual_commands)

    def test_total_points_all_positive(self):
        # make sure sum is correct and takes into account deductions
        # make sure sum doesn't go below zero
        self.ag_test_cmd1.validate_and_update(points_for_correct_return_code=5)
        self.ag_test_cmd2.validate_and_update(points_for_correct_stdout=3)

        obj_build.make_correct_ag_test_command_result(self.ag_test_cmd1)
        obj_build.make_correct_ag_test_command_result(self.ag_test_cmd2)

        self.assertEqual(8, self.ag_test_case_result.get_fdbk().total_points)
        self.assertEqual(8, self.ag_test_case_result.get_fdbk().total_points_possible)

    def test_total_points_some_positive_some_negative_positive_total(self):
        self.ag_test_cmd1.validate_and_update(points_for_correct_return_code=5)
        self.ag_test_cmd2.validate_and_update(deduction_for_wrong_stdout=-2)

        obj_build.make_correct_ag_test_command_result(self.ag_test_cmd1)
        obj_build.make_incorrect_ag_test_command_result(self.ag_test_cmd2)

        self.assertEqual(3, self.ag_test_case_result.get_fdbk().total_points)
        self.assertEqual(5, self.ag_test_case_result.get_fdbk().total_points_possible)

    def test_total_points_not_below_zero(self):
        self.ag_test_cmd1.validate_and_update(points_for_correct_return_code=5)
        self.ag_test_cmd2.validate_and_update(deduction_for_wrong_stdout=-10)

        obj_build.make_correct_ag_test_command_result(self.ag_test_cmd1)
        obj_build.make_correct_ag_test_command_result(self.ag_test_cmd2)

        self.assertEqual(5, self.ag_test_case_result.get_fdbk().total_points)
        self.assertEqual(0, self.ag_test_case_result.get_fdbk().total_points_possible)

    def test_show_individual_commands(self):
        result1 = obj_build.make_correct_ag_test_command_result(self.ag_test_cmd1)
        result2 = obj_build.make_correct_ag_test_command_result(self.ag_test_cmd2)

        self.assertSequenceEqual(
            [result1, result2],
            self.ag_test_case_result.get_fdbk().ag_test_command_results)

        self.ag_test_case.normal_fdbk_config.validate_and_update(show_individual_commands=False)
        self.assertSequenceEqual(
            [], self.ag_test_case_result.get_fdbk().ag_test_command_results)
