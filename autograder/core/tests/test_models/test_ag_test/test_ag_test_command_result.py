import datetime
from unittest import mock

from django.db.utils import IntegrityError
from django.core.cache import cache
from django.utils import timezone

import autograder.core.models as ag_models
from autograder.core.models.autograder_test_case import feedback_config
import autograder.core.constants as constants

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class AGTestCommandResultTestCase(UnitTestBase):
    def setUp(self):
        # create an ag_test_command where normal feedback is set to max
        submission = obj_build.build_submission()
        project = submission.submission_group.project
        suite = ag_models.AGTestSuite.objects.validate_and_create(name='kajsdhf', project=project)
        self.ag_test_case = ag_models.AGTestCase.objects.validate_and_create(
            name='aksdbva', ag_test_suite=suite)
        suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            submission=submission, ag_test_suite=suite)
        self.ag_test_case_result = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=self.ag_test_case, ag_test_suite_result=suite_result)

        self.ag_test_command = ag_models.AGTestCommand.objects.validate_and_create(
            name='madsnbvihq',
            ag_test_case=self.ag_test_case,
            cmd='aksdjhfalsdf',

            # These specific values don't matter, other than that
            # they should indicate that return code, stdout, and
            # stderr are checked. We'll be manually setting the
            # correctness fields on AGTestCommandResults.
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stderr_source=ag_models.ExpectedOutputSource.text,

            points_for_correct_return_code=1,
            points_for_correct_stdout=2,
            points_for_correct_stderr=3,
            deduction_for_wrong_return_code=-4,
            deduction_for_wrong_stdout=-2,
            deduction_for_wrong_stderr=-1
        )
        self.max_points_possible = 6
        self.min_points_possible = -7

    def test_feedback_calculator_named_ctors(self):
        # check against the actual objects (their pks)
        self.fail()

    def test_points_everything_correct_max_fdbk(self):
        cmd_result = ag_models.AGTestCommandResult.objects.validate_and_create(
            ag_test_command=self.ag_test_command,
            ag_test_case_result=self.ag_test_case_result,
            return_code=0,

            return_code_correct=True,
            stdout_correct=True,
            stderr_correct=True
        )
        fdbk = cmd_result.get_max_feedback()

        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points_possible)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points_possible)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points_possible)

        self.assertEqual(self.max_points_possible, fdbk.total_points)
        self.assertEqual(self.max_points_possible, fdbk.total_points_possible)

    def test_points_everything_incorrect_max_fdbk(self):
        cmd_result = ag_models.AGTestCommandResult.objects.validate_and_create(
            ag_test_command=self.ag_test_command,
            ag_test_case_result=self.ag_test_case_result,
            return_code=0,

            return_code_correct=False,
            stdout_correct=False,
            stderr_correct=False
        )
        fdbk = cmd_result.get_max_feedback()

        self.assertEqual(self.ag_test_command.deduction_for_wrong_return_code,
                         fdbk.return_code_points)
        self.assertEqual(self.ag_test_command.points_for_correct_return_code,
                         fdbk.return_code_points_possible)
        self.assertEqual(self.ag_test_command.deduction_for_wrong_stdout,
                         fdbk.stdout_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stdout,
                         fdbk.stdout_points_possible)
        self.assertEqual(self.ag_test_command.deduction_for_wrong_stderr,
                         fdbk.stderr_points)
        self.assertEqual(self.ag_test_command.points_for_correct_stderr,
                         fdbk.stderr_points_possible)

        self.assertEqual(self.min_points_possible, fdbk.total_points)
        self.assertEqual(self.max_points_possible, fdbk.total_points_possible)

    def test_points_return_code_not_checked(self):
        self.ag_test_command.validate_and_update(
            expected_return_code=ag_models.ExpectedReturnCode.none)

        correct_cmd_result = ag_models.AGTestCommandResult.objects.validate_and_create(
            ag_test_command=self.ag_test_command,
            ag_test_case_result=self.ag_test_case_result,
            return_code=0,
            return_code_correct=True)
        self.assertEqual(0, correct_cmd_result.get_max_feedback().return_code_points)
        self.assertEqual(0, correct_cmd_result.get_max_feedback().return_code_points_possible)

        correct_cmd_result.delete()

        incorrect_cmd_result = ag_models.AGTestCommandResult.objects.validate_and_create(
            ag_test_command=self.ag_test_command,
            ag_test_case_result=self.ag_test_case_result,
            return_code=0,
            return_code_correct=False)
        self.assertEqual(0, incorrect_cmd_result.get_max_feedback().return_code_points)
        self.assertEqual(0, incorrect_cmd_result.get_max_feedback().return_code_points_possible)

    def test_points_stdout_not_checked(self):
        self.ag_test_command.validate_and_update(
            expected_stdout_source=ag_models.ExpectedOutputSource.none)

        correct_cmd_result = ag_models.AGTestCommandResult.objects.validate_and_create(
            ag_test_command=self.ag_test_command,
            ag_test_case_result=self.ag_test_case_result,
            return_code=0,
            stdout_correct=True)
        self.assertEqual(0, correct_cmd_result.get_max_feedback().stdout_points)
        self.assertEqual(0, correct_cmd_result.get_max_feedback().stdout_points_possible)

        correct_cmd_result.delete()

        incorrect_cmd_result = ag_models.AGTestCommandResult.objects.validate_and_create(
            ag_test_command=self.ag_test_command,
            ag_test_case_result=self.ag_test_case_result,
            return_code=0,
            stdout_correct=False)
        self.assertEqual(0, incorrect_cmd_result.get_max_feedback().stdout_points)
        self.assertEqual(0, incorrect_cmd_result.get_max_feedback().stdout_points_possible)

    def test_points_stderr_not_checked(self):
        self.ag_test_command.validate_and_update(
            expected_stderr_source=ag_models.ExpectedOutputSource.none)

        correct_cmd_result = ag_models.AGTestCommandResult.objects.validate_and_create(
            ag_test_command=self.ag_test_command,
            ag_test_case_result=self.ag_test_case_result,
            return_code=0,
            stderr_correct=True)
        self.assertEqual(0, correct_cmd_result.get_max_feedback().stderr_points)
        self.assertEqual(0, correct_cmd_result.get_max_feedback().stderr_points_possible)

        correct_cmd_result.delete()

        incorrect_cmd_result = ag_models.AGTestCommandResult.objects.validate_and_create(
            ag_test_command=self.ag_test_command,
            ag_test_case_result=self.ag_test_case_result,
            return_code=0,
            stderr_correct=False)
        self.assertEqual(0, incorrect_cmd_result.get_max_feedback().stderr_points)
        self.assertEqual(0, incorrect_cmd_result.get_max_feedback().stderr_points_possible)

    def test_return_code_correctness_visibility(self):
        # hidden
        #   - no points or deductions shown
        # correct or incorrect
        #   - points and correctness but no expected and actual
        # expected and actual
        #   - points, correctness, and expected and actual

        self.fail()

    def test_return_code_visibility(self):
        # hidden and visible, shouldn't affect points
        self.fail()

    def test_timed_out_visibility(self):
        # hidden and visible, shouldn't affect points
        self.fail()

    def test_stdout_correctness_visibility(self):
        # hidden
        #   - no points or deductions shown
        # correct or incorrect
        #   - points and correctness but no expected and actual
        # expected and actual
        #   - points, correctness, and expected and actual
        self.fail()

    def test_stdout_visibility(self):
        # hidden and visible, shouldn't affect points
        self.fail()

    def test_stderr_correctness_visibility(self):
        # hidden
        #   - no points or deductions shown
        # correct or incorrect
        #   - points and correctness but no expected and actual
        # expected and actual
        #   - points, correctness, and expected and actual
        self.fail()

    def test_stderr_visibility(self):
        # hidden and visible, shouldn't affect points
        self.fail()

    def test_points_visibility(self):
        # hidden and visible, should affect points but nothing else
        self.fail()

    def test_very_large_output_truncated(self):
        stdout = 'a' * 3000000000
        stderr = 'b' * 3000000000

        cmd_result = ag_models.AGTestCommandResult.objects.validate_and_create(
            ag_test_command=self.ag_test_command,
            ag_test_case_result=self.ag_test_case_result,
            return_code=0,
            stdout=stdout,
            stderr=stderr
        )

        self.assertEqual(
            cmd_result.stdout,
            stdout[:constants.MAX_OUTPUT_LENGTH] + '\nOutput truncated')
        self.assertEqual(
            cmd_result.stderr,
            stderr[:constants.MAX_OUTPUT_LENGTH] + '\nOutput truncated')

