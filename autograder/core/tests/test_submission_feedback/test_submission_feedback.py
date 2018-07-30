import json
from decimal import Decimal

from django.core.serializers.json import DjangoJSONEncoder

from autograder.core.models import get_submissions_with_results_queryset
from autograder.core.submission_feedback import update_denormalized_ag_test_results
from autograder.core.tests.test_submission_feedback.fdbk_getter_shortcuts import (
    get_suite_fdbk, get_submission_fdbk)
from autograder.utils.testing import UnitTestBase
import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build


class SubmissionFeedbackTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None

        self.project = obj_build.make_project()
        self.course = self.project.course

        self.ag_test_suite1 = obj_build.make_ag_test_suite(self.project)
        self.ag_test_case1 = obj_build.make_ag_test_case(self.ag_test_suite1)
        self.ag_test_cmd1 = obj_build.make_full_ag_test_command(
            self.ag_test_case1, set_arbitrary_points=True)

        self.ag_test_suite2 = obj_build.make_ag_test_suite(self.project)
        self.ag_test_case2 = obj_build.make_ag_test_case(self.ag_test_suite2)
        self.ag_test_cmd2 = obj_build.make_full_ag_test_command(
            self.ag_test_case2, set_arbitrary_points=True)

        self.points_per_bug_exposed = Decimal('3.5')
        self.num_buggy_impls = 4
        self.student_suite1 = ag_models.StudentTestSuite.objects.validate_and_create(
            name='suite1', project=self.project,
            buggy_impl_names=['bug{}'.format(i) for i in range(self.num_buggy_impls)],
            points_per_exposed_bug=self.points_per_bug_exposed
        )  # type: ag_models.StudentTestSuite
        self.student_suite2 = ag_models.StudentTestSuite.objects.validate_and_create(
            name='suite2', project=self.project,
            buggy_impl_names=['bug{}'.format(i) for i in range(self.num_buggy_impls)],
            points_per_exposed_bug=self.points_per_bug_exposed
        )  # type: ag_models.StudentTestSuite

        self.group = obj_build.make_group(num_members=1, project=self.project)
        self.submission = obj_build.make_submission(group=self.group)

        self.ag_suite_result1 = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=self.ag_test_suite1, submission=self.submission
        )  # type: ag_models.AGTestSuiteResult
        self.ag_case_result1 = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_suite_result=self.ag_suite_result1, ag_test_case=self.ag_test_case1
        )  # type: ag_models.AGTestCaseResult
        self.ag_cmd_result1 = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd1, self.ag_case_result1)

        self.ag_suite_result2 = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=self.ag_test_suite2, submission=self.submission
        )  # type: ag_models.AGTestSuiteResult
        self.ag_case_result2 = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_suite_result=self.ag_suite_result2, ag_test_case=self.ag_test_case2
        )  # type: ag_models.AGTestCaseResult
        self.ag_cmd_result2 = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd2, self.ag_case_result2)

        self.num_student_tests = 6
        self.student_tests = ['test{}'.format(i) for i in range(self.num_student_tests)]
        self.student_suite_result1 = ag_models.StudentTestSuiteResult.objects.validate_and_create(
            student_test_suite=self.student_suite1,
            submission=self.submission,
            student_tests=self.student_tests,
            bugs_exposed=self.student_suite1.buggy_impl_names
        )  # type: ag_models.StudentTestSuiteResult
        self.student_suite_result2 = ag_models.StudentTestSuiteResult.objects.validate_and_create(
            student_test_suite=self.student_suite2,
            submission=self.submission,
            student_tests=self.student_tests,
            bugs_exposed=self.student_suite2.buggy_impl_names
        )  # type: ag_models.StudentTestSuiteResult

        self.total_points_per_ag_suite = get_suite_fdbk(
            self.ag_suite_result1, ag_models.FeedbackCategory.max).total_points

        self.total_points_per_student_suite = self.num_buggy_impls * self.points_per_bug_exposed

        self.total_points = (self.total_points_per_ag_suite * 2
                             + self.total_points_per_student_suite * 2)
        self.total_points_possible = self.total_points

        self.assertEqual(
            self.total_points_per_ag_suite,
            get_suite_fdbk(self.ag_suite_result2, ag_models.FeedbackCategory.max).total_points)

        self.assertEqual(
            self.total_points_per_student_suite,
            self.student_suite_result1.get_fdbk(ag_models.FeedbackCategory.max).total_points)

        print(self.total_points)
        self.assertNotEqual(0, self.total_points_per_ag_suite)
        self.assertNotEqual(0, self.total_points_per_student_suite)
        self.assertNotEqual(0, self.total_points)

        self.submission = update_denormalized_ag_test_results(self.submission.pk)

    def test_max_fdbk(self):
        fdbk = get_submission_fdbk(self.submission, ag_models.FeedbackCategory.max)
        self.assertEqual(self.total_points, fdbk.total_points)
        self.assertEqual(self.total_points, fdbk.total_points_possible)

        self.assertSequenceEqual([self.ag_suite_result1.pk, self.ag_suite_result2.pk],
                                 [res.pk for res in fdbk.ag_test_suite_results])

        self.assertSequenceEqual([self.student_suite_result1, self.student_suite_result2],
                                 fdbk.student_test_suite_results)

    def test_ag_suite_result_ordering(self):
        for i in range(2):
            self.project.set_agtestsuite_order([self.ag_test_suite2.pk, self.ag_test_suite1.pk])
            fdbk = get_submission_fdbk(self.submission, ag_models.FeedbackCategory.max)
            self.assertSequenceEqual([self.ag_suite_result2.pk, self.ag_suite_result1.pk],
                                     [res.pk for res in fdbk.ag_test_suite_results])

            self.project.set_agtestsuite_order([self.ag_test_suite1.pk, self.ag_test_suite2.pk])
            fdbk = get_submission_fdbk(self.submission, ag_models.FeedbackCategory.max)
            self.assertSequenceEqual([self.ag_suite_result1.pk, self.ag_suite_result2.pk],
                                     [res.pk for res in fdbk.ag_test_suite_results])

    def test_student_suite_result_ordering(self):
        for i in range(2):
            self.project.set_studenttestsuite_order(
                [self.student_suite2.pk, self.student_suite1.pk])
            fdbk = get_submission_fdbk(self.submission, ag_models.FeedbackCategory.max)
            self.assertSequenceEqual([self.student_suite_result2, self.student_suite_result1],
                                     fdbk.student_test_suite_results)

            self.project.set_studenttestsuite_order(
                [self.student_suite1.pk, self.student_suite2.pk])
            fdbk = get_submission_fdbk(self.submission, ag_models.FeedbackCategory.max)
            self.assertSequenceEqual([self.student_suite_result1, self.student_suite_result2],
                                     fdbk.student_test_suite_results)

    def test_max_fdbk_some_incorrect(self):
        # Make something incorrect, re-check total points and total points
        # possible.
        self.ag_cmd_result1.return_code_correct = False
        self.ag_cmd_result1.stdout_correct = False
        self.ag_cmd_result1.stderr_correct = False
        self.ag_cmd_result1.save()
        self.submission = update_denormalized_ag_test_results(self.submission.pk)

        self.student_suite_result1.bugs_exposed = []
        self.student_suite_result1.save()

        fdbk = get_submission_fdbk(self.submission, ag_models.FeedbackCategory.max)

        self.assertEqual(self.total_points_per_ag_suite + self.total_points_per_student_suite,
                         fdbk.total_points)
        self.assertEqual(self.total_points_possible, fdbk.total_points_possible)

        # Make sure that adjusting max_points for a student test suite propagates
        max_points = self.points_per_bug_exposed.to_integral_value()
        self.student_suite2.validate_and_update(max_points=max_points)

        fdbk = get_submission_fdbk(self.submission, ag_models.FeedbackCategory.max)
        self.assertEqual(self.total_points_per_ag_suite + max_points,
                         fdbk.total_points)
        self.assertEqual(
            self.total_points_per_ag_suite * 2 + self.total_points_per_student_suite + max_points,
            fdbk.total_points_possible)

    def test_normal_fdbk(self):
        self.ag_test_cmd1.validate_and_update(
            normal_fdbk_config={
                'visible': False,
                'return_code_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'stdout_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'stderr_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'show_points': True
            }
        )
        self.ag_test_cmd2.validate_and_update(
            normal_fdbk_config={
                'stdout_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'stderr_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'show_points': True
            }
        )

        self.student_suite1.normal_fdbk_config.validate_and_update(
            bugs_exposed_fdbk_level=ag_models.BugsExposedFeedbackLevel.num_bugs_exposed,
            show_points=True)

        expected_points = (
            self.total_points_per_ag_suite - self.ag_test_cmd2.points_for_correct_return_code
            + self.total_points_per_student_suite)

        fdbk = get_submission_fdbk(self.submission, ag_models.FeedbackCategory.normal)
        self.assertEqual(expected_points, fdbk.total_points)
        self.assertEqual(expected_points, fdbk.total_points_possible)

        self.assertSequenceEqual([self.ag_suite_result1.pk, self.ag_suite_result2.pk],
                                 [res.pk for res in fdbk.ag_test_suite_results])
        actual_cmd_results = fdbk.to_dict()[
            'ag_test_suite_results'][0]['ag_test_case_results'][0]['ag_test_command_results']
        self.assertSequenceEqual([], actual_cmd_results)

        self.assertSequenceEqual([self.student_suite_result1, self.student_suite_result2],
                                 fdbk.student_test_suite_results)

    def test_past_limit_fdbk(self):
        self.ag_test_cmd2.validate_and_update(
            past_limit_submission_fdbk_config={
                'visible': False,
                'return_code_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'stdout_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'stderr_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'show_points': True
            }
        )
        self.ag_test_cmd1.validate_and_update(
            past_limit_submission_fdbk_config={
                'return_code_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'stderr_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'show_points': True
            }
        )

        self.student_suite2.past_limit_submission_fdbk_config.validate_and_update(
            bugs_exposed_fdbk_level=ag_models.BugsExposedFeedbackLevel.num_bugs_exposed,
            show_points=True)

        expected_points = (
            self.total_points_per_ag_suite - self.ag_test_cmd1.points_for_correct_stdout)
        fdbk = get_submission_fdbk(
            self.submission, ag_models.FeedbackCategory.past_limit_submission)
        self.assertEqual(expected_points, fdbk.total_points)
        self.assertEqual(expected_points, fdbk.total_points_possible)

        self.assertSequenceEqual([self.ag_suite_result1.pk, self.ag_suite_result2.pk],
                                 [res.pk for res in fdbk.ag_test_suite_results])
        actual_cmd_results = fdbk.to_dict()[
            'ag_test_suite_results'][1]['ag_test_case_results'][0]['ag_test_command_results']
        self.assertSequenceEqual([], actual_cmd_results)

        self.assertSequenceEqual([], fdbk.student_test_suite_results)

    def test_ultimate_fdbk(self):
        self.ag_test_cmd1.validate_and_update(ultimate_submission_fdbk_config={'visible': False})
        self.student_suite1.ultimate_submission_fdbk_config.validate_and_update(visible=False)
        fdbk = get_submission_fdbk(self.submission, ag_models.FeedbackCategory.ultimate_submission)
        self.assertEqual(self.total_points_per_ag_suite + self.total_points_per_student_suite,
                         fdbk.total_points)
        self.assertEqual(self.total_points_per_ag_suite + self.total_points_per_student_suite,
                         fdbk.total_points_possible)

        self.assertSequenceEqual([self.ag_suite_result1.pk, self.ag_suite_result2.pk],
                                 [res.pk for res in fdbk.ag_test_suite_results])
        actual_cmd_results = fdbk.to_dict()[
            'ag_test_suite_results'][0]['ag_test_case_results'][0]['ag_test_command_results']
        self.assertSequenceEqual([], actual_cmd_results)

        self.assertSequenceEqual([self.student_suite_result2], fdbk.student_test_suite_results)

    def test_individual_suite_result_order(self):
        self.project.set_agtestsuite_order([self.ag_test_suite2.pk, self.ag_test_suite1.pk])
        self.project.set_studenttestsuite_order([self.student_suite2.pk, self.student_suite1.pk])

        self.submission = get_submissions_with_results_queryset().get(pk=self.submission.pk)
        fdbk = get_submission_fdbk(self.submission, ag_models.FeedbackCategory.max)

        self.assertSequenceEqual([self.ag_suite_result2.pk, self.ag_suite_result1.pk],
                                 [res.pk for res in fdbk.ag_test_suite_results])
        self.assertSequenceEqual(
            [get_suite_fdbk(self.ag_suite_result2, ag_models.FeedbackCategory.max).to_dict(),
             get_suite_fdbk(self.ag_suite_result1, ag_models.FeedbackCategory.max).to_dict()],
            fdbk.to_dict()['ag_test_suite_results'])

        self.assertSequenceEqual([self.student_suite_result2, self.student_suite_result1],
                                 fdbk.student_test_suite_results)
        self.assertSequenceEqual(
            [self.student_suite_result2.get_fdbk(ag_models.FeedbackCategory.max).to_dict(),
             self.student_suite_result1.get_fdbk(ag_models.FeedbackCategory.max).to_dict()],
            fdbk.to_dict()['student_test_suite_results'])

    def test_some_ag_and_student_test_suites_not_visible(self):
        self.ag_test_suite2.validate_and_update(
            ultimate_submission_fdbk_config={'visible': False})
        self.student_suite2.validate_and_update(
            ultimate_submission_fdbk_config={'visible': False})

        fdbk = get_submission_fdbk(self.submission, ag_models.FeedbackCategory.ultimate_submission)
        self.assertEqual(self.total_points_per_ag_suite + self.total_points_per_student_suite,
                         fdbk.total_points)
        self.assertEqual(self.total_points_per_ag_suite + self.total_points_per_student_suite,
                         fdbk.total_points_possible)

        self.assertSequenceEqual([self.ag_suite_result1.pk],
                                 [res.pk for res in fdbk.ag_test_suite_results])
        self.assertSequenceEqual(
            [get_suite_fdbk(self.ag_suite_result1,
                            ag_models.FeedbackCategory.ultimate_submission).to_dict()],
            fdbk.to_dict()['ag_test_suite_results'])

        self.assertSequenceEqual([self.student_suite_result1], fdbk.student_test_suite_results)
        self.assertSequenceEqual(
            [self.student_suite_result1.get_fdbk(
                ag_models.FeedbackCategory.ultimate_submission).to_dict()],
            fdbk.to_dict()['student_test_suite_results'])

    def test_fdbk_to_dict(self):
        expected = {
            'pk': self.submission.pk,
            'total_points': self.total_points,
            'total_points_possible': self.total_points,
            'ag_test_suite_results': [
                get_suite_fdbk(self.ag_suite_result1, ag_models.FeedbackCategory.max).to_dict(),
                get_suite_fdbk(self.ag_suite_result2, ag_models.FeedbackCategory.max).to_dict()
            ],
            'student_test_suite_results': [
                self.student_suite_result1.get_fdbk(ag_models.FeedbackCategory.max).to_dict(),
                self.student_suite_result2.get_fdbk(ag_models.FeedbackCategory.max).to_dict(),
            ]
        }

        actual = get_submission_fdbk(self.submission, ag_models.FeedbackCategory.max).to_dict()
        print(json.dumps(actual, indent=4, sort_keys=True, cls=DjangoJSONEncoder))
        self.assertEqual(expected, actual)
