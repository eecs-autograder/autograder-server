from unittest import mock

from django.db.models import signals
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.models.ag_test.ag_test_command import AGTestCommandFeedbackConfig
from autograder.core.submission_feedback import update_denormalized_ag_test_results
from autograder.core.tests.test_submission_feedback.fdbk_getter_shortcuts import \
    get_submission_fdbk
from autograder.grading_tasks.tasks import mark_submission_as_finished
from autograder.utils.testing import UnitTestBase


# Disable cache invalidation from editing commands.
@mock.patch('autograder.rest_api.signals.clear_submission_results_cache',
            new=lambda *args, **kwargs: None)
class SubmissionResultsCachingTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_submission_normal_fdbk_results_cached_by_default(self):
        self.maxDiff = None
        cmd = obj_build.make_full_ag_test_command(
            normal_fdbk_config=AGTestCommandFeedbackConfig.max_fdbk_config())
        project = cmd.ag_test_case.ag_test_suite.project
        project.validate_and_update(visible_to_students=True)

        admin_group = obj_build.make_group(project=project, members_role=obj_build.UserRole.admin)
        submission1 = obj_build.make_finished_submission(group=admin_group)
        submission2 = obj_build.make_finished_submission(group=admin_group)

        submission1_cmd_result = obj_build.make_correct_ag_test_command_result(
            cmd, submission=submission1)
        submission2_cmd_result = obj_build.make_incorrect_ag_test_command_result(
            cmd, submission=submission2)
        submission1 = update_denormalized_ag_test_results(submission1.pk)
        submission2 = update_denormalized_ag_test_results(submission2.pk)

        # Request the results for submission1 so that they are cached.
        self.client.force_authenticate(admin_group.members.first())
        response = self.client.get(self._make_url(submission1))
        old_submission1_results = get_submission_fdbk(
            submission1, ag_models.FeedbackCategory.normal).to_dict()
        self.assertIsNotNone(old_submission1_results['total_points'])
        self.assertNotEqual(0, old_submission1_results['total_points_possible'])
        self.assertEqual(old_submission1_results, response.data)

        # Change something in the test that affects the results.
        cmd.validate_and_update(
            points_for_correct_return_code=cmd.points_for_correct_return_code + 5)

        # Request submission1 results again, we should get the old (cached) results.
        response = self.client.get(self._make_url(submission1))
        self.assertEqual(old_submission1_results, response.data)

        # Request submission2 results, they should reflect the change we made.
        response = self.client.get(self._make_url(submission2))
        self.assertEqual(get_submission_fdbk(submission2,
                                             ag_models.FeedbackCategory.normal).to_dict(),
                         response.data)

    def test_non_normal_feedback_results_not_cached(self):
        cmd = obj_build.make_full_ag_test_command(
            normal_fdbk_config=AGTestCommandFeedbackConfig.max_fdbk_config(),
            ultimate_submission_fdbk_config=AGTestCommandFeedbackConfig.max_fdbk_config(),
            past_limit_submission_fdbk_config=AGTestCommandFeedbackConfig.max_fdbk_config())
        project = cmd.ag_test_case.ag_test_suite.project
        project.validate_and_update(visible_to_students=True)

        admin_group = obj_build.make_group(project=project, members_role=obj_build.UserRole.admin)
        submission = obj_build.make_finished_submission(group=admin_group)

        cmd_result = obj_build.make_correct_ag_test_command_result(cmd, submission=submission)
        submission = update_denormalized_ag_test_results(submission.pk)

        self.client.force_authenticate(admin_group.members.first())

        for fdbk_category in ag_models.FeedbackCategory:
            if fdbk_category == ag_models.FeedbackCategory.normal:
                continue

            url = self._make_url(submission, fdbk_category=fdbk_category)
            old_response = self.client.get(url)
            self.assertEqual(
                get_submission_fdbk(submission, fdbk_category).to_dict(),
                old_response.data)

            cmd.validate_and_update(
                points_for_correct_return_code=cmd.points_for_correct_return_code + 1)

            new_response = self.client.get(url)
            self.assertNotEqual(old_response.data, new_response.data)

            self.assertEqual(get_submission_fdbk(submission, fdbk_category).to_dict(),
                             new_response.data)

    # In autograder.grading_tasks.tasks.grade_submission.mark_submission_as_finished,
    # the cached submission results will be cleared. This allows us to cache results
    # for a submission that is waiting for deferred tests to finish.
    def test_result_caching_per_grading_status(self):
        """
        Tests that results for received, queued, and being_graded submissions are
        never cached. Then, makes sure that when a submission goes from waiting_for_deferred
        to finished_grading, the cached results for that submission are cleared.
        """
        self.maxDiff = None
        cmd = obj_build.make_full_ag_test_command(
            normal_fdbk_config=AGTestCommandFeedbackConfig.max_fdbk_config(),
            ultimate_submission_fdbk_config=AGTestCommandFeedbackConfig.max_fdbk_config(),
            past_limit_submission_fdbk_config=AGTestCommandFeedbackConfig.max_fdbk_config())
        project = cmd.ag_test_case.ag_test_suite.project
        project.validate_and_update(visible_to_students=True)

        student_group = obj_build.make_group(project=project)
        self.client.force_authenticate(student_group.members.first())

        # Make sure that the cache invalidation on waiting_for_deferred -> finished_grading
        # isn't overly aggressive.
        finished_submission = obj_build.make_finished_submission(group=student_group)
        finished_result = obj_build.make_correct_ag_test_command_result(
            cmd, submission=finished_submission)
        response = self.client.get(self._make_url(finished_submission))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        old_finished_data = response.data

        submission = obj_build.make_submission(
            group=student_group, status=ag_models.Submission.GradingStatus.received)

        url = self._make_url(submission)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        submission.status = ag_models.Submission.GradingStatus.queued
        submission.save()

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        submission.status = ag_models.Submission.GradingStatus.being_graded
        submission.save()

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        cmd_result = obj_build.make_correct_ag_test_command_result(cmd, submission=submission)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_submission_fdbk(submission,
                                             ag_models.FeedbackCategory.normal).to_dict(),
                         response.data)
        # Make a change to the command to make sure extra sure that being_graded
        # submission results aren't cached.
        cmd.validate_and_update(points_for_correct_stdout=cmd.points_for_correct_stdout + 1)
        # We should get fresh results here
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_submission_fdbk(submission,
                                             ag_models.FeedbackCategory.normal).to_dict(),
                         response.data)

        submission.status = ag_models.Submission.GradingStatus.waiting_for_deferred
        submission.save()

        # Waiting for deferred should be cached by this request...
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        old_data = get_submission_fdbk(submission, ag_models.FeedbackCategory.normal).to_dict()

        # ...so we should get stale results here.
        cmd.validate_and_update(points_for_correct_stdout=cmd.points_for_correct_stdout + 1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(old_data, response.data)

        # This should mark the submission as finished and clear the results cache...
        mark_submission_as_finished(None, submission.pk)
        # ...so we should get fresh results here.
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_submission_fdbk(submission,
                                             ag_models.FeedbackCategory.normal).to_dict(),
                         response.data)

        # Make sure that the results for are other submission are still stale.
        response = self.client.get(self._make_url(finished_submission))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(old_finished_data, response.data)

    def test_submission_normal_fdbk_results_use_cache_false(self):
        self.maxDiff = None
        cmd = obj_build.make_full_ag_test_command(
            normal_fdbk_config=AGTestCommandFeedbackConfig.max_fdbk_config())
        project = cmd.ag_test_case.ag_test_suite.project
        project.validate_and_update(visible_to_students=True)

        student_group = obj_build.make_group(project=project,
                                             members_role=obj_build.UserRole.admin)
        submission = obj_build.make_finished_submission(group=student_group)

        submission_cmd_result = obj_build.make_correct_ag_test_command_result(
            cmd, submission=submission)
        submission = update_denormalized_ag_test_results(submission.pk)

        self.client.force_authenticate(student_group.members.first())

        # Request the results for submission with use_cache=false
        response = self.client.get(self._make_url(submission, use_cache=False))
        old_submission_results = get_submission_fdbk(
            submission,
            ag_models.FeedbackCategory.normal
        ).to_dict()

        self.assertIsNotNone(old_submission_results['total_points'])
        self.assertNotEqual(0, old_submission_results['total_points_possible'])
        self.assertEqual(old_submission_results, response.data)

        # Change something in the test that affects the results.
        cmd.validate_and_update(
            points_for_correct_return_code=cmd.points_for_correct_return_code + 1)

        # Request the results for submission with use_cache=true, we should get
        # the updated results, and the updated results should be cached.
        response = self.client.get(self._make_url(submission))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        old_submission_results = get_submission_fdbk(
            submission, ag_models.FeedbackCategory.normal).to_dict()
        self.assertEqual(old_submission_results, response.data)

        # Update the test again
        cmd.validate_and_update(
            points_for_correct_return_code=cmd.points_for_correct_return_code + 1)

        # Requesting with cache should give us stale results
        response = self.client.get(self._make_url(submission))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(old_submission_results, response.data)

        # Requesting without cache should give us up-to-date results.
        response = self.client.get(self._make_url(submission, use_cache=False))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(get_submission_fdbk(submission,
                                             ag_models.FeedbackCategory.normal).to_dict(),
                         response.data)

    def test_admin_can_clear_results_cache_for_project(self):
        self.maxDiff = None
        course = obj_build.make_course()
        project1 = obj_build.make_project(course)
        project1_cmd = obj_build.make_full_ag_test_command(
            normal_fdbk_config=AGTestCommandFeedbackConfig.max_fdbk_config(),
            ag_test_case=obj_build.make_ag_test_case(
                ag_test_suite=obj_build.make_ag_test_suite(project=project1)))

        project2 = obj_build.make_project(course)
        project2_cmd = obj_build.make_full_ag_test_command(
            normal_fdbk_config=AGTestCommandFeedbackConfig.max_fdbk_config(),
            ag_test_case=obj_build.make_ag_test_case(
                ag_test_suite=obj_build.make_ag_test_suite(project=project2)))

        project1_group = obj_build.make_group(project=project1,
                                              members_role=obj_build.UserRole.admin)
        project1_submission1 = obj_build.make_finished_submission(group=project1_group)
        project1_submission1_cmd_result = obj_build.make_incorrect_ag_test_command_result(
            project1_cmd, submission=project1_submission1)
        project1_submission1 = update_denormalized_ag_test_results(project1_submission1.pk)

        project1_submission2 = obj_build.make_finished_submission(group=project1_group)
        project1_submission2_cmd_result = obj_build.make_correct_ag_test_command_result(
            project1_cmd, submission=project1_submission2)
        project1_submission2 = update_denormalized_ag_test_results(project1_submission2.pk)

        project2_group = obj_build.make_group(project=project2,
                                              members_role=obj_build.UserRole.admin)
        project2_submission = obj_build.make_finished_submission(group=project2_group)
        project2_cmd_result = obj_build.make_correct_ag_test_command_result(
            project2_cmd, submission=project2_submission)
        project2_submission = update_denormalized_ag_test_results(project2_submission.pk)

        # Request the results so they get cached
        self.client.force_authenticate(project1_group.members.first())
        response = self.client.get(self._make_url(project1_submission1))
        project1_submission1_old_results = get_submission_fdbk(
            project1_submission1, ag_models.FeedbackCategory.normal).to_dict()
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(project1_submission1_old_results, response.data)

        response = self.client.get(self._make_url(project1_submission2))
        project1_submission2_old_results = get_submission_fdbk(
            project1_submission2, ag_models.FeedbackCategory.normal).to_dict()
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(project1_submission2_old_results, response.data)

        self.client.force_authenticate(project2_group.members.first())
        response = self.client.get(self._make_url(project2_submission))
        project2_submission_old_results = get_submission_fdbk(
            project2_submission, ag_models.FeedbackCategory.normal).to_dict()
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(project2_submission_old_results, response.data)

        for result in (project1_submission1_old_results,
                       project1_submission2_old_results,
                       project2_submission_old_results):
            self.assertIsNotNone(result['total_points'])
            self.assertNotEqual(0, result['total_points_possible'])

        # Change something in both tests that affects the results
        project1_cmd.validate_and_update(
            points_for_correct_return_code=project1_cmd.points_for_correct_return_code + 2)
        project2_cmd.validate_and_update(
            points_for_correct_stdout=project2_cmd.points_for_correct_stdout + 3)

        # Clear project1's results cache
        response = self.client.delete(reverse('project-results-cache', kwargs={'pk': project1.pk}))
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

        # Make sure that only project1's results cache was cleared, not project2's
        self.client.force_authenticate(project1_group.members.first())
        response = self.client.get(self._make_url(project1_submission1))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(
            get_submission_fdbk(project1_submission1, ag_models.FeedbackCategory.normal).to_dict(),
            response.data)
        response = self.client.get(self._make_url(project1_submission2))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(
            get_submission_fdbk(project1_submission2, ag_models.FeedbackCategory.normal).to_dict(),
            response.data)

        self.client.force_authenticate(project2_group.members.first())
        response = self.client.get(self._make_url(project2_submission))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(project2_submission_old_results, response.data)

    def test_non_admin_clear_results_cache_permission_denied(self):
        project = obj_build.make_project()
        [staff] = obj_build.make_staff_users(project.course, 1)
        self.client.force_authenticate(staff)
        response = self.client.delete(reverse('project-results-cache', kwargs={'pk': project.pk}))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def _make_url(self, submission: ag_models.Submission,
                  fdbk_category: ag_models.FeedbackCategory = ag_models.FeedbackCategory.normal,
                  use_cache=True):
        url = reverse('submission-results', kwargs={'pk': submission.pk})
        url += '?feedback_category={}'.format(fdbk_category.value)
        if not use_cache:
            url += '&use_cache=false'

        return url
