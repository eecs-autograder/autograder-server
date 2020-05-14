import os

import autograder.core.models as ag_models
from autograder.core.tests.test_submission_feedback.fdbk_getter_shortcuts import (
    get_suite_fdbk, get_case_fdbk, get_cmd_fdbk)
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build

import autograder.core.utils as core_ut


class AGTestSuiteFeedbackTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None
        submission = obj_build.make_submission()
        project = submission.group.project
        self.ag_test_suite = ag_models.AGTestSuite.objects.validate_and_create(
            name='kajsdhf', project=project,
            setup_suite_cmd_name='asdlkjfa;skldjf;aksdf'
        )  # type: ag_models.AGTestSuite

        self.ag_test_case1 = ag_models.AGTestCase.objects.validate_and_create(
            name='aksdbva', ag_test_suite=self.ag_test_suite
        )  # type: ag_models.AGTestCase
        self.ag_test_case2 = ag_models.AGTestCase.objects.validate_and_create(
            name='ndkaadjhfa', ag_test_suite=self.ag_test_suite,
        )  # type: ag_models.AGTestCase

        self.ag_test_cmd1 = obj_build.make_full_ag_test_command(
            self.ag_test_case1, set_arbitrary_points=False,
            points_for_correct_return_code=4)
        self.ag_test_cmd2 = obj_build.make_full_ag_test_command(
            self.ag_test_case2, set_arbitrary_points=False,
            points_for_correct_return_code=5)
        self.total_points = 9

        self.ag_test_suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            submission=submission, ag_test_suite=self.ag_test_suite
        )  # type: ag_models.AGTestSuiteResult

        self.ag_test_case_result1 = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=self.ag_test_case1, ag_test_suite_result=self.ag_test_suite_result
        )  # type: ag_models.AGTestCaseResult
        self.ag_test_case_result2 = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=self.ag_test_case2, ag_test_suite_result=self.ag_test_suite_result
        )  # type: ag_models.AGTestCaseResult

        self.cmd_result1 = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd1, self.ag_test_case_result1)
        self.cmd_result2 = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd2, self.ag_test_case_result2)

    def test_ag_test_case_result_ordering(self):
        for i in range(2):
            self.ag_test_suite.set_agtestcase_order([self.ag_test_case2.pk, self.ag_test_case1.pk])
            fdbk = get_suite_fdbk(self.ag_test_suite_result, ag_models.FeedbackCategory.max)
            print(fdbk)
            self.assertSequenceEqual([self.ag_test_case_result2.pk, self.ag_test_case_result1.pk],
                                     [res.pk for res in fdbk.ag_test_case_results])

            self.ag_test_suite.set_agtestcase_order([self.ag_test_case1.pk, self.ag_test_case2.pk])
            fdbk = get_suite_fdbk(self.ag_test_suite_result, ag_models.FeedbackCategory.max)
            self.assertSequenceEqual([self.ag_test_case_result1.pk, self.ag_test_case_result2.pk],
                                     [res.pk for res in fdbk.ag_test_case_results])

    def test_output_filenames(self):
        expected_setup_stdout_filename = os.path.join(
            core_ut.get_result_output_dir(self.ag_test_suite_result.submission),
            'suite_result_' + str(self.ag_test_suite_result.pk) + '_setup_stdout')
        self.assertEqual(expected_setup_stdout_filename,
                         self.ag_test_suite_result.setup_stdout_filename)

        expected_setup_stderr_filename = os.path.join(
            core_ut.get_result_output_dir(self.ag_test_suite_result.submission),
            'suite_result_' + str(self.ag_test_suite_result.pk) + '_setup_stderr')
        self.assertEqual(expected_setup_stderr_filename,
                         self.ag_test_suite_result.setup_stderr_filename)

    def test_feedback_calculator_ctor(self):
        self.assertEqual(
            self.ag_test_suite.normal_fdbk_config.to_dict(),
            get_suite_fdbk(self.ag_test_suite_result,
                           ag_models.FeedbackCategory.normal).fdbk_conf.to_dict())
        self.assertEqual(
            self.ag_test_suite.ultimate_submission_fdbk_config.to_dict(),
            get_suite_fdbk(self.ag_test_suite_result,
                           ag_models.FeedbackCategory.ultimate_submission).fdbk_conf.to_dict())
        self.assertEqual(
            self.ag_test_suite.past_limit_submission_fdbk_config.to_dict(),
            get_suite_fdbk(self.ag_test_suite_result,
                           ag_models.FeedbackCategory.past_limit_submission).fdbk_conf.to_dict())
        self.assertEqual(
            self.ag_test_suite.staff_viewer_fdbk_config.to_dict(),
            get_suite_fdbk(self.ag_test_suite_result,
                           ag_models.FeedbackCategory.staff_viewer).fdbk_conf.to_dict())

        max_config = get_suite_fdbk(
            self.ag_test_suite_result, ag_models.FeedbackCategory.max).fdbk_conf
        self.assertTrue(max_config.show_individual_tests)
        self.assertTrue(max_config.show_setup_stdout)
        self.assertTrue(max_config.show_setup_stderr)

    def test_points_max_fdbk(self):
        fdbk = get_suite_fdbk(self.ag_test_suite_result, ag_models.FeedbackCategory.max)
        self.assertEqual(self.total_points, fdbk.total_points)
        self.assertEqual(self.total_points, fdbk.total_points_possible)

    def test_points_minimum_ag_test_command_fdbk(self):
        fdbk = get_suite_fdbk(self.ag_test_suite_result, ag_models.FeedbackCategory.normal)
        self.assertEqual(0, fdbk.total_points)
        self.assertEqual(0, fdbk.total_points_possible)

    def test_show_individual_tests(self):
        self.ag_test_cmd1.validate_and_update(
            normal_fdbk_config={
                'return_code_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'show_points': True
            }
        )

        self.ag_test_cmd2.validate_and_update(
            normal_fdbk_config={
                'return_code_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'show_points': True
            }
        )

        self.assertTrue(self.ag_test_suite.normal_fdbk_config.show_individual_tests)
        fdbk = get_suite_fdbk(self.ag_test_suite_result, ag_models.FeedbackCategory.normal)
        self.assertEqual(
            [self.ag_test_case_result1.pk, self.ag_test_case_result2.pk],
            [res.pk for res in fdbk.ag_test_case_results])
        self.assertEqual(self.total_points, fdbk.total_points)
        self.assertEqual(self.total_points, fdbk.total_points_possible)

        self.ag_test_suite.validate_and_update(
            normal_fdbk_config={'show_individual_tests': False})
        fdbk = get_suite_fdbk(self.ag_test_suite_result, ag_models.FeedbackCategory.normal)
        self.assertEqual([], fdbk.ag_test_case_results)
        self.assertEqual(self.total_points, fdbk.total_points)
        self.assertEqual(self.total_points, fdbk.total_points_possible)

    def test_individual_test_result_order(self):
        self.ag_test_suite.set_agtestcase_order([self.ag_test_case2.pk, self.ag_test_case1.pk])
        fdbk = get_suite_fdbk(self.ag_test_suite_result, ag_models.FeedbackCategory.max)
        self.assertEqual([self.ag_test_case_result2.pk, self.ag_test_case_result1.pk],
                         [res.pk for res in fdbk.ag_test_case_results])

    def test_show_setup_output_return_code_and_timed_out(self):
        setup_return_code = 3
        setup_timed_out = True
        setup_stdout = 'adfjka;dskjf'
        setup_stderr = 'a,xcmvnaieo;sdf'

        self.ag_test_suite_result.setup_return_code = setup_return_code
        self.ag_test_suite_result.setup_timed_out = setup_timed_out
        with self.ag_test_suite_result.open_setup_stdout('w') as f:
            f.write(setup_stdout)
        with self.ag_test_suite_result.open_setup_stderr('w') as f:
            f.write(setup_stderr)
        self.ag_test_suite_result.save()

        self.ag_test_suite_result.setup_stdout_truncated = True
        fdbk = get_suite_fdbk(self.ag_test_suite_result, ag_models.FeedbackCategory.max)
        self.assertEqual(self.ag_test_suite.setup_suite_cmd_name, fdbk.setup_name)
        self.assertEqual(setup_return_code, fdbk.setup_return_code)
        self.assertEqual(setup_timed_out, fdbk.setup_timed_out)
        self.assertEqual(setup_stdout, fdbk.setup_stdout.read().decode())
        self.assertEqual(len(setup_stdout), fdbk.get_setup_stdout_size())
        self.assertEqual(setup_stderr, fdbk.setup_stderr.read().decode())
        self.assertEqual(len(setup_stderr), fdbk.get_setup_stderr_size())
        self.assertTrue(fdbk.setup_stdout_truncated)
        self.assertFalse(fdbk.setup_stderr_truncated)

        self.ag_test_suite.validate_and_update(
            normal_fdbk_config={
                'show_setup_return_code': False,
                'show_setup_timed_out': False,
                'show_setup_stdout': False,
                'show_setup_stderr': False
            }
        )

        fdbk = get_suite_fdbk(self.ag_test_suite_result, ag_models.FeedbackCategory.normal)
        self.assertIsNone(fdbk.setup_name)
        self.assertIsNone(fdbk.setup_return_code)
        self.assertIsNone(fdbk.setup_timed_out)
        self.assertIsNone(fdbk.setup_stdout)
        self.assertIsNone(fdbk.get_setup_stdout_size())
        self.assertIsNone(fdbk.setup_stderr)
        self.assertIsNone(fdbk.get_setup_stderr_size())
        self.assertIsNone(fdbk.setup_stdout_truncated)
        self.assertIsNone(fdbk.setup_stderr_truncated)

    def test_show_setup_name_with_return_code_non_null_and_timed_out_false(self) -> None:
        self.ag_test_suite.validate_and_update(
            normal_fdbk_config={
                'show_setup_return_code': False,
                'show_setup_timed_out': False,
                'show_setup_stdout': False,
                'show_setup_stderr': True,
            }
        )

        self.ag_test_suite_result.setup_return_code = 42
        self.ag_test_suite_result.setup_timed_out = False
        self.ag_test_suite_result.save()

        fdbk = get_suite_fdbk(self.ag_test_suite_result, ag_models.FeedbackCategory.normal)
        self.assertEqual(self.ag_test_suite.setup_suite_cmd_name, fdbk.setup_name)

    def test_show_setup_name_with_return_code_null_and_timed_out_true(self) -> None:
        self.ag_test_suite.validate_and_update(
            normal_fdbk_config={
                'show_setup_return_code': False,
                'show_setup_timed_out': False,
                'show_setup_stdout': True,
                'show_setup_stderr': False,
            }
        )

        self.ag_test_suite_result.setup_return_code = None
        self.ag_test_suite_result.setup_timed_out = True
        self.ag_test_suite_result.save()

        fdbk = get_suite_fdbk(self.ag_test_suite_result, ag_models.FeedbackCategory.normal)
        self.assertEqual(self.ag_test_suite.setup_suite_cmd_name, fdbk.setup_name)

    def test_show_setup_name_with_return_code_null_and_timed_out_false(self) -> None:
        self.ag_test_suite_result.setup_return_code = None
        self.ag_test_suite_result.setup_timed_out = False
        self.ag_test_suite_result.save()

        fdbk = get_suite_fdbk(self.ag_test_suite_result, ag_models.FeedbackCategory.max)
        self.assertIsNone(fdbk.setup_name)

    def test_some_ag_test_cases_not_visible(self):
        self.ag_test_case2.validate_and_update(ultimate_submission_fdbk_config={'visible': False})
        expected_points = get_cmd_fdbk(
            self.cmd_result1, ag_models.FeedbackCategory.max).total_points_possible

        fdbk = get_suite_fdbk(self.ag_test_suite_result,
                              ag_models.FeedbackCategory.ultimate_submission)
        self.assertSequenceEqual([self.ag_test_case_result1.pk],
                                 [res.pk for res in fdbk.ag_test_case_results])
        self.assertEqual(expected_points, fdbk.total_points)
        self.assertEqual(expected_points, fdbk.total_points_possible)

    def test_fdbk_to_dict(self):
        self.ag_test_case1.validate_and_update(
            normal_fdbk_config={'show_individual_commands': False})

        expected_keys = [
            'pk',
            'ag_test_suite_name',
            'ag_test_suite_pk',
            'fdbk_settings',
            'setup_name',
            'setup_return_code',
            'setup_timed_out',
            'total_points',
            'total_points_possible',
            'ag_test_case_results',
        ]

        for fdbk_category in ag_models.FeedbackCategory:
            result_dict = get_suite_fdbk(self.ag_test_suite_result, fdbk_category).to_dict()
            self.assertCountEqual(expected_keys, result_dict.keys())

            self.assertCountEqual(
                [get_case_fdbk(self.ag_test_case_result1, fdbk_category).to_dict(),
                 get_case_fdbk(self.ag_test_case_result2, fdbk_category).to_dict()],
                result_dict['ag_test_case_results'])


class FirstFailedTestFeedbackTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        submission = obj_build.make_submission()
        self.project = submission.group.project

        self.ag_suite1 = ag_models.AGTestSuite.objects.validate_and_create(
            name='kajsdhf', project=self.project)

        self.ag_suite1_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            submission=submission, ag_test_suite=self.ag_suite1)

        self.ag_test_case1 = ag_models.AGTestCase.objects.validate_and_create(
            name='aksdbva', ag_test_suite=self.ag_suite1)
        self.ag_test_case2 = ag_models.AGTestCase.objects.validate_and_create(
            name='noniresta', ag_test_suite=self.ag_suite1)
        self.ag_test_case3 = ag_models.AGTestCase.objects.validate_and_create(
            name='eaoneastno', ag_test_suite=self.ag_suite1)

        self.ag_test_case1_correct_result = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=self.ag_test_case1, ag_test_suite_result=self.ag_suite1_result)
        self.ag_test_case2_incorrect_result = (
            ag_models.AGTestCaseResult.objects.validate_and_create(
                ag_test_case=self.ag_test_case2, ag_test_suite_result=self.ag_suite1_result)
        )
        self.ag_test_case3_incorrect_result = (
            ag_models.AGTestCaseResult.objects.validate_and_create(
                ag_test_case=self.ag_test_case3, ag_test_suite_result=self.ag_suite1_result)
        )

        self.ag_test_case1_cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case1,
            normal_fdbk_config={
                'return_code_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'show_points': True
            },
            first_failed_test_normal_fdbk_config=(
                ag_models.AGTestCommandFeedbackConfig.max_fdbk_config())
        )
        self.total_points_possible = (self.ag_test_case1_cmd.points_for_correct_return_code
                                      + self.ag_test_case1_cmd.points_for_correct_stdout
                                      + self.ag_test_case1_cmd.points_for_correct_stderr)

        self.ag_test_case2_cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case2,
            normal_fdbk_config={
                'return_code_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'show_points': True
            },
            first_failed_test_normal_fdbk_config=(
                ag_models.AGTestCommandFeedbackConfig.max_fdbk_config())
        )

        self.ag_test_case3_cmd = obj_build.make_full_ag_test_command(
            self.ag_test_case3,
            normal_fdbk_config={
                'return_code_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'show_points': True
            },
            first_failed_test_normal_fdbk_config=(
                ag_models.AGTestCommandFeedbackConfig.max_fdbk_config())
        )

        self.case1_cmd_res = obj_build.make_correct_ag_test_command_result(
            self.ag_test_case1_cmd, ag_test_case_result=self.ag_test_case1_correct_result)

        self.case2_cmd_res = obj_build.make_incorrect_ag_test_command_result(
            self.ag_test_case2_cmd, ag_test_case_result=self.ag_test_case2_incorrect_result)

        self.case3_cmd_res = obj_build.make_incorrect_ag_test_command_result(
            self.ag_test_case3_cmd, ag_test_case_result=self.ag_test_case3_incorrect_result)

        max_fdbk = get_suite_fdbk(self.ag_suite1_result, ag_models.FeedbackCategory.max)
        self.assertEqual(self.total_points_possible, max_fdbk.total_points)
        self.assertEqual(self.total_points_possible * 3, max_fdbk.total_points_possible)

    def test_first_failed_test_gets_overriden_normal_feedback(self):
        fdbk = get_suite_fdbk(self.ag_suite1_result, ag_models.FeedbackCategory.normal)

        expected_case_fdbks = [
            get_case_fdbk(
                self.ag_test_case1_correct_result, ag_models.FeedbackCategory.normal).to_dict(),
            get_case_fdbk(
                self.ag_test_case2_incorrect_result, ag_models.FeedbackCategory.normal,
                is_first_failure=True).to_dict(),
            get_case_fdbk(
                self.ag_test_case3_incorrect_result, ag_models.FeedbackCategory.normal).to_dict()
        ]

        self.assertEqual(expected_case_fdbks,
                         [case_fdbk.to_dict() for case_fdbk in fdbk.ag_test_case_results])

    def test_no_failed_tests_all_get_normal_fdbk(self):
        self.case2_cmd_res.delete()
        self.case3_cmd_res.delete()

        ag_test_case2_correct_result = self.ag_test_case2_incorrect_result
        ag_test_case3_correct_result = self.ag_test_case3_incorrect_result

        self.case2_cmd_res = obj_build.make_correct_ag_test_command_result(
            self.ag_test_case2_cmd, ag_test_case_result=ag_test_case2_correct_result)
        self.case3_cmd_res = obj_build.make_correct_ag_test_command_result(
            self.ag_test_case3_cmd, ag_test_case_result=ag_test_case3_correct_result)

        fdbk = get_suite_fdbk(self.ag_suite1_result, ag_models.FeedbackCategory.normal)

        expected_case_fdbks = [
            get_case_fdbk(
                self.ag_test_case1_correct_result, ag_models.FeedbackCategory.normal).to_dict(),
            get_case_fdbk(
                ag_test_case2_correct_result, ag_models.FeedbackCategory.normal).to_dict(),
            get_case_fdbk(
                ag_test_case3_correct_result, ag_models.FeedbackCategory.normal).to_dict()
        ]

        self.assertEqual(expected_case_fdbks,
                         [case_fdbk.to_dict() for case_fdbk in fdbk.ag_test_case_results])

    def test_non_normal_fdbk_no_override(self):
        fdbk = get_suite_fdbk(self.ag_suite1_result,
                              ag_models.FeedbackCategory.past_limit_submission)

        self.assertEqual(0, fdbk.total_points)
        self.assertEqual(0, fdbk.total_points_possible)

        expected_case_fdbks = [
            get_case_fdbk(
                self.ag_test_case1_correct_result,
                ag_models.FeedbackCategory.past_limit_submission).to_dict(),
            get_case_fdbk(
                self.ag_test_case2_incorrect_result,
                ag_models.FeedbackCategory.past_limit_submission).to_dict(),
            get_case_fdbk(
                self.ag_test_case3_incorrect_result,
                ag_models.FeedbackCategory.past_limit_submission).to_dict()
        ]

        self.assertEqual(expected_case_fdbks,
                         [case_fdbk.to_dict() for case_fdbk in fdbk.ag_test_case_results])
