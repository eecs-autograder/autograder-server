import random

import autograder.core.models as ag_models
import autograder.core.models.autograder_test_case.feedback_config as fdbk_lvls

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.tests.test_models.test_autograder_test_case.models \
    import _DummyAutograderTestCase


class ReturnCodeFdbkTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.project = obj_build.build_project()

        expected_ret_code = random.randint(0, 10)
        self.expected_ret_code_ag_test = (
            _DummyAutograderTestCase.objects.validate_and_create(
                name='expected_ret_code_ag_test',
                project=self.project,
                expected_return_code=expected_ret_code,
                points_for_correct_return_code=random.randint(1, 5)))
        self.expected_ret_code_correct_result = (
            ag_models.AutograderTestCaseResult(
                test_case=self.expected_ret_code_ag_test,
                return_code=expected_ret_code))
        self.expected_ret_code_incorrect_result = (
            ag_models.AutograderTestCaseResult(
                test_case=self.expected_ret_code_ag_test,
                return_code=expected_ret_code + 2))

        self.expect_nonzero_ret_code_ag_test = (
            _DummyAutograderTestCase.objects.validate_and_create(
                name='expect_nonzero_ret_code_ag_test',
                project=self.project,
                expect_any_nonzero_return_code=True,
                points_for_correct_return_code=random.randint(1, 5)))
        self.expect_nonzero_ret_code_correct_result = (
            ag_models.AutograderTestCaseResult(
                test_case=self.expect_nonzero_ret_code_ag_test,
                return_code=random.randint(1, 5)))
        self.expect_nonzero_ret_code_incorrect_result = (
            ag_models.AutograderTestCaseResult(
                test_case=self.expect_nonzero_ret_code_ag_test,
                return_code=0))

        self.tests_and_results = (
            (self.expected_ret_code_ag_test,
             self.expected_ret_code_correct_result,
             self.expected_ret_code_incorrect_result),

            (self.expect_nonzero_ret_code_ag_test,
             self.expect_nonzero_ret_code_correct_result,
             self.expect_nonzero_ret_code_incorrect_result),
        )

    def test_no_feedback(self):
        for test, correct, incorrect in self.tests_and_results:
            test.feedback_configuration.validate_and_update(
                points_fdbk=fdbk_lvls.PointsFdbkLevel.show_breakdown)

            self.assertIsNone(correct.get_feedback().return_code_correct,
                              msg=test.name)
            self.assertIsNone(correct.get_feedback().expected_return_code,
                              msg=test.name)
            self.assertIsNone(correct.get_feedback().actual_return_code,
                              msg=test.name)
            self.assertIsNone(correct.get_feedback().return_code_points,
                              msg=test.name)
            self.assertIsNone(
                correct.get_feedback().return_code_points_possible,
                msg=test.name)

            self.assertIsNone(incorrect.get_feedback().return_code_correct,
                              msg=test.name)
            self.assertIsNone(incorrect.get_feedback().expected_return_code,
                              msg=test.name)
            self.assertIsNone(incorrect.get_feedback().actual_return_code,
                              msg=test.name)
            self.assertIsNone(incorrect.get_feedback().return_code_points,
                              msg=test.name)
            self.assertIsNone(
                incorrect.get_feedback().return_code_points_possible,
                msg=test.name)

    def test_correct_or_incorrect_only_fdbk(self):
        for test, correct, incorrect in self.tests_and_results:
            test.feedback_configuration.validate_and_update(
                return_code_fdbk=(
                    fdbk_lvls.ReturnCodeFdbkLevel.correct_or_incorrect_only))

            # Show points
            test.feedback_configuration.validate_and_update(
                points_fdbk=fdbk_lvls.PointsFdbkLevel.show_breakdown)

            self.assertTrue(correct.get_feedback().return_code_correct,
                            msg=test.name)
            self.assertEqual(test.points_for_correct_return_code,
                             correct.get_feedback().return_code_points,
                             msg=test.name)
            self.assertEqual(test.points_for_correct_return_code,
                             correct.get_feedback().return_code_points_possible,
                             msg=test.name)
            self.assertIsNone(correct.get_feedback().expected_return_code)
            self.assertIsNone(correct.get_feedback().actual_return_code)

            self.assertFalse(incorrect.get_feedback().return_code_correct,
                             msg=test.name)
            self.assertEqual(0, incorrect.get_feedback().return_code_points)
            self.assertEqual(
                test.points_for_correct_return_code,
                incorrect.get_feedback().return_code_points_possible)
            self.assertIsNone(incorrect.get_feedback().expected_return_code)
            self.assertIsNone(incorrect.get_feedback().actual_return_code)

            # Hide points
            test.feedback_configuration.validate_and_update(
                points_fdbk=fdbk_lvls.PointsFdbkLevel.hide)
            self.assertIsNone(correct.get_feedback().return_code_points,
                              msg=test.name)
            self.assertIsNone(
                correct.get_feedback().return_code_points_possible,
                msg=test.name)
            self.assertIsNone(incorrect.get_feedback().return_code_points,
                              msg=test.name)
            self.assertIsNone(
                incorrect.get_feedback().return_code_points_possible,
                msg=test.name)

    def test_show_expected_and_actual_values_fdbk(self):
        for test, correct, incorrect in self.tests_and_results:
            test.feedback_configuration.validate_and_update(
                return_code_fdbk=(
                    fdbk_lvls.ReturnCodeFdbkLevel.show_expected_and_actual_values))

            # Show points
            test.feedback_configuration.validate_and_update(
                points_fdbk=fdbk_lvls.PointsFdbkLevel.show_breakdown)

            self.assertEqual(test.expected_return_code,
                             correct.get_feedback().expected_return_code,
                             msg=test.name)
            self.assertEqual(correct.return_code,
                             correct.get_feedback().actual_return_code,
                             msg=test.name)
            self.assertEqual(test.points_for_correct_return_code,
                             correct.get_feedback().return_code_points,
                             msg=test.name)
            self.assertEqual(
                test.points_for_correct_return_code,
                correct.get_feedback().return_code_points_possible,
                msg=test.name)
            self.assertTrue(correct.get_feedback().return_code_correct,
                            msg=test.name)

            self.assertEqual(test.expected_return_code,
                             incorrect.get_feedback().expected_return_code,
                             msg=test.name)
            self.assertEqual(incorrect.return_code,
                             incorrect.get_feedback().actual_return_code,
                             msg=test.name)
            self.assertEqual(0, incorrect.get_feedback().return_code_points,
                             msg=test.name)
            self.assertEqual(
                test.points_for_correct_return_code,
                incorrect.get_feedback().return_code_points_possible,
                msg=test.name)
            self.assertFalse(incorrect.get_feedback().return_code_correct,
                             msg=test.name)

            # Hide points
            test.feedback_configuration.validate_and_update(
                points_fdbk=fdbk_lvls.PointsFdbkLevel.hide)
            self.assertIsNone(correct.get_feedback().return_code_points,
                              msg=test.name)
            self.assertIsNone(
                correct.get_feedback().return_code_points_possible,
                msg=test.name)

            self.assertIsNone(incorrect.get_feedback().return_code_points,
                              msg=test.name)
            self.assertIsNone(
                incorrect.get_feedback().return_code_points_possible,
                msg=test.name)

    def test_show_return_code(self):
        for test, correct, incorrect in self.tests_and_results:
            test.feedback_configuration.validate_and_update(
                show_return_code=True)

            self.assertEqual(correct.return_code,
                             correct.get_feedback().actual_return_code)
            self.assertEqual(incorrect.return_code,
                             incorrect.get_feedback().actual_return_code)

    def test_fdbk_not_applicable_return_code_not_checked(self):
        no_ret_code_check_ag_test = _DummyAutograderTestCase.objects.validate_and_create(
            name='no_ret_code_check_ag_test',
            project=self.project,
            points_for_correct_return_code=random.randint(1, 5))
        no_ret_code_check_result = ag_models.AutograderTestCaseResult(
            test_case=no_ret_code_check_ag_test,
            return_code=42)

        no_ret_code_check_ag_test.feedback_configuration.validate_and_update(
            return_code_fdbk=(
                fdbk_lvls.ReturnCodeFdbkLevel.show_expected_and_actual_values))
        no_ret_code_check_ag_test.feedback_configuration.validate_and_update(
            points_fdbk=fdbk_lvls.PointsFdbkLevel.show_breakdown)

        self.assertIsNone(
            no_ret_code_check_result.get_feedback().return_code_correct)
        self.assertIsNone(
            no_ret_code_check_result.get_feedback().expected_return_code)
        self.assertIsNone(
            no_ret_code_check_result.get_feedback().return_code_points)
        self.assertIsNone(
            no_ret_code_check_result.get_feedback().return_code_points_possible)

        # Hide return code
        self.assertIsNone(
            no_ret_code_check_result.get_feedback().actual_return_code)

        # Show return code
        no_ret_code_check_ag_test.feedback_configuration.validate_and_update(
            show_return_code=True)

        self.assertEqual(
            no_ret_code_check_result.return_code,
            no_ret_code_check_result.get_feedback().actual_return_code)