#
# class _SetUp(test_ut.UnitTestBase):
#     def setUp(self):
#         super().setUp()
#
#         self.closing_time = timezone.now() - datetime.timedelta(hours=1)
#
#         group = obj_build.build_submission_group(
#             project_kwargs={'closing_time': self.closing_time})
#         self.project = group.project
#
#         self.test_name = 'my_test'
#         self.test_case = _DummyAutograderTestCase.objects.validate_and_create(
#             name=self.test_name, project=self.project)
#
#         self.submission = ag_models.Submission.objects.validate_and_create(
#             submission_group=group,
#             submitted_files=[])


# class AGTestCaseResultFdbkGettersTestCase(_SetUp):
#     def setUp(self):
#         super().setUp()
#
#         self.result = ag_models.AutograderTestCaseResult.objects.get(
#             test_case=self.test_case,
#             submission=self.submission)
#
#     def test_get_normal_feedback(self):
#         fdbk = obj_build.random_fdbk()
#         self.test_case.validate_and_update(feedback_configuration=fdbk)
#
#         self.assertEqual(fdbk.to_dict(),
#                          self.result.get_normal_feedback().fdbk_conf.to_dict())
#
#     def test_get_ultimate_submission_feedback(self):
#         fdbk = obj_build.random_fdbk()
#         self.test_case.validate_and_update(ultimate_submission_fdbk_conf=fdbk)
#
#         self.assertEqual(
#             fdbk.to_dict(),
#             self.result.get_ultimate_submission_feedback().fdbk_conf.to_dict())
#
#     def test_get_staff_viewer_feedback(self):
#         fdbk = obj_build.random_fdbk()
#         self.test_case.validate_and_update(staff_viewer_fdbk_conf=fdbk)
#
#         self.assertEqual(
#             fdbk.to_dict(),
#             self.result.get_staff_viewer_feedback().fdbk_conf.to_dict())
#
#     def test_get_past_submission_limit_feedback(self):
#         fdbk = obj_build.random_fdbk()
#         self.test_case.validate_and_update(past_submission_limit_fdbk_conf=fdbk)
#
#         self.assertEqual(
#             fdbk.to_dict(),
#             self.result.get_past_submission_limit_feedback().fdbk_conf.to_dict())
#
#     def test_get_max_feedback(self):
#         fdbk = ag_models.FeedbackConfig.create_with_max_fdbk()
#         self.test_case.validate_and_update(ultimate_submission_fdbk_conf=fdbk)
#
#         self.assertEqual(
#             fdbk.to_dict(),
#             self.result.get_max_feedback().fdbk_conf.to_dict())
#

