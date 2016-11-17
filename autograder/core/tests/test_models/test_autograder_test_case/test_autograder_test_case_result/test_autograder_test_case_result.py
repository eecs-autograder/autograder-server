import datetime

from django.core.cache import cache
from django.utils import timezone

import autograder.core.models as ag_models
from autograder.core.models.autograder_test_case import feedback_config
import autograder.core.constants as const

import autograder.utils.testing as test_ut
import autograder.utils.testing.model_obj_builders as obj_build

from autograder.core.tests.test_models.test_autograder_test_case.models \
    import _DummyAutograderTestCase


class _SetUp:
    def setUp(self):
        super().setUp()

        self.closing_time = timezone.now() - datetime.timedelta(hours=1)

        group = obj_build.build_submission_group(
            project_kwargs={'closing_time': self.closing_time})
        self.project = group.project

        self.submission = ag_models.Submission.objects.validate_and_create(
            submission_group=group,
            submitted_files=[])

        self.test_name = 'my_test'
        self.test_case = _DummyAutograderTestCase.objects.validate_and_create(
            name=self.test_name,
            project=self.project)


class AGTestCaseResultFdbkGettersTestCase(_SetUp, test_ut.UnitTestBase):
    def setUp(self):
        super().setUp()

        self.result = ag_models.AutograderTestCaseResult.objects.create(
            test_case=self.test_case,
            submission=self.submission)

    def test_get_normal_feedback(self):
        fdbk = obj_build.random_fdbk()
        self.test_case.feedback_configuration = fdbk

        self.assertEqual(fdbk.to_dict(),
                         self.result.get_normal_feedback().fdbk_conf.to_dict())

    def test_get_ultimate_submission_feedback(self):
        fdbk = obj_build.random_fdbk()
        self.test_case.ultimate_submission_fdbk_conf = fdbk

        self.assertEqual(
            fdbk.to_dict(),
            self.result.get_ultimate_submission_feedback().fdbk_conf.to_dict())

    def test_get_staff_viewer_feedback(self):
        fdbk = obj_build.random_fdbk()
        self.test_case.staff_viewer_fdbk_conf = fdbk

        self.assertEqual(
            fdbk.to_dict(),
            self.result.get_staff_viewer_feedback().fdbk_conf.to_dict())

    def test_get_past_submission_limit_feedback(self):
        fdbk = obj_build.random_fdbk()
        self.test_case.past_submission_limit_fdbk_conf = fdbk

        self.assertEqual(
            fdbk.to_dict(),
            self.result.get_past_submission_limit_feedback().fdbk_conf.to_dict())

    def test_get_max_feedback(self):
        fdbk = ag_models.FeedbackConfig.create_with_max_fdbk()
        self.test_case.ultimate_submission_fdbk_conf = fdbk

        self.assertEqual(
            fdbk.to_dict(),
            self.result.get_max_feedback().fdbk_conf.to_dict())


class MiscAutograderTestCaseResultTestCase(_SetUp, test_ut.UnitTestBase):
    def test_default_init(self):
        result = ag_models.AutograderTestCaseResult.objects.create(
            test_case=self.test_case,
            submission=self.submission)

        result.refresh_from_db()

        self.assertEqual(result.test_case, self.test_case)
        self.assertIsNone(result.return_code)
        self.assertEqual(result.standard_output, '')
        self.assertEqual(result.standard_error_output, '')
        self.assertFalse(result.timed_out)
        self.assertIsNone(result.valgrind_return_code)
        self.assertEqual(result.valgrind_output, '')
        self.assertIsNone(result.compilation_return_code)
        self.assertEqual(result.compilation_standard_output, '')
        self.assertEqual(result.compilation_standard_error_output, '')

    def test_feedback_calculator_default_to_dict_fields(self):
        expected = [
            'ag_test_name',
            'return_code_correct',
            'expected_return_code',
            'actual_return_code',
            'return_code_points',
            'return_code_points_possible',

            'stdout_correct',
            'stdout_content',
            'stdout_diff',
            'stdout_points',
            'stdout_points_possible',

            'stderr_correct',
            'stderr_content',
            'stderr_diff',
            'stderr_points',
            'stderr_points_possible',

            'compilation_succeeded',
            'compilation_stdout',
            'compilation_stderr',
            'compilation_points',
            'compilation_points_possible',

            'valgrind_errors_reported',
            'valgrind_output',
            'valgrind_points_deducted',

            'total_points',
            'total_points_possible'
        ]

        self.assertCountEqual(
            expected,
            (ag_models.AutograderTestCaseResult
                      .FeedbackCalculator.get_default_to_dict_fields()))

    def test_to_dict_pk_included(self):
        result = ag_models.AutograderTestCaseResult.objects.create(
            test_case=self.test_case,
            submission=self.submission)

        fdbk = ag_models.AutograderTestCaseResult.FeedbackCalculator(
            result, self.test_case.feedback_configuration)
        self.assertIn('pk', fdbk.to_dict())

    def test_very_large_output_truncated(self):
        stdout = 'a' * 300000000
        stderr = 'b' * 300000000
        valgrind = 'c' * 300000000
        comp_stdout = 'd' * 300000000
        comp_stderr = 'e' * 300000000
        result = ag_models.AutograderTestCaseResult.objects.create(
            test_case=self.test_case,
            submission=self.submission,
            standard_output=stdout,
            standard_error_output=stderr,
            valgrind_output=valgrind,
            compilation_standard_output=comp_stdout,
            compilation_standard_error_output=comp_stderr)

        result.refresh_from_db()

        self.assertEqual(
            result.standard_output,
            stdout[:const.MAX_OUTPUT_LENGTH] + '\nOutput truncated')
        self.assertEqual(
            result.standard_error_output,
            stderr[:const.MAX_OUTPUT_LENGTH] + '\nOutput truncated')
        self.assertEqual(
            result.valgrind_output,
            valgrind[:const.MAX_OUTPUT_LENGTH] + '\nOutput truncated')
        self.assertEqual(
            result.compilation_standard_output,
            comp_stdout[:const.MAX_OUTPUT_LENGTH] + '\nOutput truncated')
        self.assertEqual(
            result.compilation_standard_error_output,
            comp_stderr[:const.MAX_OUTPUT_LENGTH] + '\nOutput truncated')


