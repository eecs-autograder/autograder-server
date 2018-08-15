import datetime
from unittest import mock

from django.utils import timezone

import autograder.core.models as ag_models
from autograder.core.models.get_ultimate_submissions import get_ultimate_submission
from autograder.core.submission_feedback import (
    update_denormalized_ag_test_results, AGTestPreLoader, SubmissionResultFeedback)
from autograder.rest_api.serialize_ultimate_submission_results import (
    serialize_ultimate_submission_results)
from autograder.utils import two_decimal_place_string
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as hg_models


class SerializeUltimateSubmissionResultsTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None

        self.project = obj_build.make_project(
            # Future closing_time
            closing_time=timezone.now() + datetime.timedelta(days=1)
        )
        self.course = self.project.course

        self.ag_test_suite = obj_build.make_ag_test_suite(self.project)
        self.ag_test_case = obj_build.make_ag_test_case(self.ag_test_suite)
        self.ag_test_cmd = obj_build.make_full_ag_test_command(self.ag_test_case)

        self.student_test_suite = obj_build.make_student_test_suite(self.project)

        self.ag_test_preloader = AGTestPreLoader(self.project)

    def test_serialize_groups_ultimate_submissions(self):
        group1 = obj_build.make_group(project=self.project)
        submission1 = obj_build.make_finished_submission(group1)
        submission1 = self._add_results_to_submission(submission1, results_correct=False)
        submission1_fdbk = SubmissionResultFeedback(
            submission1, ag_models.FeedbackCategory.max, self.ag_test_preloader)
        self.assertEqual(0, submission1_fdbk.total_points)
        self.assertNotEqual(0, submission1_fdbk.total_points_possible)

        group2 = obj_build.make_group(project=self.project, num_members=2)
        submission2 = obj_build.make_finished_submission(group2)
        submission2 = self._add_results_to_submission(submission2, results_correct=True)
        submission2_fdbk = SubmissionResultFeedback(
            submission2, ag_models.FeedbackCategory.max, self.ag_test_preloader)
        self.assertNotEqual(0, submission2_fdbk.total_points)
        self.assertNotEqual(0, submission2_fdbk.total_points_possible)

        expected = [
            {
                'username': group1.member_names[0],
                'group': group1.to_dict(),
                'ultimate_submission': {
                    'results': {
                        'total_points': two_decimal_place_string(submission1_fdbk.total_points),
                        'total_points_possible': two_decimal_place_string(
                            submission1_fdbk.total_points_possible)
                    },
                    **submission1.to_dict()
                }
            },

            {
                'username': group2.member_names[0],
                'group': group2.to_dict(),
                'ultimate_submission': {
                    'results': {
                        'total_points': two_decimal_place_string(submission2_fdbk.total_points),
                        'total_points_possible': two_decimal_place_string(
                            submission2_fdbk.total_points_possible)
                    },
                    **submission2.to_dict()
                }
            },
            {
                'username': group2.member_names[1],
                'group': group2.to_dict(),
                'ultimate_submission': {
                    'results': {
                        'total_points': two_decimal_place_string(submission2_fdbk.total_points),
                        'total_points_possible': two_decimal_place_string(
                            submission2_fdbk.total_points_possible)
                    },
                    **submission2.to_dict()
                }
            }
        ]

        actual = serialize_ultimate_submission_results(
            [SubmissionResultFeedback(submission1, ag_models.FeedbackCategory.max,
                                      self.ag_test_preloader),
             SubmissionResultFeedback(submission2, ag_models.FeedbackCategory.max,
                                      self.ag_test_preloader)],
            full_results=False
        )
        self.assertEqual(expected, actual)

    def test_serialize_groups_ultimate_submissions_full_results(self):
        group = obj_build.make_group(project=self.project)
        submission = obj_build.make_finished_submission(group)
        submission = self._add_results_to_submission(submission, results_correct=False)
        submission_fdbk = SubmissionResultFeedback(
            submission, ag_models.FeedbackCategory.max, self.ag_test_preloader)
        self.assertEqual(0, submission_fdbk.total_points)
        self.assertNotEqual(0, submission_fdbk.total_points_possible)

        expected = [
            {
                'username': group.member_names[0],
                'group': group.to_dict(),
                'ultimate_submission': {
                    'results': submission_fdbk.to_dict(),
                    **submission.to_dict()
                }
            },
        ]

        actual = serialize_ultimate_submission_results(
            [SubmissionResultFeedback(submission, ag_models.FeedbackCategory.max,
                                      self.ag_test_preloader)],
            full_results=True
        )
        self.assertEqual(expected, actual)

    def test_group_has_extension_ultimate_submission_is_none(self):
        group_with_future_extension = obj_build.make_group(
            num_members=2,
            project=self.project, extended_due_date=timezone.now() + datetime.timedelta(days=1))
        extension_submission = obj_build.make_finished_submission(group_with_future_extension)
        extension_submission = self._add_results_to_submission(
            extension_submission, results_correct=True)

        group = obj_build.make_group(project=self.project)
        submission = obj_build.make_finished_submission(group)
        submission = self._add_results_to_submission(submission, results_correct=False)
        submission_fdbk = SubmissionResultFeedback(
            submission, ag_models.FeedbackCategory.max, self.ag_test_preloader)
        self.assertEqual(0, submission_fdbk.total_points)
        self.assertNotEqual(0, submission_fdbk.total_points_possible)

        expected = [
            {
                'username': group_with_future_extension.member_names[0],
                'group': group_with_future_extension.to_dict(),
                'ultimate_submission': None
            },
            {
                'username': group_with_future_extension.member_names[1],
                'group': group_with_future_extension.to_dict(),
                'ultimate_submission': None
            },

            {
                'username': group.member_names[0],
                'group': group.to_dict(),
                'ultimate_submission': {
                    'results': {
                        'total_points': two_decimal_place_string(submission_fdbk.total_points),
                        'total_points_possible': two_decimal_place_string(
                            submission_fdbk.total_points_possible)
                    },
                    **submission.to_dict()
                }
            }
        ]

        actual = serialize_ultimate_submission_results(
            [SubmissionResultFeedback(extension_submission, ag_models.FeedbackCategory.max,
                                      self.ag_test_preloader),
             SubmissionResultFeedback(submission, ag_models.FeedbackCategory.max,
                                      self.ag_test_preloader)],
            full_results=False
        )
        self.assertEqual(expected, actual)

    def test_group_has_user_most_recent_doesnt_count_for(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)

        group = obj_build.make_group(project=self.project, num_members=2)

        # IMPORTANT: Keep the doesn't count for user as the first in the
        # group. That way we can verify that special-casing an ultimate
        # submission for a member of the group doesn't affect the
        # other group members' scores.
        doesnt_count_for_username = group.member_names[0]
        doesnt_count_for_user = group.members.get(username=doesnt_count_for_username)
        counts_for_username = group.member_names[1]

        first_submission = self._add_results_to_submission(
            obj_build.make_finished_submission(group), results_correct=True)

        second_most_recent_submission = self._add_results_to_submission(
            obj_build.make_finished_submission(group), results_correct=False)
        second_most_recent_submission_fdbk = SubmissionResultFeedback(
            second_most_recent_submission, ag_models.FeedbackCategory.max, self.ag_test_preloader)
        self.assertEqual(0, second_most_recent_submission_fdbk.total_points)
        self.assertNotEqual(0, second_most_recent_submission_fdbk.total_points_possible)

        most_recent_submission = self._add_results_to_submission(
            obj_build.make_finished_submission(group), results_correct=True)
        most_recent_submission_fdbk = SubmissionResultFeedback(
            most_recent_submission, ag_models.FeedbackCategory.max, self.ag_test_preloader)
        self.assertNotEqual(0, most_recent_submission_fdbk.total_points)
        self.assertNotEqual(0, most_recent_submission_fdbk.total_points_possible)

        most_recent_submission.does_not_count_for = [doesnt_count_for_username]
        most_recent_submission.save()

        expected = [
            {
                'username': doesnt_count_for_username,
                'group': group.to_dict(),
                'ultimate_submission': {
                    'results': {
                        'total_points': two_decimal_place_string(
                            second_most_recent_submission_fdbk.total_points),
                        'total_points_possible': two_decimal_place_string(
                            second_most_recent_submission_fdbk.total_points_possible)
                    },
                    **second_most_recent_submission.to_dict()
                }
            },
            {
                'username': counts_for_username,
                'group': group.to_dict(),
                'ultimate_submission': {
                    'results': {
                        'total_points': two_decimal_place_string(
                            most_recent_submission_fdbk.total_points),
                        'total_points_possible': two_decimal_place_string(
                            most_recent_submission_fdbk.total_points_possible)
                    },
                    **most_recent_submission.to_dict()
                }
            }
        ]

        actual = serialize_ultimate_submission_results(
            [most_recent_submission_fdbk], full_results=False
        )
        self.assertEqual(expected, actual)

        mock_get_ultimate_submission = mock.Mock(wraps=get_ultimate_submission)
        with mock.patch('autograder.rest_api.serialize_ultimate_submission_results'
                        '.get_ultimate_submission',
                        new=mock_get_ultimate_submission):
            serialize_ultimate_submission_results(
                [most_recent_submission_fdbk], full_results=False)

            mock_get_ultimate_submission.assert_called_once_with(group, doesnt_count_for_user)

    def test_some_groups_have_finished_handgrading_result_others_have_no_handgrading_result(self):
        handgrading_rubric = hg_models.HandgradingRubric.objects.validate_and_create(
            project=self.project
        )  # type: hg_models.HandgradingRubric

        criterion = hg_models.Criterion.objects.validate_and_create(
            points=2, handgrading_rubric=handgrading_rubric)

        group_no_handgrading = obj_build.make_group(project=self.project)
        submission1 = obj_build.make_finished_submission(group_no_handgrading)
        submission1 = self._add_results_to_submission(submission1, results_correct=False)
        submission1_fdbk = SubmissionResultFeedback(
            submission1, ag_models.FeedbackCategory.max, self.ag_test_preloader)
        self.assertEqual(0, submission1_fdbk.total_points)
        self.assertNotEqual(0, submission1_fdbk.total_points_possible)

        group_2_members = obj_build.make_group(project=self.project, num_members=2)
        submission2 = obj_build.make_finished_submission(group_2_members)
        submission2 = self._add_results_to_submission(submission2, results_correct=True)
        submission2_fdbk = SubmissionResultFeedback(
            submission2, ag_models.FeedbackCategory.max, self.ag_test_preloader)
        self.assertNotEqual(0, submission2_fdbk.total_points)
        self.assertNotEqual(0, submission2_fdbk.total_points_possible)
        group_2_handgrading_result = hg_models.HandgradingResult.objects.validate_and_create(
            submission=submission2,
            group=group_2_members,
            handgrading_rubric=handgrading_rubric,
            finished_grading=True
        )  # type: hg_models.HandgradingResult
        hg_models.CriterionResult.objects.validate_and_create(
            selected=True,
            criterion=criterion,
            handgrading_result=group_2_handgrading_result)

        group_with_handgrading = obj_build.make_group(project=self.project)
        submission3 = obj_build.make_finished_submission(group_with_handgrading)
        submission3 = self._add_results_to_submission(submission3, results_correct=False)
        submission3_fdbk = SubmissionResultFeedback(
            submission3, ag_models.FeedbackCategory.max, self.ag_test_preloader)
        self.assertEqual(0, submission3_fdbk.total_points)
        self.assertNotEqual(0, submission3_fdbk.total_points_possible)
        group_3_handgrading_result = hg_models.HandgradingResult.objects.validate_and_create(
            submission=submission3,
            group=group_with_handgrading,
            handgrading_rubric=handgrading_rubric,
            finished_grading=True
        )  # type: hg_models.HandgradingResult
        hg_models.CriterionResult.objects.validate_and_create(
            selected=False,
            criterion=criterion,
            handgrading_result=group_3_handgrading_result)

        expected = [
            {
                'username': group_no_handgrading.member_names[0],
                'group': group_no_handgrading.to_dict(),
                'ultimate_submission': {
                    'results': {
                        'total_points': two_decimal_place_string(submission1_fdbk.total_points),
                        'total_points_possible': two_decimal_place_string(
                            submission1_fdbk.total_points_possible),
                        'handgrading_total_points': None,
                        'handgrading_total_points_possible': None
                    },
                    **submission1.to_dict()
                }
            },

            {
                'username': group_2_members.member_names[0],
                'group': group_2_members.to_dict(),
                'ultimate_submission': {
                    'results': {
                        'total_points': two_decimal_place_string(submission2_fdbk.total_points),
                        'total_points_possible': two_decimal_place_string(
                            submission2_fdbk.total_points_possible),
                        'handgrading_total_points': (
                            submission2_fdbk.submission.handgrading_result.total_points),
                        'handgrading_total_points_possible': (
                            submission2_fdbk.submission.handgrading_result.total_points_possible)
                    },
                    **submission2.to_dict()
                }
            },
            {
                'username': group_2_members.member_names[1],
                'group': group_2_members.to_dict(),
                'ultimate_submission': {
                    'results': {
                        'total_points': two_decimal_place_string(submission2_fdbk.total_points),
                        'total_points_possible': two_decimal_place_string(
                            submission2_fdbk.total_points_possible),
                        'handgrading_total_points': (
                            submission2_fdbk.submission.handgrading_result.total_points),
                        'handgrading_total_points_possible': (
                            submission2_fdbk.submission.handgrading_result.total_points_possible)
                    },
                    **submission2.to_dict()
                }
            },

            {
                'username': group_with_handgrading.member_names[0],
                'group': group_with_handgrading.to_dict(),
                'ultimate_submission': {
                    'results': {
                        'total_points': two_decimal_place_string(submission3_fdbk.total_points),
                        'total_points_possible': two_decimal_place_string(
                            submission3_fdbk.total_points_possible),
                        'handgrading_total_points': (
                            submission3_fdbk.submission.handgrading_result.total_points),
                        'handgrading_total_points_possible': (
                            submission3_fdbk.submission.handgrading_result.total_points_possible)
                    },
                    **submission3.to_dict()
                }
            }
        ]

        actual = serialize_ultimate_submission_results(
            [SubmissionResultFeedback(submission1, ag_models.FeedbackCategory.max,
                                      self.ag_test_preloader),
             SubmissionResultFeedback(submission2, ag_models.FeedbackCategory.max,
                                      self.ag_test_preloader),
             SubmissionResultFeedback(submission3, ag_models.FeedbackCategory.max,
                                      self.ag_test_preloader)],
            full_results=False,
            include_handgrading=True
        )
        self.assertEqual(expected, actual)

    def test_group_has_unfinished_handgrading_result(self):
        handgrading_rubric = hg_models.HandgradingRubric.objects.validate_and_create(
            project=self.project
        )  # type: hg_models.HandgradingRubric

        criterion = hg_models.Criterion.objects.validate_and_create(
            points=2, handgrading_rubric=handgrading_rubric)

        group_unfinished_handgrading = obj_build.make_group(project=self.project)
        submission = obj_build.make_finished_submission(group_unfinished_handgrading)
        submission = self._add_results_to_submission(submission, results_correct=False)
        submission_fdbk = SubmissionResultFeedback(
            submission, ag_models.FeedbackCategory.max, self.ag_test_preloader)
        handgrading_result = hg_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            group=group_unfinished_handgrading,
            handgrading_rubric=handgrading_rubric,
            finished_grading=False
        )  # type: hg_models.HandgradingResult
        hg_models.CriterionResult.objects.validate_and_create(
            selected=True,
            criterion=criterion,
            handgrading_result=handgrading_result)

        expected = [
            {
                'username': group_unfinished_handgrading.member_names[0],
                'group': group_unfinished_handgrading.to_dict(),
                'ultimate_submission': {
                    'results': {
                        'total_points': two_decimal_place_string(submission_fdbk.total_points),
                        'total_points_possible': two_decimal_place_string(
                            submission_fdbk.total_points_possible),
                        'handgrading_total_points': None,
                        'handgrading_total_points_possible': None
                    },
                    **submission.to_dict()
                }
            }
        ]

        actual = serialize_ultimate_submission_results(
            [SubmissionResultFeedback(submission, ag_models.FeedbackCategory.max,
                                      self.ag_test_preloader)],
            full_results=False,
            include_handgrading=True
        )
        self.assertEqual(expected, actual)

    def test_group_has_handgrading_result_with_full_results(self):
        handgrading_rubric = hg_models.HandgradingRubric.objects.validate_and_create(
            project=self.project
        )  # type: hg_models.HandgradingRubric

        criterion = hg_models.Criterion.objects.validate_and_create(
            points=2, handgrading_rubric=handgrading_rubric)

        group = obj_build.make_group(project=self.project)
        submission = obj_build.make_finished_submission(group)
        submission = self._add_results_to_submission(submission, results_correct=False)
        submission_fdbk = SubmissionResultFeedback(
            submission, ag_models.FeedbackCategory.max, self.ag_test_preloader)
        handgrading_result = hg_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            group=group,
            handgrading_rubric=handgrading_rubric,
            finished_grading=True
        )  # type: hg_models.HandgradingResult
        hg_models.CriterionResult.objects.validate_and_create(
            selected=True,
            criterion=criterion,
            handgrading_result=handgrading_result)

        results = submission_fdbk.to_dict()
        results['handgrading_total_points'] = (
            submission_fdbk.submission.handgrading_result.total_points)
        results['handgrading_total_points_possible'] = (
            submission_fdbk.submission.handgrading_result.total_points_possible)

        expected = [
            {
                'username': group.member_names[0],
                'group': group.to_dict(),
                'ultimate_submission': {
                    'results': results,
                    **submission.to_dict()
                }
            }
        ]

        actual = serialize_ultimate_submission_results(
            [SubmissionResultFeedback(submission, ag_models.FeedbackCategory.max,
                                      self.ag_test_preloader)],
            full_results=True,
            include_handgrading=True
        )
        self.assertEqual(expected, actual)

    def _add_results_to_submission(self, submission: ag_models.Submission,
                                   *, results_correct: bool) -> ag_models.Submission:
        if results_correct:
            obj_build.make_correct_ag_test_command_result(self.ag_test_cmd, submission=submission)
        else:
            obj_build.make_incorrect_ag_test_command_result(
                self.ag_test_cmd, submission=submission)

        ag_models.StudentTestSuiteResult.objects.validate_and_create(
            submission=submission, student_test_suite=self.student_test_suite)

        return update_denormalized_ag_test_results(submission.pk)
