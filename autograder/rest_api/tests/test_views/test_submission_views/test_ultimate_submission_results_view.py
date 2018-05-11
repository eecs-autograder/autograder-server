import datetime
from typing import Optional

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

    def _make_group_with_submissions(self, num_members: int, num_submissions: int=1,
                                     members_role: obj_build.UserRole=obj_build.UserRole.student,
                                     **group_kwargs):
        assert num_submissions > 0

        group = obj_build.make_group(
            num_members=num_members,
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

        return group

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

    def test_admin_get_results(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)

        student_group = self._make_group_with_submissions(2, 3)
        staff_group = self._make_group_with_submissions(1, members_role=obj_build.UserRole.staff)
        admin = obj_build.make_admin_user(self.course)
        self.client.force_authenticate(admin)

        response = self.client.get(self.base_url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

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

        self.assertCountEqual(expected, response.data['results'])

    def test_staff_get_results_past_deadline_ultimate_scores_shown(self):
        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best,
            hide_ultimate_submission_fdbk=False
        )

        student_group = self._make_group_with_submissions(1, 2)
        staff_group = self._make_group_with_submissions(1, members_role=obj_build.UserRole.staff)

        expected = [
            self._make_result_content_for_user(
                student_group.member_names[0], student_group,
                student_group.submissions.last(), points_only=True),
            self._make_result_content_for_user(
                staff_group.member_names[0], staff_group, staff_group.submissions.first(),
                points_only=True)

        ]

        staff = obj_build.make_staff_user(self.course)
        self.client.force_authenticate(staff)

        past_closing_time = timezone.now() - datetime.timedelta(hours=1)
        for closing_time in past_closing_time, None:
            self.project.validate_and_update(closing_time=closing_time)

            response = self.client.get(self.base_url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)

            self.assertCountEqual(expected, response.data['results'])

    def test_get_results_with_result_details(self):
        self.fail()

    def test_get_results_exclude_staff(self):
        self.fail()

    def test_get_results_custom_page_size(self):
        self.fail()

    def test_non_staff_get_results_permission_denied(self):
        self.fail()

    def test_staff_get_results_deadline_not_past_permission_denied(self):
        self.fail()

    def test_staff_get_results_ultimate_scores_hidden_permission_denied(self):
        self.fail()

    def test_get_results_group_has_extension_ultimate_submission_is_null(self):
        self.fail()
