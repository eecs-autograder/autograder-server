import random
import string

from autograder.utils.testing import UnitTestBase

import autograder.core.models as ag_models
import autograder.core.models.autograder_test_case.feedback_config as fdbk_lvls

import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.tests.test_models.test_autograder_test_case.models import (
    _DummyAutograderTestCase, _DummyCompiledAutograderTestCase)


class CompilationFdbkTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.project = obj_build.build_project()

        self.compiler_stdout = (
            'it compiled ' + random.choice(string.ascii_letters))
        self.compiler_stderr = (
            'ERRORRRRRR ' + random.choice(string.ascii_letters))
        self.compilation_ag_test = _DummyCompiledAutograderTestCase.objects.validate_and_create(
            name='compilation_ag_test',
            project=self.project,
            compiler='g++',
            points_for_compilation_success=random.randint(1, 9))

        self.correct_result = ag_models.AutograderTestCaseResult(
            test_case=self.compilation_ag_test,
            compilation_standard_output=self.compiler_stdout,
            compilation_standard_error_output=self.compiler_stderr,
            compilation_return_code=0)

        self.incorrect_result = ag_models.AutograderTestCaseResult(
            test_case=self.compilation_ag_test,
            compilation_standard_output=self.compiler_stdout,
            compilation_standard_error_output=self.compiler_stderr,
            compilation_return_code=random.randint(1, 5))

    def test_no_fdbk(self):
        self.compilation_ag_test.feedback_configuration.validate_and_update(
            points_fdbk=fdbk_lvls.PointsFdbkLevel.show_breakdown)

        self.assertIsNone(self.correct_result.get_feedback().compilation_stdout)
        self.assertIsNone(self.correct_result.get_feedback().compilation_stderr)
        self.assertIsNone(self.correct_result.get_feedback().compilation_succeeded)

        self.assertIsNone(self.incorrect_result.get_feedback().compilation_stdout)
        self.assertIsNone(self.incorrect_result.get_feedback().compilation_stderr)
        self.assertIsNone(self.incorrect_result.get_feedback().compilation_succeeded)

        self.assertIsNone(self.correct_result.get_feedback().compilation_points)
        self.assertIsNone(
            self.correct_result.get_feedback().compilation_points_possible)

        self.assertIsNone(self.incorrect_result.get_feedback().compilation_points)
        self.assertIsNone(
            self.incorrect_result.get_feedback().compilation_points_possible)

    def test_success_or_failure_only(self):
        self.compilation_ag_test.feedback_configuration.validate_and_update(
            compilation_fdbk=(
                fdbk_lvls.CompilationFdbkLevel.success_or_failure_only))

        self.assertIsNone(self.correct_result.get_feedback().compilation_stdout)
        self.assertIsNone(self.correct_result.get_feedback().compilation_stderr)
        self.assertTrue(self.correct_result.get_feedback().compilation_succeeded)

        self.assertIsNone(self.incorrect_result.get_feedback().compilation_stdout)
        self.assertIsNone(self.incorrect_result.get_feedback().compilation_stderr)
        self.assertFalse(self.incorrect_result.get_feedback().compilation_succeeded)

        self._check_points_fdbk_shown_and_hidden()

    def test_show_compiler_output(self):
        self.compilation_ag_test.feedback_configuration.validate_and_update(
            compilation_fdbk=(
                fdbk_lvls.CompilationFdbkLevel.show_compiler_output))

        self.assertEqual(self.compiler_stdout,
                         self.correct_result.get_feedback().compilation_stdout)
        self.assertEqual(self.compiler_stderr,
                         self.correct_result.get_feedback().compilation_stderr)
        self.assertTrue(self.correct_result.get_feedback().compilation_succeeded)

        self.assertEqual(self.compiler_stdout,
                         self.incorrect_result.get_feedback().compilation_stdout)
        self.assertEqual(self.compiler_stderr,
                         self.incorrect_result.get_feedback().compilation_stderr)
        self.assertFalse(self.incorrect_result.get_feedback().compilation_succeeded)

        self._check_points_fdbk_shown_and_hidden()

    def test_fdbk_not_applicable_compilation_not_used(self):
        non_compiled_ag_test = _DummyAutograderTestCase.objects.validate_and_create(
            name='non_compiled_ag_test',
            project=self.project,
            points_for_compilation_success=random.randint(1, 6))
        result = ag_models.AutograderTestCaseResult(
            test_case=non_compiled_ag_test)

        non_compiled_ag_test.feedback_configuration.validate_and_update(
            compilation_fdbk=(
                fdbk_lvls.CompilationFdbkLevel.show_compiler_output))
        non_compiled_ag_test.feedback_configuration.validate_and_update(
            points_fdbk=fdbk_lvls.PointsFdbkLevel.show_breakdown)

        self.assertIsNone(result.get_feedback().compilation_stdout)
        self.assertIsNone(result.get_feedback().compilation_stderr)
        self.assertIsNone(result.get_feedback().compilation_succeeded)
        self.assertIsNone(result.get_feedback().compilation_points)
        self.assertIsNone(result.get_feedback().compilation_points_possible)

    def _check_points_fdbk_shown_and_hidden(self):
        self.compilation_ag_test.feedback_configuration.validate_and_update(
            points_fdbk=fdbk_lvls.PointsFdbkLevel.hide)
        # Hide points
        self.assertIsNone(self.correct_result.get_feedback().compilation_points)
        self.assertIsNone(
            self.correct_result.get_feedback().compilation_points_possible)

        self.assertIsNone(self.incorrect_result.get_feedback().compilation_points)
        self.assertIsNone(
            self.incorrect_result.get_feedback().compilation_points_possible)

        # Show points
        self.compilation_ag_test.feedback_configuration.validate_and_update(
            points_fdbk=fdbk_lvls.PointsFdbkLevel.show_breakdown)
        self.assertEqual(
            self.compilation_ag_test.points_for_compilation_success,
            self.correct_result.get_feedback().compilation_points)
        self.assertEqual(
            self.compilation_ag_test.points_for_compilation_success,
            self.correct_result.get_feedback().compilation_points_possible)

        self.assertEqual(0, self.incorrect_result.get_feedback().compilation_points)
        self.assertEqual(
            self.compilation_ag_test.points_for_compilation_success,
            self.incorrect_result.get_feedback().compilation_points_possible)
