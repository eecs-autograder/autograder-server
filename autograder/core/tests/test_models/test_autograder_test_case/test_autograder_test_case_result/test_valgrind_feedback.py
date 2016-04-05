import random
import string

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.core.models as ag_models

import autograder.core.shared.feedback_configuration as fbc

from autograder.core.tests.test_models.test_autograder_test_case.models \
    import _DummyCompiledAutograderTestCase


class ValgrindFdbkTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.valgrind_output = (
            'memcheckererr ' + random.choice(string.ascii_letters))
        self.valgrind_ag_test = _DummyCompiledAutograderTestCase(
            name='valgrind_ag_test',
            use_valgrind=True,
            deduction_for_valgrind_errors=random.randint(-5, -2))

        self.correct_result = ag_models.AutograderTestCaseResult(
            test_case=self.valgrind_ag_test,
            valgrind_output=self.valgrind_output,
            valgrind_return_code=0)

        self.incorrect_result = ag_models.AutograderTestCaseResult(
            test_case=self.valgrind_ag_test,
            valgrind_output=self.valgrind_output,
            valgrind_return_code=random.randint(1, 4))

    def test_no_fdbk(self):
        self.assertIsNone(
            self.correct_result.get_feedback().valgrind_errors_reported)
        self.assertIsNone(self.correct_result.get_feedback().valgrind_output)

        self.assertIsNone(
            self.incorrect_result.get_feedback().valgrind_errors_reported)
        self.assertIsNone(self.incorrect_result.get_feedback().valgrind_output)

        # Hide points
        self.assertIsNone(
            self.correct_result.get_feedback().valgrind_points_deducted)
        self.assertIsNone(
            self.incorrect_result.get_feedback().valgrind_points_deducted)

        # Show points set (but points still hidden)
        self.valgrind_ag_test.feedback_configuration.points_feedback_level = (
            fbc.PointsFeedbackLevel.show_breakdown)
        self.assertIsNone(
            self.correct_result.get_feedback().valgrind_points_deducted)
        self.assertIsNone(
            self.incorrect_result.get_feedback().valgrind_points_deducted)

    def test_errors_or_no_errors_only(self):
        (self.valgrind_ag_test.feedback_configuration
                              .valgrind_feedback_level) = (
            fbc.ValgrindFeedbackLevel.errors_or_no_errors_only)

        self.assertFalse(
            self.correct_result.get_feedback().valgrind_errors_reported)
        self.assertIsNone(self.correct_result.get_feedback().valgrind_output)

        self.assertTrue(
            self.incorrect_result.get_feedback().valgrind_errors_reported)
        self.assertIsNone(self.incorrect_result.get_feedback().valgrind_output)

        self._check_points_shown_and_hidden()

    def test_show_valgrind_output(self):
        (self.valgrind_ag_test.feedback_configuration
                              .valgrind_feedback_level) = (
            fbc.ValgrindFeedbackLevel.show_valgrind_output)

        self.assertFalse(
            self.correct_result.get_feedback().valgrind_errors_reported)
        self.assertEqual(self.valgrind_output,
                         self.correct_result.get_feedback().valgrind_output)

        self.assertTrue(
            self.incorrect_result.get_feedback().valgrind_errors_reported)
        self.assertEqual(self.valgrind_output,
                         self.incorrect_result.get_feedback().valgrind_output)

        self._check_points_shown_and_hidden()

    def test_fdbk_not_applicable_valgrind_not_used(self):
        no_valgrind_test = _DummyCompiledAutograderTestCase(
            name='no_valgrind_test', deduction_for_valgrind_errors=42)
        result = ag_models.AutograderTestCaseResult(test_case=no_valgrind_test)

        self.assertIsNone(
            result.get_feedback().valgrind_errors_reported)
        self.assertIsNone(result.get_feedback().valgrind_output)
        self.assertIsNone(result.get_feedback().valgrind_points_deducted)

    def _check_points_shown_and_hidden(self):
        # Hide points
        self.assertIsNone(
            self.correct_result.get_feedback().valgrind_points_deducted)
        self.assertIsNone(
            self.incorrect_result.get_feedback().valgrind_points_deducted)

        # Show points
        self.valgrind_ag_test.feedback_configuration.points_feedback_level = (
            fbc.PointsFeedbackLevel.show_breakdown)
        self.assertEqual(
            0,
            self.correct_result.get_feedback().valgrind_points_deducted)
        self.assertEqual(
            self.valgrind_ag_test.deduction_for_valgrind_errors,
            self.incorrect_result.get_feedback().valgrind_points_deducted)
