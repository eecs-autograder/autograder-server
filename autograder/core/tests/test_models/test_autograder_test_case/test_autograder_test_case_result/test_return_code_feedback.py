import random

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut

from autograder.core.models import (
    Project, Semester, Course,
    AutograderTestCaseFactory, AutograderTestCaseResult,
    SubmissionGroup, Submission)

import autograder.core.shared.feedback_configuration as fbc

from autograder.core.tests.test_models.test_autograder_test_case.models import (
    _DummyAutograderTestCase, _DummyCompiledAutograderTestCase)


class ReturnCodeFdbkTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.project = obj_ut.build_project()

        expected_ret_code = random.randint(0, 10)
        self.expected_ret_code_ag_test = (
            _DummyAutograderTestCase(
                name='expected_ret_code_ag_test', project=self.project,
                expected_return_code=expected_ret_code,
                points_for_correct_return_code=random.randint(1, 5)))
        self.expected_ret_code_correct_result = (
            AutograderTestCaseResult(
                test_case=self.expected_ret_code_ag_test,
                return_code=expected_ret_code))
        self.expected_ret_code_incorrect_result = (
            AutograderTestCaseResult(
                test_case=self.expected_ret_code_ag_test,
                return_code=expected_ret_code + 2))

        self.expect_nonzero_ret_code_ag_test = (
            _DummyAutograderTestCase(
                name='expect_nonzero_ret_code_ag_test', project=self.project,
                expect_any_nonzero_return_code=True,
                points_for_correct_return_code=random.randint(1, 5)))
        self.expect_nonzero_ret_code_correct_result = (
            AutograderTestCaseResult(
                test_case=self.expect_nonzero_ret_code_ag_test,
                return_code=random.randint(1, 5)))
        self.expect_nonzero_ret_code_incorrect_result = (
            AutograderTestCaseResult(
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
            test.feedback_configuration.points_feedback_level = (
                fbc.PointsFeedbackLevel.show_breakdown)

            self.assertIsNone(correct.feedback.return_code_correct,
                              msg=test.name)
            self.assertIsNone(correct.feedback.expected_return_code,
                              msg=test.name)
            self.assertIsNone(correct.feedback.actual_return_code,
                              msg=test.name)
            self.assertIsNone(correct.feedback.return_code_points,
                              msg=test.name)

            self.assertIsNone(incorrect.feedback.return_code_correct,
                              msg=test.name)
            self.assertIsNone(incorrect.feedback.expected_return_code,
                              msg=test.name)
            self.assertIsNone(incorrect.feedback.actual_return_code,
                              msg=test.name)
            self.assertIsNone(incorrect.feedback.return_code_points,
                              msg=test.name)

    def test_correct_or_incorrect_only_fdbk(self):
        for test, correct, incorrect in self.tests_and_results:
            test.feedback_configuration.return_code_feedback_level = (
                fbc.ReturnCodeFeedbackLevel.correct_or_incorrect_only)

            # Show points
            test.feedback_configuration.points_feedback_level = (
                fbc.PointsFeedbackLevel.show_breakdown)

            self.assertTrue(correct.feedback.return_code_correct,
                            msg=test.name)
            self.assertEqual(test.points_for_correct_return_code,
                             correct.feedback.return_code_points,
                             msg=test.name)
            self.assertIsNone(correct.feedback.expected_return_code)
            self.assertIsNone(correct.feedback.actual_return_code)

            self.assertFalse(incorrect.feedback.return_code_correct,
                             msg=test.name)
            self.assertEqual(0, incorrect.feedback.return_code_points)
            self.assertIsNone(incorrect.feedback.expected_return_code)
            self.assertIsNone(incorrect.feedback.actual_return_code)

            # Hide points
            test.feedback_configuration.points_feedback_level = (
                fbc.PointsFeedbackLevel.hide)
            self.assertIsNone(correct.feedback.return_code_points,
                              msg=test.name)
            self.assertIsNone(incorrect.feedback.return_code_points,
                              msg=test.name)

    def test_show_expected_and_actual_values_fdbk(self):
        for test, correct, incorrect in self.tests_and_results:
            test.feedback_configuration.return_code_feedback_level = (
                fbc.ReturnCodeFeedbackLevel.show_expected_and_actual_values)

            # Show points
            test.feedback_configuration.points_feedback_level = (
                fbc.PointsFeedbackLevel.show_breakdown)

            self.assertEqual(test.expected_return_code,
                             correct.feedback.expected_return_code,
                             msg=test.name)
            self.assertEqual(correct.return_code,
                             correct.feedback.actual_return_code,
                             msg=test.name)
            self.assertEqual(test.points_for_correct_return_code,
                             correct.feedback.return_code_points,
                             msg=test.name)
            self.assertTrue(correct.feedback.return_code_correct,
                            msg=test.name)

            self.assertEqual(test.expected_return_code,
                             incorrect.feedback.expected_return_code,
                             msg=test.name)
            self.assertEqual(incorrect.return_code,
                             incorrect.feedback.actual_return_code,
                             msg=test.name)
            self.assertEqual(0, incorrect.feedback.return_code_points,
                             msg=test.name)
            self.assertFalse(incorrect.feedback.return_code_correct,
                             msg=test.name)

            # Hide points
            test.feedback_configuration.points_feedback_level = (
                fbc.PointsFeedbackLevel.hide)
            self.assertIsNone(correct.feedback.return_code_points,
                              msg=test.name)
            self.assertIsNone(incorrect.feedback.return_code_points,
                              msg=test.name)

    def test_fdbk_not_applicable_return_code_not_checked(self):
        no_ret_code_check_ag_test = _DummyAutograderTestCase(
            name='no_ret_code_check_ag_test', project=self.project,
            points_for_correct_return_code=random.randint(1, 5))
        no_ret_code_check_result = AutograderTestCaseResult(
            test_case=no_ret_code_check_ag_test,
            return_code=42)

        (no_ret_code_check_ag_test.feedback_configuration
                                  .return_code_feedback_level) = (
            fbc.ReturnCodeFeedbackLevel.show_expected_and_actual_values)
        (no_ret_code_check_ag_test.feedback_configuration
                                  .points_feedback_level) = (
            fbc.PointsFeedbackLevel.show_breakdown)

        self.assertIsNone(
            no_ret_code_check_result.feedback.return_code_correct)
        self.assertIsNone(
            no_ret_code_check_result.feedback.expected_return_code)
        self.assertIsNone(
            no_ret_code_check_result.feedback.actual_return_code)
        self.assertIsNone(
            no_ret_code_check_result.feedback.return_code_points)


class ReturnCodeFdbkOverrideTesCase(TemporaryFilesystemTestCase):
    def test_manual_override(self):
        self.fail()

    def test_ultimate_submission_fdbk_override(self):
        self.fail()

    def test_ultimate_submission_fdbk_and_manual_override(self):
        self.fail()

    def test_reduced_submission_fdbk_override(self):
        self.fail()

    def test_reduced_submission_fdbk_and_manual_override(self):
        self.fail()

    def test_reduced_and_ultimate_submission_fdbk_override(self):
        self.fail()

    def test_reduced_and_ultimate_submission_fdbk_and_manual_override(self):
        self.fail()
