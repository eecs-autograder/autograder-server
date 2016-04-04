import random
import difflib

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.core.models as ag_models

import autograder.core.shared.feedback_configuration as fbc

from autograder.core.tests.test_models.test_autograder_test_case.models import (
    _DummyAutograderTestCase)

_DIFFER = difflib.Differ()


class StdoutFdbkTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        expected_stdout = "some\n cool\n output\n {}\n".format(
            random.randint(0, 9000))
        self.stdout_ag_test = _DummyAutograderTestCase(
            name='stdout_ag_test',
            expected_standard_output=expected_stdout,
            points_for_correct_stdout=random.randint(1, 9))

        self.correct_result = ag_models.AutograderTestCaseResult(
            test_case=self.stdout_ag_test,
            standard_output=expected_stdout)

        self.incorrect_result = ag_models.AutograderTestCaseResult(
            test_case=self.stdout_ag_test,
            standard_output=expected_stdout + 'wrong')

    def test_no_fdbk(self):
        self.stdout_ag_test.feedback_configuration.points_feedback_level = (
            fbc.PointsFeedbackLevel.show_breakdown)

        self.assertIsNone(self.correct_result.feedback.stdout_correct)
        self.assertIsNone(self.correct_result.feedback.stdout_content)
        self.assertIsNone(self.correct_result.feedback.stdout_diff)
        self.assertIsNone(self.correct_result.feedback.stdout_points)

        self.assertIsNone(self.incorrect_result.feedback.stdout_correct)
        self.assertIsNone(self.incorrect_result.feedback.stdout_content)
        self.assertIsNone(self.incorrect_result.feedback.stdout_diff)
        self.assertIsNone(self.incorrect_result.feedback.stdout_points)

    def test_correct_or_incorrect_only_fdbk(self):
        (self.stdout_ag_test.feedback_configuration
                            .standard_output_feedback_level) = (
            fbc.StandardOutputFeedbackLevel.correct_or_incorrect_only)

        self.assertTrue(self.correct_result.feedback.stdout_correct)
        self.assertIsNone(self.correct_result.feedback.stdout_content)
        self.assertIsNone(self.correct_result.feedback.stdout_diff)

        self.assertFalse(self.incorrect_result.feedback.stdout_correct)
        self.assertIsNone(self.incorrect_result.feedback.stdout_content)
        self.assertIsNone(self.incorrect_result.feedback.stdout_diff)

        self._check_points_shown_and_hidden()

    def test_show_expected_and_actual_values_fdbk(self):
        (self.stdout_ag_test.feedback_configuration
                            .standard_output_feedback_level) = (
            fbc.StandardOutputFeedbackLevel.show_expected_and_actual_values)

        self.assertTrue(self.correct_result.feedback.stdout_correct)
        self.assertIsNone(self.correct_result.feedback.stdout_content)
        self.assertEqual('', self.correct_result.feedback.stdout_diff)

        self.assertFalse(self.incorrect_result.feedback.stdout_correct)
        self.assertIsNone(self.correct_result.feedback.stdout_content)
        diff = _DIFFER.compare(
            self.stdout_ag_test.expected_standard_output.splitlines(
                keepends=True),
            self.incorrect_result.standard_output.splitlines(keepends=True))
        self.assertEqual(list(diff),
                         self.incorrect_result.feedback.stdout_diff)

        self._check_points_shown_and_hidden()

    def test_show_program_stdout_fdbk(self):
        self.stdout_ag_test.feedback_configuration.show_stdout_content = True

        self.assertEqual(self.correct_result.standard_output,
                         self.correct_result.feedback.stdout_content)

        self.assertEqual(self.incorrect_result.standard_output,
                         self.incorrect_result.feedback.stdout_content)

    def test_fdbk_not_applicable_stdout_not_checked_fdbk(self):
        no_stdout_check_ag_test = _DummyAutograderTestCase(
            name='no_stdout_check_ag_test',
            points_for_correct_stdout=random.randint(1, 9))
        result = ag_models.AutograderTestCaseResult(
            test_case=no_stdout_check_ag_test,
            standard_output=self.stdout_ag_test.expected_standard_output)

        (no_stdout_check_ag_test.feedback_configuration
                                .standard_output_feedback_level) = (
            fbc.StandardOutputFeedbackLevel.show_expected_and_actual_values)

        self.assertIsNone(result.feedback.stdout_correct)
        self.assertIsNone(result.feedback.stdout_diff)
        self.assertIsNone(result.feedback.stdout_points)

        # Hide stdout
        self.assertIsNone(result.feedback.stdout_content)

        # Show stdout
        no_stdout_check_ag_test.feedback_configuration.show_stdout_content = (
            True)
        self.assertEqual(result.standard_output,
                         result.feedback.stdout_content)

    def _check_points_shown_and_hidden(self):
        # Show points
        self.stdout_ag_test.feedback_configuration.points_feedback_level = (
            fbc.PointsFeedbackLevel.show_breakdown)
        self.assertEqual(self.stdout_ag_test.points_for_correct_stdout,
                         self.correct_result.feedback.stdout_points)
        self.assertEqual(0, self.incorrect_result.feedback.stdout_points)

        # Hide points
        self.stdout_ag_test.feedback_configuration.points_feedback_level = (
            fbc.PointsFeedbackLevel.hide)
        self.assertIsNone(self.correct_result.feedback.stdout_points)
        self.assertIsNone(self.incorrect_result.feedback.stdout_points)


class StderrFdbkTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        expected_stderr = "some\n cool\n stderrrr\n {}\n".format(
            random.randint(0, 9000))
        self.stderr_ag_test = _DummyAutograderTestCase(
            name='stderr_ag_test',
            expected_standard_error_output=expected_stderr,
            points_for_correct_stderr=random.randint(1, 9))

        self.correct_result = ag_models.AutograderTestCaseResult(
            test_case=self.stderr_ag_test,
            standard_error_output=expected_stderr)

        self.incorrect_result = ag_models.AutograderTestCaseResult(
            test_case=self.stderr_ag_test,
            standard_error_output=expected_stderr + 'wrong')

    def test_no_fdbk(self):
        self.stderr_ag_test.feedback_configuration.points_feedback_level = (
            fbc.PointsFeedbackLevel.show_breakdown)

        self.assertIsNone(self.correct_result.feedback.stderr_correct)
        self.assertIsNone(self.correct_result.feedback.stderr_content)
        self.assertIsNone(self.correct_result.feedback.stderr_diff)
        self.assertIsNone(self.correct_result.feedback.stderr_points)

        self.assertIsNone(self.incorrect_result.feedback.stderr_correct)
        self.assertIsNone(self.incorrect_result.feedback.stderr_content)
        self.assertIsNone(self.incorrect_result.feedback.stderr_diff)
        self.assertIsNone(self.incorrect_result.feedback.stderr_points)

    def test_correct_or_incorrect_only_fdbk(self):
        (self.stderr_ag_test.feedback_configuration
                            .standard_error_output_feedback_level) = (
            fbc.StandardErrorOutputFeedbackLevel.correct_or_incorrect_only)

        self.assertTrue(self.correct_result.feedback.stderr_correct)
        self.assertIsNone(self.correct_result.feedback.stderr_content)
        self.assertIsNone(self.correct_result.feedback.stderr_diff)

        self.assertFalse(self.incorrect_result.feedback.stderr_correct)
        self.assertIsNone(self.incorrect_result.feedback.stderr_content)
        self.assertIsNone(self.incorrect_result.feedback.stderr_diff)

        self._check_points_shown_and_hidden()

    def test_show_expected_and_actual_values_fdbk(self):
        (self.stderr_ag_test.feedback_configuration
                            .standard_error_output_feedback_level) = (
            (fbc.StandardErrorOutputFeedbackLevel
                .show_expected_and_actual_values))

        self.assertTrue(self.correct_result.feedback.stderr_correct)
        self.assertIsNone(self.correct_result.feedback.stderr_content)
        self.assertEqual('', self.correct_result.feedback.stderr_diff)

        self.assertFalse(self.incorrect_result.feedback.stderr_correct)
        self.assertIsNone(self.correct_result.feedback.stderr_content)
        diff = _DIFFER.compare(
            self.stderr_ag_test.expected_standard_error_output.splitlines(
                keepends=True),
            self.incorrect_result.standard_error_output.splitlines(
                keepends=True))
        self.assertEqual(list(diff),
                         self.incorrect_result.feedback.stderr_diff)

        self._check_points_shown_and_hidden()

    def test_show_program_stderr_fdbk(self):
        self.stderr_ag_test.feedback_configuration.show_stderr_content = True

        self.assertEqual(self.correct_result.standard_error_output,
                         self.correct_result.feedback.stderr_content)

        self.assertEqual(self.incorrect_result.standard_error_output,
                         self.incorrect_result.feedback.stderr_content)

    def test_fdbk_not_applicable_stderr_not_checked_fdbk(self):
        no_stderr_check_ag_test = _DummyAutograderTestCase(
            name='no_stderr_check_ag_test',
            points_for_correct_stderr=random.randint(1, 9))
        result = ag_models.AutograderTestCaseResult(
            test_case=no_stderr_check_ag_test,
            standard_error_output=(
                self.stderr_ag_test.expected_standard_error_output))

        (no_stderr_check_ag_test.feedback_configuration
                                .standard_error_output_feedback_level) = (
            (fbc.StandardErrorOutputFeedbackLevel
                .show_expected_and_actual_values))

        self.assertIsNone(result.feedback.stderr_correct)
        self.assertIsNone(result.feedback.stderr_diff)
        self.assertIsNone(result.feedback.stderr_points)

        # Hide stderr
        self.assertIsNone(result.feedback.stderr_content)

        # Show stderr
        no_stderr_check_ag_test.feedback_configuration.show_stderr_content = (
            True)
        self.assertEqual(result.standard_error_output,
                         result.feedback.stderr_content)

    def _check_points_shown_and_hidden(self):
        # Show points
        self.stderr_ag_test.feedback_configuration.points_feedback_level = (
            fbc.PointsFeedbackLevel.show_breakdown)
        self.assertEqual(self.stderr_ag_test.points_for_correct_stderr,
                         self.correct_result.feedback.stderr_points)
        self.assertEqual(0, self.incorrect_result.feedback.stderr_points)

        # Hide points
        self.stderr_ag_test.feedback_configuration.points_feedback_level = (
            fbc.PointsFeedbackLevel.hide)
        self.assertIsNone(self.correct_result.feedback.stderr_points)
        self.assertIsNone(self.incorrect_result.feedback.stderr_points)
