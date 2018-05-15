import datetime
from typing import Optional
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
from autograder.utils import filter_dict
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class AllUltimateSubmissionResultsViewTestCase(UnitTestBase):
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

        self.client = APIClient()
        self.base_url = reverse('all-ultimate-submission-results',
                                kwargs={'project_pk': self.project.pk})

        # For use by self._make_group_with_submissions only
        self._num_groups = 0

        # This is to make sure we use the right group queryset
        other_project = obj_build.make_project()
        other_group = obj_build.make_group(project=other_project)
        other_submission = obj_build.make_finished_submission(other_group)

    def _make_group_with_submissions(self, num_members: int, *, num_submissions: int=1,
                                     members_role: obj_build.UserRole=obj_build.UserRole.student,
                                     members=None,
                                     **group_kwargs):
        assert num_submissions > 0

        self._num_groups += 1
        if members is None:
            # We want groups to be sorted in the same order they're created.
            members = [
                User.objects.create(username=f'group{self._num_groups}_user{i}')
                for i in range(num_members)
            ]
        group = obj_build.make_group(
            members=members,
            members_role=members_role,
            project=self.project,
            **group_kwargs)

        # The first submission gets correct results so that it's the best.
        # The others get incorrect results.
        best_submission = obj_build.make_finished_submission(group=group)
        self._add_results_to_submission(best_submission, results_correct=True)

        for i in range(num_submissions - 1):
            submission = obj_build.make_finished_submission(group=group)
            self._add_results_to_submission(submission, results_correct=False)

        return group, best_submission

    def _add_results_to_submission(self, submission: ag_models.Submission,
                                   *, results_correct: bool):
        if results_correct:
            obj_build.make_correct_ag_test_command_result(self.ag_test_cmd, submission=submission)
        else:
            obj_build.make_incorrect_ag_test_command_result(
                self.ag_test_cmd, submission=submission)

        ag_models.StudentTestSuiteResult.objects.validate_and_create(
            submission=submission, student_test_suite=self.student_test_suite)

    def _make_result_content_for_user(self, username: str, group: ag_models.Group,
                                      ultimate_submission: Optional[ag_models.Submission],
                                      *, points_only: bool):
        submission_data = (
            ultimate_submission.to_dict() if ultimate_submission is not None else None)
        if submission_data is not None:
            result_data = ultimate_submission.get_fdbk(ag_models.FeedbackCategory.max).to_dict()
            if points_only:
                result_data = filter_dict(result_data, ('total_points', 'total_points_possible'))
            submission_data['results'] = result_data

        return {
            "username": username,
            "group": group.to_dict(),
            "ultimate_submission": submission_data
        }

    def test_admin_get_results_ultimate_policy_most_recent(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)

        student_group, _ = self._make_group_with_submissions(2, num_submissions=3)
        staff_group, _ = self._make_group_with_submissions(
            1, members_role=obj_build.UserRole.staff)

        expected = [
            self._make_result_content_for_user(
                username, student_group, student_group.submissions.first(), points_only=True)
            for username in student_group.member_names
        ]
        expected.append(
            self._make_result_content_for_user(
                staff_group.member_names[0], staff_group, staff_group.submissions.first(),
                points_only=True)
        )

        admin = obj_build.make_admin_user(self.course)
        self.client.force_authenticate(admin)

        response = self.client.get(self.base_url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(expected, response.data['results'])

    def test_staff_get_results_past_deadline_ultimate_scores_shown_ultimate_policy_best(self):
        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best,
            hide_ultimate_submission_fdbk=False
        )

        student_group, student_best = self._make_group_with_submissions(1, num_submissions=2)
        staff_group, staff_best = self._make_group_with_submissions(
            1, members_role=obj_build.UserRole.staff)

        expected = [
            self._make_result_content_for_user(
                student_group.member_names[0], student_group,
                student_best, points_only=True),
            self._make_result_content_for_user(
                staff_group.member_names[0], staff_group,
                staff_best, points_only=True)
        ]

        staff = obj_build.make_staff_user(self.course)
        self.client.force_authenticate(staff)

        past_closing_time = timezone.now() - datetime.timedelta(hours=1)
        for closing_time in past_closing_time, None:
            self.project.validate_and_update(closing_time=closing_time)

            response = self.client.get(self.base_url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)

            self.assertSequenceEqual(expected, response.data['results'])

    def test_get_results_with_result_details(self):
        student_group, submission = self._make_group_with_submissions(1)

        expected = [
            self._make_result_content_for_user(
                student_group.member_names[0], student_group,
                submission, points_only=False)
        ]

        admin = obj_build.make_admin_user(self.course)
        self.client.force_authenticate(admin)

        query_params = {
            'full_results': 'true'
        }
        url = f'{self.base_url}?{urlencode(query_params)}'

        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(expected, response.data['results'])

    def test_get_results_exclude_staff(self):
        student_group, student_submission = self._make_group_with_submissions(1)
        # Staff and admin will be excluded
        staff_group, staff_submission = self._make_group_with_submissions(
            1, members_role=obj_build.UserRole.staff)
        admin_group, admin_submission = self._make_group_with_submissions(
            1, members_role=obj_build.UserRole.admin)

        expected = [
            self._make_result_content_for_user(
                student_group.member_names[0], student_group,
                student_submission, points_only=True),
        ]

        admin = obj_build.make_admin_user(self.course)
        self.client.force_authenticate(admin)

        query_params = {
            'include_staff': 'false'
        }
        url = f'{self.base_url}?{urlencode(query_params)}'

        admin = obj_build.make_admin_user(self.course)
        self.client.force_authenticate(admin)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(expected, response.data['results'])

    def test_get_results_custom_page_size(self):
        student_group1, student_submission1 = self._make_group_with_submissions(2)
        # This will be on_page 2
        student_group2, student_submission2 = self._make_group_with_submissions(1)

        expected = [
            # There are still two entries for student_group1, even
            # though we only have one group per page.
            self._make_result_content_for_user(
                student_group1.member_names[0], student_group1,
                student_submission1, points_only=True),
            self._make_result_content_for_user(
                student_group1.member_names[1], student_group1,
                student_submission1, points_only=True),
        ]

        admin = obj_build.make_admin_user(self.course)
        self.client.force_authenticate(admin)

        query_params = {
            'groups_per_page': 1
        }
        url = f'{self.base_url}?{urlencode(query_params)}'

        response = self.client.get(url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(expected, response.data['results'])

        page_two = [
            self._make_result_content_for_user(
                student_group2.member_names[0], student_group2,
                student_submission2, points_only=True),
        ]

        query_params = {
            'groups_per_page': 1,
            'page': 2
        }
        url = f'{self.base_url}?{urlencode(query_params)}'

        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(page_two, response.data['results'])

    def test_non_staff_get_results_permission_denied(self):
        student_group1, student_submission1 = self._make_group_with_submissions(1)
        self.client.force_authenticate(student_group1.members.first())
        response = self.client.get(self.base_url)

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_staff_get_results_deadline_not_past_permission_denied(self):
        self.assertLess(timezone.now(), self.project.closing_time)
        self.project.validate_and_update(hide_ultimate_submission_fdbk=False)

        staff = obj_build.make_staff_user(self.course)

        self.client.force_authenticate(staff)
        response = self.client.get(self.base_url)

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_staff_get_results_ultimate_scores_hidden_permission_denied(self):
        self.project.validate_and_update(
            closing_time=None,
            hide_ultimate_submission_fdbk=True)

        staff = obj_build.make_staff_user(self.course)

        self.client.force_authenticate(staff)
        response = self.client.get(self.base_url)

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_get_results_group_has_extension_ultimate_submission_is_null(self):
        student_group, student_submission = self._make_group_with_submissions(
            2, extended_due_date=timezone.now() + datetime.timedelta(days=1))

        expected = [
            self._make_result_content_for_user(
                student_group.member_names[0], student_group,
                None, points_only=True),
            self._make_result_content_for_user(
                student_group.member_names[1], student_group,
                None, points_only=True),
        ]

        admin = obj_build.make_admin_user(self.course)
        self.client.force_authenticate(admin)

        response = self.client.get(self.base_url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(expected, response.data['results'])

    def test_get_results_group_has_no_submissions(self):
        group = obj_build.make_group(num_members=2, project=self.project)
        self.assertEqual(0, group.submissions.count())

        admin = obj_build.make_admin_user(self.course)
        self.client.force_authenticate(admin)

        response = self.client.get(self.base_url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual([], response.data['results'])
