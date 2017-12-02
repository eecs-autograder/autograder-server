import autograder.core.models as ag_models
from autograder.core.models.submission import get_ag_test_case_results_queryset
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

        self.ag_test_cmd1 = obj_build.make_full_ag_test_command(
            self.ag_test_case, set_arbitrary_points=False)
        self.ag_test_cmd2 = obj_build.make_full_ag_test_command(
            self.ag_test_case, set_arbitrary_points=False)

    def test_feedback_calculator_ctor(self):
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

        obj_build.make_correct_ag_test_command_result(self.ag_test_cmd1, self.ag_test_case_result)
        obj_build.make_correct_ag_test_command_result(self.ag_test_cmd2, self.ag_test_case_result)

        self.assertEqual(
            8, self.ag_test_case_result.get_fdbk(ag_models.FeedbackCategory.max).total_points)
        self.assertEqual(
            8,
            self.ag_test_case_result.get_fdbk(
                ag_models.FeedbackCategory.max).total_points_possible)

    def test_total_points_some_positive_some_negative_positive_total(self):
        self.ag_test_cmd1.validate_and_update(points_for_correct_return_code=5)
        self.ag_test_cmd2.validate_and_update(deduction_for_wrong_stdout=-2)

        obj_build.make_correct_ag_test_command_result(self.ag_test_cmd1, self.ag_test_case_result)
        obj_build.make_incorrect_ag_test_command_result(
            self.ag_test_cmd2, self.ag_test_case_result)

        self.assertEqual(
            3,
            self.ag_test_case_result.get_fdbk(ag_models.FeedbackCategory.max).total_points)
        self.assertEqual(
            5,
            self.ag_test_case_result.get_fdbk(
                ag_models.FeedbackCategory.max).total_points_possible)

    def test_total_points_not_below_zero(self):
        self.ag_test_cmd1.validate_and_update(points_for_correct_return_code=5)
        self.ag_test_cmd2.validate_and_update(deduction_for_wrong_stdout=-10)

        obj_build.make_correct_ag_test_command_result(self.ag_test_cmd1, self.ag_test_case_result)
        obj_build.make_correct_ag_test_command_result(self.ag_test_cmd2, self.ag_test_case_result)

        self.assertEqual(
            5,
            self.ag_test_case_result.get_fdbk(ag_models.FeedbackCategory.max).total_points)
        self.assertEqual(
            5,
            self.ag_test_case_result.get_fdbk(
                ag_models.FeedbackCategory.max).total_points_possible)

    def test_total_points_minimum_ag_test_command_fdbk(self):
        self.ag_test_cmd1.validate_and_update(
            points_for_correct_return_code=1,
            points_for_correct_stdout=2,
            points_for_correct_stderr=3)
        self.ag_test_cmd2.validate_and_update(
            deduction_for_wrong_return_code=-4,
            deduction_for_wrong_stdout=-2,
            deduction_for_wrong_stderr=-1)

        obj_build.make_correct_ag_test_command_result(self.ag_test_cmd1, self.ag_test_case_result)
        obj_build.make_correct_ag_test_command_result(self.ag_test_cmd2, self.ag_test_case_result)

        self.assertEqual(
            0, self.ag_test_case_result.get_fdbk(ag_models.FeedbackCategory.normal).total_points)
        self.assertEqual(
            0,
            self.ag_test_case_result.get_fdbk(
                ag_models.FeedbackCategory.normal).total_points_possible)

    def test_show_individual_commands(self):
        total_cmd_points = 6
        self.ag_test_cmd1.validate_and_update(points_for_correct_return_code=total_cmd_points)
        self.ag_test_cmd1.normal_fdbk_config.validate_and_update(
            return_code_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            show_points=True)

        self.assertTrue(self.ag_test_case.normal_fdbk_config.show_individual_commands)
        result1 = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd1, self.ag_test_case_result)
        result2 = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd2, self.ag_test_case_result)

        fdbk = self.ag_test_case_result.get_fdbk(ag_models.FeedbackCategory.max)

        self.assertEqual([result1, result2], fdbk.ag_test_command_results)
        self.assertEqual(total_cmd_points, fdbk.total_points)
        self.assertEqual(total_cmd_points, fdbk.total_points_possible)

        self.ag_test_case.normal_fdbk_config.validate_and_update(show_individual_commands=False)
        fdbk = self.ag_test_case_result.get_fdbk(ag_models.FeedbackCategory.normal)

        self.assertEqual([], fdbk.ag_test_command_results)
        self.assertEqual(total_cmd_points, fdbk.total_points)
        self.assertEqual(total_cmd_points, fdbk.total_points_possible)

    def test_individual_cmd_result_order(self):
        result1 = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd1, self.ag_test_case_result)
        result2 = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd2, self.ag_test_case_result)

        self.ag_test_case.set_agtestcommand_order([self.ag_test_cmd2.pk, self.ag_test_cmd1.pk])
        self.ag_test_case_result = get_ag_test_case_results_queryset(
            ag_models.FeedbackCategory.max).get(pk=self.ag_test_case_result.pk)
        fdbk = self.ag_test_case_result.get_fdbk(ag_models.FeedbackCategory.max)
        self.assertEqual([result2, result1], fdbk.ag_test_command_results)

    def test_some_commands_not_visible(self):
        self.ag_test_cmd1.ultimate_submission_fdbk_config.validate_and_update(visible=False)
        cmd1_pts = 5
        cmd2_pts = 3
        self.ag_test_cmd1.validate_and_update(points_for_correct_return_code=cmd1_pts)
        self.ag_test_cmd2.validate_and_update(points_for_correct_return_code=cmd2_pts)

        cmd_result1 = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd1, self.ag_test_case_result)
        cmd_result2 = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd2, self.ag_test_case_result)

        self.assertEqual(
            cmd1_pts + cmd2_pts,
            self.ag_test_case_result.get_fdbk(ag_models.FeedbackCategory.max).total_points)
        self.assertEqual(
            cmd1_pts + cmd2_pts,
            self.ag_test_case_result.get_fdbk(
                ag_models.FeedbackCategory.max).total_points_possible)

        fdbk = self.ag_test_case_result.get_fdbk(ag_models.FeedbackCategory.ultimate_submission)
        self.assertSequenceEqual([cmd_result2], fdbk.ag_test_command_results)
        self.assertEqual(
            cmd2_pts,
            self.ag_test_case_result.get_fdbk(
                ag_models.FeedbackCategory.ultimate_submission).total_points)
        self.assertEqual(
            cmd2_pts,
            self.ag_test_case_result.get_fdbk(
                ag_models.FeedbackCategory.ultimate_submission).total_points_possible)

    def test_fdbk_to_dict(self):
        self.ag_test_cmd1.validate_and_update(
            points_for_correct_return_code=2,
            points_for_correct_stdout=3,
            points_for_correct_stderr=8
        )

        self.ag_test_cmd2.validate_and_update(
            points_for_correct_return_code=4,
            points_for_correct_stdout=5,
            points_for_correct_stderr=7
        )

        result1 = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd1, self.ag_test_case_result)
        result2 = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd2, self.ag_test_case_result)

        expected_keys = [
            'pk',
            'ag_test_case_name',
            'ag_test_case_pk',
            'fdbk_settings',
            'total_points',
            'total_points_possible',
            'ag_test_command_results',
        ]

        for fdbk_category in ag_models.FeedbackCategory:
            result_dict = self.ag_test_case_result.get_fdbk(fdbk_category).to_dict()
            self.assertCountEqual(expected_keys, result_dict.keys())

            self.assertCountEqual(
                [result1.get_fdbk(fdbk_category).to_dict(),
                 result2.get_fdbk(fdbk_category).to_dict()],
                result_dict['ag_test_command_results'])
