import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class AGTestSuiteResultTestCase(UnitTestBase):
    def setUp(self):
        submission = obj_build.build_submission()
        project = submission.submission_group.project
        self.ag_test_suite = ag_models.AGTestSuite.objects.validate_and_create(
            name='kajsdhf', project=project
        )  # type: ag_models.AGTestSuite

        self.ag_test_case1 = ag_models.AGTestCase.objects.validate_and_create(
            name='aksdbva', ag_test_suite=self.ag_test_suite
        )  # type: ag_models.AGTestCase
        self.ag_test_case2 = ag_models.AGTestCase.objects.validate_and_create(
            name='ndkaadjhfa', ag_test_suite=self.ag_test_suite,
        )  # type: ag_models.AGTestCase

        self.ag_test_cmd1 = obj_build.make_full_ag_test_command(
            self.ag_test_case1, set_arbitrary_points=False,
            points_for_correct_return_code=4)
        self.ag_test_cmd2 = obj_build.make_full_ag_test_command(
            self.ag_test_case2, set_arbitrary_points=False,
            points_for_correct_return_code=5)
        self.total_points = 9

        self.ag_test_suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            submission=submission, ag_test_suite=self.ag_test_suite
        )  # type: ag_models.AGTestSuiteResult

        self.ag_test_case_result1 = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=self.ag_test_case1, ag_test_suite_result=self.ag_test_suite_result
        )  # type: ag_models.AGTestCaseResult
        self.ag_test_case_result2 = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=self.ag_test_case2, ag_test_suite_result=self.ag_test_suite_result
        )  # type: ag_models.AGTestCaseResult

        obj_build.make_correct_ag_test_command_result(self.ag_test_cmd1, self.ag_test_case_result1)
        obj_build.make_correct_ag_test_command_result(self.ag_test_cmd2, self.ag_test_case_result2)

    def test_feedback_calculator_ctor(self):
        self.assertEqual(
            self.ag_test_suite.normal_fdbk_config,
            self.ag_test_suite_result.get_fdbk(ag_models.FeedbackCategory.normal).fdbk_conf)
        self.assertEqual(
            self.ag_test_suite.ultimate_submission_fdbk_config,
            self.ag_test_suite_result.get_fdbk(
                ag_models.FeedbackCategory.ultimate_submission).fdbk_conf)
        self.assertEqual(
            self.ag_test_suite.past_limit_submission_fdbk_config,
            self.ag_test_suite_result.get_fdbk(
                ag_models.FeedbackCategory.past_limit_submission).fdbk_conf)
        self.assertEqual(
            self.ag_test_suite.staff_viewer_fdbk_config,
            self.ag_test_suite_result.get_fdbk(ag_models.FeedbackCategory.staff_viewer).fdbk_conf)

        max_config = self.ag_test_suite_result.get_fdbk(ag_models.FeedbackCategory.max).fdbk_conf
        self.assertTrue(max_config.show_individual_tests)
        self.assertTrue(max_config.show_setup_and_teardown_commands)

    def test_points_max_fdbk(self):
        self.assertEqual(
            self.total_points,
            self.ag_test_suite_result.get_fdbk(ag_models.FeedbackCategory.max).total_points)
        self.assertEqual(
            self.total_points,
            self.ag_test_suite_result.get_fdbk(ag_models.FeedbackCategory.max).total_points_possible)

    def test_points_minimum_ag_test_command_fdbk(self):
        fdbk = self.ag_test_suite_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertEqual(0, fdbk.total_points)
        self.assertEqual(0, fdbk.total_points_possible)

    def test_show_individual_tests(self):
        self.ag_test_cmd1.normal_fdbk_config.validate_and_update(
            return_code_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            show_points=True)

        self.ag_test_cmd2.normal_fdbk_config.validate_and_update(
            return_code_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            show_points=True)

        self.assertTrue(self.ag_test_suite.normal_fdbk_config.show_individual_tests)
        fdbk = self.ag_test_suite_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertEqual(
            [self.ag_test_case_result1, self.ag_test_case_result2], fdbk.ag_test_case_results)
        self.assertEqual(self.total_points, fdbk.total_points)
        self.assertEqual(self.total_points, fdbk.total_points_possible)

        self.ag_test_suite.normal_fdbk_config.validate_and_update(show_individual_tests=False)
        fdbk = self.ag_test_suite_result.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertEqual([], fdbk.ag_test_case_results)
        self.assertEqual(self.total_points, fdbk.total_points)
        self.assertEqual(self.total_points, fdbk.total_points_possible)

    def test_individual_test_result_order(self):
        self.ag_test_suite.set_agtestcase_order([self.ag_test_case2.pk, self.ag_test_case1.pk])
        fdbk = self.ag_test_suite_result.get_fdbk(ag_models.FeedbackCategory.max)
        self.assertEqual([self.ag_test_case_result2, self.ag_test_case_result1],
                         fdbk.ag_test_case_results)

    def test_show_setup_and_teardown_commands(self):
        self.fail()

    def test_fdbk_to_dict(self):
        # use mocking to make sure fdbk propagates
        self.fail()