# class MiscAGTestResultTestCase(_SetUp):
#     def test_default_init(self):
#         self.fail()
#         result = ag_models.AutograderTestCaseResult.objects.get(
#             test_case=self.test_case,
#             submission=self.submission)
#
#         self.assertEqual(result.test_case, self.test_case)
#         self.assertEqual(result.submission, self.submission)
#         self.assertEqual(
#             result.status,
#             ag_models.AutograderTestCaseResult.ResultStatus.pending)
#         self.assertEqual('', result.error_msg)
#
#         self.assertIsNone(result.return_code)
#         self.assertEqual(result.stdout, '')
#         self.assertEqual(result.stderr, '')
#         self.assertFalse(result.timed_out)
#
#     def test_invalid_create_duplicate(self):
#         with self.assertRaises(IntegrityError):
#             ag_models.AutograderTestCaseResult.objects.create(
#                 test_case=self.test_case,
#                 submission=self.submission)
#
#     def test_very_large_output_truncated(self):
#         stdout = 'a' * 300000000
#         stderr = 'b' * 300000000
#         valgrind = 'c' * 300000000
#         comp_stdout = 'd' * 300000000
#         comp_stderr = 'e' * 300000000
#
#         result = ag_models.AutograderTestCaseResult.objects.get(
#             test_case=self.test_case,
#             submission=self.submission)
#
#         result.standard_output = stdout
#         result.standard_error_output = stderr
#         result.valgrind_output = valgrind
#         result.compilation_standard_output = comp_stdout
#         result.compilation_standard_error_output = comp_stderr
#         result.save()
#
#         self.assertEqual(
#             result.standard_output,
#             stdout[:constants.MAX_OUTPUT_LENGTH] + '\nOutput truncated')
#         self.assertEqual(
#             result.standard_error_output,
#             stderr[:constants.MAX_OUTPUT_LENGTH] + '\nOutput truncated')
#         self.assertEqual(
#             result.valgrind_output,
#             valgrind[:constants.MAX_OUTPUT_LENGTH] + '\nOutput truncated')
#         self.assertEqual(
#             result.compilation_standard_output,
#             comp_stdout[:constants.MAX_OUTPUT_LENGTH] + '\nOutput truncated')
#         self.assertEqual(
#             result.compilation_standard_error_output,
#             comp_stderr[:constants.MAX_OUTPUT_LENGTH] + '\nOutput truncated')

