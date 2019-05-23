import datetime
from unittest import mock

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.submission_feedback import update_denormalized_ag_test_results
from autograder.rest_api.tests.test_views.ag_view_test_base import AGViewTestBase
from autograder.utils.testing import UnitTestBase


class _SetUp(AGViewTestBase):
    def setUp(self):
        super().setUp()

        self.client = APIClient()

        self.ag_test_cmd = obj_build.make_full_ag_test_command(set_arbitrary_points=True)
        self.ag_test_case = self.ag_test_cmd.ag_test_case
        self.ag_test_suite = self.ag_test_case.ag_test_suite
        self.project = self.ag_test_suite.project
        self.project.validate_and_update(
            visible_to_students=True,
            hide_ultimate_submission_fdbk=False,
            closing_time=None,
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best
        )
        self.course = self.project.course


class StaffOrStudentRetrieveStudentUltimateSubmissionTestCase(_SetUp):
    def setUp(self):
        super().setUp()
        self.student_group = obj_build.make_group(project=self.project)
        self.student = self.student_group.members.first()

        self.student_group_best_submission = obj_build.make_finished_submission(
            group=self.student_group)
        self.student_best_res = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_group_best_submission)
        self.student_group_best_submission = update_denormalized_ag_test_results(
            self.student_group_best_submission.pk)

        self.student_group_most_recent_submission = obj_build.make_finished_submission(
            group=self.student_group)
        self.student_most_recent_res = obj_build.make_incorrect_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_group_most_recent_submission)
        self.student_group_most_recent_submission = update_denormalized_ag_test_results(
            self.student_group_most_recent_submission.pk)

        self.staff = obj_build.make_staff_user(self.course)

        self.url = reverse('group-ultimate-submission', kwargs={'pk': self.student_group.pk})

    def test_retrieve_ultimate_submission_deadline_past_or_none(self):
        self.do_get_object_test(self.client, self.student, self.url,
                                self.student_group_best_submission.to_dict())
        self.do_get_object_test(self.client, self.staff, self.url,
                                self.student_group_best_submission.to_dict())

        self.project.validate_and_update(
            closing_time=timezone.now() - datetime.timedelta(minutes=2))

        self.do_get_object_test(self.client, self.student, self.url,
                                self.student_group_best_submission.to_dict())
        self.do_get_object_test(self.client, self.staff, self.url,
                                self.student_group_best_submission.to_dict())

    def test_retrieve_ultimate_submission_extension_past(self):
        self.project.validate_and_update(
            closing_time=timezone.now() - datetime.timedelta(days=2))

        self.student_group.validate_and_update(
            extended_due_date=timezone.now() - datetime.timedelta(minutes=2))

        self.do_get_object_test(self.client, self.student, self.url,
                                self.student_group_best_submission.to_dict())
        self.do_get_object_test(self.client, self.staff, self.url,
                                self.student_group_best_submission.to_dict())

    def test_retrieve_ultimate_submission_late_day_finished(self):
        self.project.validate_and_update(
            closing_time=timezone.now() - datetime.timedelta(days=2))

        self.student_group.late_days_used = {self.student.username: 1}
        self.student_group.save()

        self.do_get_object_test(self.client, self.student, self.url,
                                self.student_group_best_submission.to_dict())
        self.do_get_object_test(self.client, self.staff, self.url,
                                self.student_group_best_submission.to_dict())

    def test_retrieve_ultimate_submission_extension_and_late_day_finished(self):
        self.project.validate_and_update(
            closing_time=timezone.now() - datetime.timedelta(days=3))

        self.student_group.validate_and_update(
            extended_due_date=timezone.now() - datetime.timedelta(days=2))
        self.student_group.late_days_used = {self.student.username: 1}
        self.student_group.save()

        self.do_get_object_test(self.client, self.student, self.url,
                                self.student_group_best_submission.to_dict())
        self.do_get_object_test(self.client, self.staff, self.url,
                                self.student_group_best_submission.to_dict())

    def test_deadline_not_past_permission_denied(self):
        self.project.validate_and_update(
            closing_time=timezone.now() + datetime.timedelta(hours=2))

        self.do_permission_denied_get_test(self.client, self.student, self.url)
        self.do_permission_denied_get_test(self.client, self.staff, self.url)

    def test_deadline_past_ultimate_fdbk_hidden_permission_denied(self):
        self.project.validate_and_update(hide_ultimate_submission_fdbk=True)

        self.do_permission_denied_get_test(self.client, self.student, self.url)
        self.do_permission_denied_get_test(self.client, self.staff, self.url)

        self.project.validate_and_update(
            closing_time=timezone.now() - datetime.timedelta(hours=2))

        self.do_permission_denied_get_test(self.client, self.student, self.url)
        self.do_permission_denied_get_test(self.client, self.staff, self.url)

    def test_extension_not_past_permission_denied(self):
        self.project.validate_and_update(
            closing_time=timezone.now() - datetime.timedelta(days=2))

        self.student_group.validate_and_update(
            extended_due_date=timezone.now() + datetime.timedelta(minutes=2))

        self.do_permission_denied_get_test(self.client, self.student, self.url)
        self.do_permission_denied_get_test(self.client, self.staff, self.url)

    def test_extension_past_ultimate_fdbk_hidden_permission_denied(self):
        self.project.validate_and_update(
            closing_time=timezone.now() - datetime.timedelta(days=2),
            hide_ultimate_submission_fdbk=True
        )

        self.student_group.validate_and_update(
            extended_due_date=timezone.now() - datetime.timedelta(minutes=2))

        self.do_permission_denied_get_test(self.client, self.student, self.url)
        self.do_permission_denied_get_test(self.client, self.staff, self.url)

    def test_late_day_pending_permission_denied_for_student_not_staff(self):
        self.project.validate_and_update(
            closing_time=timezone.now() - datetime.timedelta(hours=12))

        self.student_group.late_days_used = {self.student.username: 1}
        self.student_group.save()

        self.do_permission_denied_get_test(self.client, self.student, self.url)
        # See autograder.rest_api.permissions.deadline_is_past for
        # details on this edge case.
        self.do_get_object_test(self.client, self.staff, self.url,
                                self.student_group_best_submission.to_dict())

    def test_late_day_finished_ultimate_fdbk_hidden_permission_denied(self):
        self.project.validate_and_update(
            closing_time=timezone.now() - datetime.timedelta(days=3),
            hide_ultimate_submission_fdbk=True)

        self.student_group.late_days_used = {self.student.username: 1}
        self.student_group.save()

        self.do_permission_denied_get_test(self.client, self.student, self.url)
        self.do_permission_denied_get_test(self.client, self.staff, self.url)

        self.student_group.validate_and_update(
            extended_due_date=timezone.now() - datetime.timedelta(days=2))

        self.do_permission_denied_get_test(self.client, self.student, self.url)
        self.do_permission_denied_get_test(self.client, self.staff, self.url)

    def test_no_submissions_404(self):
        self.student_group.submissions.all().delete()

        self.do_get_request_404_test(self.client, self.student, self.url)
        self.do_get_request_404_test(self.client, self.staff, self.url)

    def test_no_finished_submissions_404(self):
        self.student_group.submissions.all().update(
            status=ag_models.Submission.GradingStatus.waiting_for_deferred)

        self.do_get_request_404_test(self.client, self.student, self.url)
        self.do_get_request_404_test(self.client, self.staff, self.url)

    def test_project_hidden_permission_denied(self):
        self.project.validate_and_update(visible_to_students=False)
        self.do_permission_denied_get_test(self.client, self.student, self.url)

        self.course.students.clear()

        self.project.validate_and_update(guests_can_submit=True)
        self.do_permission_denied_get_test(self.client, self.student, self.url)

    def test_student_get_other_student_ultimate_submission_permission_denied(self):
        other_student = obj_build.make_student_user(self.course)
        self.do_permission_denied_get_test(self.client, other_student, self.url)

    def test_handgrader_get_student_ultimate_submission_permission_denied(self):
        handgrader = obj_build.make_handgrader_user(self.course)
        self.do_permission_denied_get_test(self.client, handgrader, self.url)


