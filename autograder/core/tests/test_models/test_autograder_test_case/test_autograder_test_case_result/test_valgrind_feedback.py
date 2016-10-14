import random
import string

import autograder.core.models as ag_models
import autograder.core.models.autograder_test_case.feedback_config as fdbk_lvls

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.tests.test_models.test_autograder_test_case.models \
    import _DummyCompiledAutograderTestCase


class ValgrindFdbkTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.project = obj_build.build_project()

        self.valgrind_output = (
            'memcheckererr ' + random.choice(string.ascii_letters))
        self.valgrind_ag_test = _DummyCompiledAutograderTestCase.objects.validate_and_create(
            name='valgrind_ag_test',
            project=self.project,
            compiler='g++',
            use_valgrind=True,
            deduction_for_valgrind_errors=random.randint(2, 5))

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
            self.correct_result.get_normal_feedback().valgrind_errors_reported)
        self.assertIsNone(self.correct_result.get_normal_feedback().valgrind_output)

        self.assertIsNone(
            self.incorrect_result.get_normal_feedback().valgrind_errors_reported)
        self.assertIsNone(self.incorrect_result.get_normal_feedback().valgrind_output)

        # Hide points
        self.assertIsNone(
            self.correct_result.get_normal_feedback().valgrind_points_deducted)
        self.assertIsNone(
            self.incorrect_result.get_normal_feedback().valgrind_points_deducted)

        # Show points set (but points still hidden)
        self.valgrind_ag_test.feedback_configuration.validate_and_update(
            points_fdbk=fdbk_lvls.PointsFdbkLevel.show_breakdown)
        self.assertIsNone(
            self.correct_result.get_normal_feedback().valgrind_points_deducted)
        self.assertIsNone(
            self.incorrect_result.get_normal_feedback().valgrind_points_deducted)

    def test_errors_or_no_errors_only(self):
        self.valgrind_ag_test.feedback_configuration.validate_and_update(
            valgrind_fdbk=fdbk_lvls.ValgrindFdbkLevel.errors_or_no_errors_only)

        self.assertFalse(
            self.correct_result.get_normal_feedback().valgrind_errors_reported)
        self.assertIsNone(self.correct_result.get_normal_feedback().valgrind_output)

        self.assertTrue(
            self.incorrect_result.get_normal_feedback().valgrind_errors_reported)
        self.assertIsNone(self.incorrect_result.get_normal_feedback().valgrind_output)

        self._check_points_shown_and_hidden()

    def test_show_valgrind_output(self):
        self.valgrind_ag_test.feedback_configuration.validate_and_update(
            valgrind_fdbk=fdbk_lvls.ValgrindFdbkLevel.show_valgrind_output)

        self.assertFalse(
            self.correct_result.get_normal_feedback().valgrind_errors_reported)
        self.assertEqual(self.valgrind_output,
                         self.correct_result.get_normal_feedback().valgrind_output)

        self.assertTrue(
            self.incorrect_result.get_normal_feedback().valgrind_errors_reported)
        self.assertEqual(self.valgrind_output,
                         self.incorrect_result.get_normal_feedback().valgrind_output)

        self._check_points_shown_and_hidden()

    def test_fdbk_not_applicable_valgrind_not_used(self):
        no_valgrind_test = _DummyCompiledAutograderTestCase.objects.validate_and_create(
            name='no_valgrind_test',
            project=self.project,
            compiler='g++',
            deduction_for_valgrind_errors=42)
        result = ag_models.AutograderTestCaseResult(test_case=no_valgrind_test)

        self.assertIsNone(
            result.get_normal_feedback().valgrind_errors_reported)
        self.assertIsNone(result.get_normal_feedback().valgrind_output)
        self.assertIsNone(result.get_normal_feedback().valgrind_points_deducted)

    def _check_points_shown_and_hidden(self):
        # Hide points
        self.assertIsNone(
            self.correct_result.get_normal_feedback().valgrind_points_deducted)
        self.assertIsNone(
            self.incorrect_result.get_normal_feedback().valgrind_points_deducted)

        # Show points
        self.valgrind_ag_test.feedback_configuration.validate_and_update(
            points_fdbk=fdbk_lvls.PointsFdbkLevel.show_breakdown)
        self.assertEqual(
            0,
            self.correct_result.get_normal_feedback().valgrind_points_deducted)
        self.assertEqual(
            self.valgrind_ag_test.deduction_for_valgrind_errors,
            self.incorrect_result.get_normal_feedback().valgrind_points_deducted)