#
# class FlexibleOutputDiffTestCase(_SetUp):
#     def test_all_diff_options_false_stdout_correct_stderr_incorrect(self):
#         self.do_diff_options_test(
#             expected_stdout='spam', actual_stdout='spam',
#             expected_stderr='yes', actual_stderr='no',
#             expect_stdout_correct=True,
#             expect_stderr_correct=False,
#             **self._get_diff_options(False))
#
#     def test_all_diff_options_false_stderr_correct_stdout_incorrect(self):
#         self.do_diff_options_test(
#             expected_stdout='yes', actual_stdout='no',
#             expected_stderr='egg', actual_stderr='egg',
#             expect_stdout_correct=False,
#             expect_stderr_correct=True,
#             **self._get_diff_options(False))
#
#     def test_all_diff_options_true_stdout_correct_stderr_incorrect(self):
#         self.do_diff_options_test(
#             expected_stdout='SPAM', actual_stdout='spam',
#             expected_stderr='yes', actual_stderr='no',
#             expect_stdout_correct=True,
#             expect_stderr_correct=False,
#             **self._get_diff_options(True))
#
#     def test_all_diff_options_true_stderr_correct_stdout_incorrect(self):
#         self.do_diff_options_test(
#             expected_stdout='yes', actual_stdout='no',
#             expected_stderr='egg', actual_stderr='EGG',
#             expect_stdout_correct=False,
#             expect_stderr_correct=True,
#             **self._get_diff_options(True))
#
#     def do_diff_options_test(self, expected_stdout='', actual_stdout='',
#                              expected_stderr='', actual_stderr='',
#                              expect_stdout_correct=True,
#                              expect_stderr_correct=True,
#                              **diff_options):
#         self.test_case.validate_and_update(
#             expected_standard_output=expected_stdout,
#             expected_standard_error_output=expected_stderr,
#             **diff_options)
#
#         result_queryset = ag_models.AutograderTestCaseResult.objects.filter(
#             test_case=self.test_case, submission=self.submission)
#         result_queryset.update(
#             standard_output=actual_stdout, standard_error_output=actual_stderr)
#         result = result_queryset.get()
#
#         mock_path = 'autograder.core.utils.get_diff'
#         with mock.patch(mock_path) as mock_differ_cls:
#             result.get_max_feedback().stdout_diff
#             mock_differ_cls.assert_called_with(expected_stdout, actual_stdout,
#                                                **diff_options)
#
#         with mock.patch(mock_path) as mock_differ_cls:
#             result.get_max_feedback().stderr_diff
#             mock_differ_cls.assert_called_with(expected_stderr, actual_stderr,
#                                                **diff_options)
#
#         if expect_stdout_correct:
#             self.assertEqual([], result.get_max_feedback().stdout_diff)
#         else:
#             self.assertNotEqual([], result.get_max_feedback().stdout_diff)
#
#         self.assertEqual(expect_stdout_correct,
#                          result.get_max_feedback().stdout_correct)
#
#         if expect_stderr_correct:
#             self.assertEqual([], result.get_max_feedback().stderr_diff)
#         else:
#             self.assertNotEqual([], result.get_max_feedback().stderr_diff)
#
#         self.assertEqual(expect_stderr_correct,
#                          result.get_max_feedback().stderr_correct)
#
#     def _get_diff_options(self, options_value):
#         return {
#             'ignore_case': options_value,
#             'ignore_whitespace': options_value,
#             'ignore_whitespace_changes': options_value,
#             'ignore_blank_lines': options_value
#         }