class StaffRetrieveOwnUltimateSubmissionTestCase(_SetUp):
    def test_staff_can_always_retrieve_own_ultimate_submission(self):
        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.staff)
        staff = group.members.first()
        submission = obj_build.make_finished_submission(group=group)

        url = reverse('group-ultimate-submission', kwargs={'pk': group.pk})

        self.do_get_object_test(self.client, staff, url, submission.to_dict())

        self.project.validate_and_update(
            visible_to_students=False,
            closing_time=timezone.now() + datetime.timedelta(hours=1))

        self.do_get_object_test(self.client, staff, url, submission.to_dict())

        group.validate_and_update(
            extended_due_date=self.project.closing_time + datetime.timedelta(days=1))

        self.do_get_object_test(self.client, staff, url, submission.to_dict())


class UltimateSubmissionLateDayEdgeCases(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_get_ultimate_submission_most_recent_submission_doesnt_count_for_user(self):
        project = obj_build.make_project(
            visible_to_students=True, hide_ultimate_submission_fdbk=False,
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.most_recent
        )
        course = project.course

        counts_for_user = obj_build.make_student_user(course)
        does_not_count_for_user = obj_build.make_student_user(course)

        group = obj_build.make_group(
            members=[counts_for_user, does_not_count_for_user],
            project=project
        )
        url = reverse('group-ultimate-submission', kwargs={'pk': group.pk})

        second_most_recent_submission = obj_build.make_finished_submission(group=group)
        most_recent_submission = obj_build.make_finished_submission(
            group=group, does_not_count_for=[does_not_count_for_user.username]
        )

        self.client.force_authenticate(counts_for_user)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(most_recent_submission.to_dict(), response.data)

        self.client.force_authenticate(does_not_count_for_user)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(second_most_recent_submission.to_dict(), response.data)

    def test_user_passed_to_get_ultimate_submission_func(self):
        project = obj_build.make_project(
            visible_to_students=True, hide_ultimate_submission_fdbk=False)
        group = obj_build.make_group(project=project)
        url = reverse('group-ultimate-submission', kwargs={'pk': group.pk})

        mocked_get_ultimate_submission = mock.Mock(return_value=None)

        with mock.patch('autograder.rest_api.views.group_views.get_ultimate_submission',
                        new=mocked_get_ultimate_submission):
            self.client.force_authenticate(group.members.first())
            response = self.client.get(url)
            self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

            mocked_get_ultimate_submission.assert_called_once_with(
                group, user=group.members.first())