class TotalScoreTestCase(test_ut.UnitTestBase):
    def test_basic_score(self):
        cache.clear()
        result = obj_build.build_compiled_ag_test_result()

        self.assertEqual(0, result.basic_score)

        result.test_case.validate_and_update(
            feedback_configuration=(
                feedback_config.FeedbackConfig.create_with_max_fdbk()))

        # # Benchmarks
        # for i in range(10):
        #     cache.clear()
        #     with test_ut.Timer(msg='Result score from empty cache'):
        #         actual_score = result.basic_score

        # for i in range(10):
        #     with test_ut.Timer(msg='Result score from full cache'):
        #         actual_score = result.basic_score

        self.assertEqual(obj_build.build_compiled_ag_test.points_with_all_used,
                         result.basic_score)

    def test_cache_invalidation(self):
        results = []
        result = obj_build.build_compiled_ag_test_result()
        result.test_case.feedback_configuration = (
            feedback_config.FeedbackConfig.create_with_max_fdbk())
        results.append(result)

        test_case = result.test_case

        result = obj_build.build_compiled_ag_test_result(
            test_case=test_case)
        result.test_case.feedback_configuration = (
            feedback_config.FeedbackConfig.create_with_max_fdbk())
        results.append(result)

        self.assertEqual(results[0].test_case, results[1].test_case)

        for result in results:
            self.assertEqual(
                obj_build.build_compiled_ag_test.points_with_all_used,
                result.basic_score)

        test_case.points_for_correct_return_code += 1
        test_case.save()

        for result in results:
            self.assertEqual(
                obj_build.build_compiled_ag_test.points_with_all_used + 1,
                result.basic_score)

        test_case.feedback_configuration.validate_and_update(
            points_fdbk=feedback_config.PointsFdbkLevel.hide)

        for result in results:
            self.assertEqual(0, result.basic_score)

    def test_feedback_total_points_and_points_possible(self):
        result = obj_build.build_compiled_ag_test_result()

        # Both zero
        self.assertEqual(0, result.get_normal_feedback().total_points)
        self.assertEqual(0, result.get_normal_feedback().total_points_possible)

        self.assertEqual(obj_build.build_compiled_ag_test.points_with_all_used,
                         result.get_max_feedback().total_points)

        # Both full points
        expected_possible_points = (
            obj_build.build_compiled_ag_test.points_with_all_used +
            result.get_max_feedback().valgrind_points_deducted)

        self.assertEqual(expected_possible_points,
                         result.get_max_feedback().total_points_possible)

        # Points awarded less than points possible
        result.compilation_return_code = 42
        expected_total_points = (
            obj_build.build_compiled_ag_test.points_with_all_used -
            result.test_case.points_for_compilation_success)

        self.assertEqual(expected_possible_points,
                         result.get_max_feedback().total_points_possible)
        self.assertEqual(expected_total_points,
                         result.get_max_feedback().total_points)

    def test_feedback_total_points_does_not_go_negative(self):
        result = obj_build.build_compiled_ag_test_result()
        result.test_case.validate_and_update(
            deduction_for_valgrind_errors=(
                obj_build.build_compiled_ag_test.points_with_all_used * 2))

        self.assertEqual(0, result.get_max_feedback().total_points)
