import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class AGTestSuiteResultTestCase(UnitTestBase):
    def setUp(self):
        submission = obj_build.build_submission()
        project = submission.submission_group.project
        self.ag_suite = ag_models.AGTestSuite.objects.validate_and_create(
            name='kajsdhf', project=project
        )  # type: ag_models.AGTestSuite

        self.ag_test_case1 = ag_models.AGTestCase.objects.validate_and_create(
            name='aksdbva', ag_test_suite=self.ag_suite
        )  # type: ag_models.AGTestCase
        self.ag_test_case2 = ag_models.AGTestCase.objects.validate_and_create(
            name='aksdbva', ag_test_suite=self.ag_suite
        )  # type: ag_models.AGTestCase

        self.suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            submission=submission, ag_test_suite=self.ag_suite
        )  # type: ag_models.AGTestSuiteResult
        ag_test_case_result = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=self.ag_test_case, ag_test_suite_result=self.suite_result
        )  # type: ag_models.AGTestCaseResult

        self.ag_test_cmd1 = obj_build.make_full_ag_test_command(
            self.ag_test_case, set_arbitrary_points=False)
        self.ag_test_cmd2 = obj_build.make_full_ag_test_command(
            self.ag_test_case, set_arbitrary_points=False)

        # 2 ag test cases, one with show individual commands, one without
        pass

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
        self.assertTrue(max_config.show_setup_command)

        self.fail()

    def test_points_max_fdbk(self):
        self.fail()

    def test_points_min_normal_fdbk(self):
        self.fail()

    def test_show_individual_tests(self):
        self.fail()

    def test_show_setup_command(self):
        self.fail()

    def test_fdbk_to_dict(self):
        self.fail()
