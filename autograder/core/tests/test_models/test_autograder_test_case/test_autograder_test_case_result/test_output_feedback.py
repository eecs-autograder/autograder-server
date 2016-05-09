import random
import difflib

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.core.models as ag_models

import autograder.core.models.autograder_test_case.feedback_config as fdbk_lvls

import autograder.core.tests.dummy_object_utils as obj_ut
from autograder.core.tests.test_models.test_autograder_test_case.models import (
    _DummyAutograderTestCase)

_DIFFER = difflib.Differ()


class StdoutFdbkTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.project = obj_ut.build_project()

        expected_stdout = "some\n cool\n output\n {}\n".format(
            random.randint(0, 9000))
        self.stdout_ag_test = _DummyAutograderTestCase.objects.validate_and_create(
            name='stdout_ag_test',
            project=self.project,
            expected_standard_output=expected_stdout,
            points_for_correct_stdout=random.randint(1, 9))

        self.correct_result = ag_models.AutograderTestCaseResult(
            test_case=self.stdout_ag_test,
            standard_output=expected_stdout)

        self.incorrect_result = ag_models.AutograderTestCaseResult(
            test_case=self.stdout_ag_test,
            standard_output=expected_stdout + 'wrong')

    def test_no_fdbk(self):
        self.stdout_ag_test.feedback_configuration.validate_and_update(
            points_fdbk=fdbk_lvls.PointsFdbkLevel.show_breakdown)

        self.assertIsNone(self.correct_result.get_feedback().stdout_correct)
        self.assertIsNone(self.correct_result.get_feedback().stdout_content)
        self.assertIsNone(self.correct_result.get_feedback().stdout_diff)
        self.assertIsNone(self.correct_result.get_feedback().stdout_points)

        self.assertIsNone(self.incorrect_result.get_feedback().stdout_correct)
        self.assertIsNone(self.incorrect_result.get_feedback().stdout_content)
        self.assertIsNone(self.incorrect_result.get_feedback().stdout_diff)
        self.assertIsNone(self.incorrect_result.get_feedback().stdout_points)

    def test_correct_or_incorrect_only_fdbk(self):
        self.stdout_ag_test.feedback_configuration.validate_and_update(
            stdout_fdbk=(
                fdbk_lvls.StdoutFdbkLevel.correct_or_incorrect_only))

        self.assertTrue(self.correct_result.get_feedback().stdout_correct)
        self.assertIsNone(self.correct_result.get_feedback().stdout_content)
        self.assertIsNone(self.correct_result.get_feedback().stdout_diff)

        self.assertFalse(self.incorrect_result.get_feedback().stdout_correct)
        self.assertIsNone(self.incorrect_result.get_feedback().stdout_content)
        self.assertIsNone(self.incorrect_result.get_feedback().stdout_diff)

        self._check_points_shown_and_hidden()

    def test_show_expected_and_actual_values_fdbk(self):
        self.stdout_ag_test.feedback_configuration.validate_and_update(
            stdout_fdbk=(
                fdbk_lvls.StdoutFdbkLevel.show_expected_and_actual_values))

        self.assertTrue(self.correct_result.get_feedback().stdout_correct)
        self.assertIsNone(self.correct_result.get_feedback().stdout_content)
        self.assertEqual('', self.correct_result.get_feedback().stdout_diff)

        self.assertFalse(self.incorrect_result.get_feedback().stdout_correct)
        self.assertIsNone(self.correct_result.get_feedback().stdout_content)
        diff = _DIFFER.compare(
            self.stdout_ag_test.expected_standard_output.splitlines(
                keepends=True),
            self.incorrect_result.standard_output.splitlines(keepends=True))
        self.assertEqual(list(diff),
                         self.incorrect_result.get_feedback().stdout_diff)

        self._check_points_shown_and_hidden()

    def test_show_program_stdout_fdbk(self):
        self.stdout_ag_test.feedback_configuration.validate_and_update(
            show_stdout_content=True)

        self.assertEqual(self.correct_result.standard_output,
                         self.correct_result.get_feedback().stdout_content)

        self.assertEqual(self.incorrect_result.standard_output,
                         self.incorrect_result.get_feedback().stdout_content)

    def test_fdbk_not_applicable_stdout_not_checked_fdbk(self):
        no_stdout_check_ag_test = _DummyAutograderTestCase.objects.validate_and_create(
            name='no_stdout_check_ag_test',
            project=self.project,
            points_for_correct_stdout=random.randint(1, 9))
        result = ag_models.AutograderTestCaseResult(
            test_case=no_stdout_check_ag_test,
            standard_output=self.stdout_ag_test.expected_standard_output)

        no_stdout_check_ag_test.feedback_configuration.validate_and_update(
            stdout_fdbk=(
                fdbk_lvls.StdoutFdbkLevel.show_expected_and_actual_values))

        self.assertIsNone(result.get_feedback().stdout_correct)
        self.assertIsNone(result.get_feedback().stdout_diff)
        self.assertIsNone(result.get_feedback().stdout_points)

        # Hide stdout
        self.assertIsNone(result.get_feedback().stdout_content)

        # Show stdout
        no_stdout_check_ag_test.feedback_configuration.validate_and_update(
            show_stdout_content=True)
        self.assertEqual(result.standard_output,
                         result.get_feedback().stdout_content)

    def _check_points_shown_and_hidden(self):
        # Show points
        self.stdout_ag_test.feedback_configuration.validate_and_update(
            points_fdbk=fdbk_lvls.PointsFdbkLevel.show_breakdown)
        self.assertEqual(self.stdout_ag_test.points_for_correct_stdout,
                         self.correct_result.get_feedback().stdout_points)
        self.assertEqual(0, self.incorrect_result.get_feedback().stdout_points)

        # Hide points
        self.stdout_ag_test.feedback_configuration.validate_and_update(
            points_fdbk=fdbk_lvls.PointsFdbkLevel.hide)
        self.assertIsNone(self.correct_result.get_feedback().stdout_points)
        self.assertIsNone(self.incorrect_result.get_feedback().stdout_points)


class StderrFdbkTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.project = obj_ut.build_project()

        expected_stderr = "some\n cool\n stderrrr\n {}\n".format(
            random.randint(0, 9000))
        self.stderr_ag_test = _DummyAutograderTestCase.objects.validate_and_create(
            name='stderr_ag_test',
            project=self.project,
            expected_standard_error_output=expected_stderr,
            points_for_correct_stderr=random.randint(1, 9))

        self.correct_result = ag_models.AutograderTestCaseResult(
            test_case=self.stderr_ag_test,
            standard_error_output=expected_stderr)

        self.incorrect_result = ag_models.AutograderTestCaseResult(
            test_case=self.stderr_ag_test,
            standard_error_output=expected_stderr + 'wrong')

    def test_no_fdbk(self):
        self.stderr_ag_test.feedback_configuration.validate_and_update(
            points_fdbk=fdbk_lvls.PointsFdbkLevel.show_breakdown)

        self.assertIsNone(self.correct_result.get_feedback().stderr_correct)
        self.assertIsNone(self.correct_result.get_feedback().stderr_content)
        self.assertIsNone(self.correct_result.get_feedback().stderr_diff)
        self.assertIsNone(self.correct_result.get_feedback().stderr_points)

        self.assertIsNone(self.incorrect_result.get_feedback().stderr_correct)
        self.assertIsNone(self.incorrect_result.get_feedback().stderr_content)
        self.assertIsNone(self.incorrect_result.get_feedback().stderr_diff)
        self.assertIsNone(self.incorrect_result.get_feedback().stderr_points)

    def test_correct_or_incorrect_only_fdbk(self):
        self.stderr_ag_test.feedback_configuration.validate_and_update(
            stderr_fdbk=(
                fdbk_lvls.StderrFdbkLevel.correct_or_incorrect_only))

        self.assertTrue(self.correct_result.get_feedback().stderr_correct)
        self.assertIsNone(self.correct_result.get_feedback().stderr_content)
        self.assertIsNone(self.correct_result.get_feedback().stderr_diff)

        self.assertFalse(self.incorrect_result.get_feedback().stderr_correct)
        self.assertIsNone(self.incorrect_result.get_feedback().stderr_content)
        self.assertIsNone(self.incorrect_result.get_feedback().stderr_diff)

        self._check_points_shown_and_hidden()

    def test_show_expected_and_actual_values_fdbk(self):
        self.stderr_ag_test.feedback_configuration.validate_and_update(
            stderr_fdbk=(
                fdbk_lvls.StderrFdbkLevel.show_expected_and_actual_values))

        self.assertTrue(self.correct_result.get_feedback().stderr_correct)
        self.assertIsNone(self.correct_result.get_feedback().stderr_content)
        self.assertEqual('', self.correct_result.get_feedback().stderr_diff)

        self.assertFalse(self.incorrect_result.get_feedback().stderr_correct)
        self.assertIsNone(self.correct_result.get_feedback().stderr_content)
        diff = _DIFFER.compare(
            self.stderr_ag_test.expected_standard_error_output.splitlines(
                keepends=True),
            self.incorrect_result.standard_error_output.splitlines(
                keepends=True))
        self.assertEqual(list(diff),
                         self.incorrect_result.get_feedback().stderr_diff)

        self._check_points_shown_and_hidden()

    def test_show_program_stderr_fdbk(self):
        self.stderr_ag_test.feedback_configuration.validate_and_update(
            show_stderr_content=True)

        self.assertEqual(self.correct_result.standard_error_output,
                         self.correct_result.get_feedback().stderr_content)

        self.assertEqual(self.incorrect_result.standard_error_output,
                         self.incorrect_result.get_feedback().stderr_content)

    def test_fdbk_not_applicable_stderr_not_checked_fdbk(self):
        no_stderr_check_ag_test = _DummyAutograderTestCase.objects.validate_and_create(
            name='no_stderr_check_ag_test',
            project=self.project,
            points_for_correct_stderr=random.randint(1, 9))
        result = ag_models.AutograderTestCaseResult(
            test_case=no_stderr_check_ag_test,
            standard_error_output=(
                self.stderr_ag_test.expected_standard_error_output))

        no_stderr_check_ag_test.feedback_configuration.validate_and_update(
            stderr_fdbk=(
                fdbk_lvls.StderrFdbkLevel.show_expected_and_actual_values))

        self.assertIsNone(result.get_feedback().stderr_correct)
        self.assertIsNone(result.get_feedback().stderr_diff)
        self.assertIsNone(result.get_feedback().stderr_points)

        # Hide stderr
        self.assertIsNone(result.get_feedback().stderr_content)

        # Show stderr
        no_stderr_check_ag_test.feedback_configuration.validate_and_update(
            show_stderr_content=True)
        self.assertEqual(result.standard_error_output,
                         result.get_feedback().stderr_content)

    def _check_points_shown_and_hidden(self):
        # Show points
        self.stderr_ag_test.feedback_configuration.validate_and_update(
            points_fdbk=fdbk_lvls.PointsFdbkLevel.show_breakdown)
        self.assertEqual(self.stderr_ag_test.points_for_correct_stderr,
                         self.correct_result.get_feedback().stderr_points)
        self.assertEqual(0, self.incorrect_result.get_feedback().stderr_points)

        # Hide points
        self.stderr_ag_test.feedback_configuration.validate_and_update(
            points_fdbk=fdbk_lvls.PointsFdbkLevel.hide)
        self.assertIsNone(self.correct_result.get_feedback().stderr_points)
        self.assertIsNone(self.incorrect_result.get_feedback().stderr_points)
