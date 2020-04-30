import datetime
import os
import random
from typing import Iterable, List, Optional
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import QueryDict
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder import utils
from autograder.core.submission_feedback import update_denormalized_ag_test_results
from autograder.rest_api.tests.test_views.ag_view_test_base import AGViewTestBase
from autograder.utils.testing import UnitTestBase


def submissions_url(group: ag_models.Group) -> str:
    return reverse('submissions', kwargs={'pk': group.pk})


class ListSubmissionsTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.maxDiff = None

        self.client = APIClient()
        self.project = obj_build.make_project()
        self.course = self.project.course

    def test_staff_list_submissions_for_any_group(self):
        staff = obj_build.make_staff_user(self.course)
        self._do_list_submissions_test(staff, group_role=obj_build.UserRole.admin)
        self._do_list_submissions_test(staff, group_role=obj_build.UserRole.staff)
        self._do_list_submissions_test(staff, group_role=obj_build.UserRole.student)
        self._do_list_submissions_test(staff, group_role=obj_build.UserRole.guest)

    def _do_list_submissions_test(self, requester: User, group_role: obj_build.UserRole) -> None:
        group = obj_build.make_group(project=self.project, members_role=group_role)
        submissions = self._make_submissions(group)
        self.do_list_objects_test(
            self.client, requester, submissions_url(group),
            [submission.to_dict() for submission in submissions]
        )

    def test_student_list_submissions_for_own_group(self):
        self.project.validate_and_update(visible_to_students=True)

        student_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.student)
        submissions = self._make_submissions(student_group)

        self.do_list_objects_test(
            self.client, student_group.members.first(), submissions_url(student_group),
            [submission.to_dict() for submission in submissions]
        )

    def test_guest_list_submissions_for_own_group(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        guest_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.guest)
        submissions = self._make_submissions(guest_group)

        self.do_list_objects_test(
            self.client, guest_group.members.first(), submissions_url(guest_group),
            [submission.to_dict() for submission in submissions]
        )

    def test_handgrader_list_student_group_submissions_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        student_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.student)
        submissions = self._make_submissions(student_group)

        handgrader = obj_build.make_handgrader_user(self.course)
        self.do_permission_denied_get_test(
            self.client, handgrader, submissions_url(student_group))

    def test_non_group_member_list_submissions_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        student_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.student)
        submissions = self._make_submissions(student_group)

        other_student = obj_build.make_student_user(self.course)
        self.do_permission_denied_get_test(
            self.client, other_student, submissions_url(student_group))

    def test_student_list_submissions_project_hidden_permission_denied(self):
        self.project.validate_and_update(visible_to_students=False, guests_can_submit=True)

        student_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.student)
        submissions = self._make_submissions(student_group)

        self.do_permission_denied_get_test(
            self.client, student_group.members.first(), submissions_url(student_group))

    def test_guest_list_submissions_project_hidden_permission_denied(self):
        self.project.validate_and_update(visible_to_students=False, guests_can_submit=True)

        guest_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.guest)
        submissions = self._make_submissions(guest_group)

        self.do_permission_denied_get_test(
            self.client, guest_group.members.first(), submissions_url(guest_group))

    def test_guest_list_submissions_project_private_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=False)

        guest_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.guest)
        submissions = self._make_submissions(guest_group)

        self.do_permission_denied_get_test(
            self.client, guest_group.members.first(), submissions_url(guest_group))

    def _make_submissions(
        self, group: ag_models.Group, num_submissions=4
    ) -> List[ag_models.Submission]:
        return [obj_build.make_finished_submission(group) for i in range(num_submissions)]


class CreateSubmissionTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.maxDiff = None

        self.client = APIClient()
        self.project = obj_build.make_project()
        self.course = self.project.course

    def test_admin_or_staff_submit(self):
        self.project.validate_and_update(
            closing_time=timezone.now() + timezone.timedelta(minutes=1))
        admin_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.admin)
        self.do_normal_submit_test(admin_group, admin_group.members.last())

        staff_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.staff)
        self.do_normal_submit_test(staff_group, staff_group.members.last())

    def test_staff_submit_deadline_past(self):
        self.project.validate_and_update(
            closing_time=timezone.now() + timezone.timedelta(seconds=-1))

        staff_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.staff)
        self.do_normal_submit_test(staff_group, staff_group.members.last())

    def test_admin_or_staff_submit_submissions_disallowed(self):
        self.project.validate_and_update(disallow_student_submissions=True)

        staff_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.staff)
        self.do_normal_submit_test(staff_group, staff_group.members.last())

    def test_student_submit(self):
        closing_time = timezone.now() + timezone.timedelta(minutes=1)
        self.project.validate_and_update(visible_to_students=True, closing_time=closing_time)

        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.student)
        self.do_normal_submit_test(group, group.members.last())

    def test_guest_submit(self):
        closing_time = timezone.now() + timezone.timedelta(minutes=1)
        self.project.validate_and_update(
            closing_time=closing_time, visible_to_students=True, guests_can_submit=True)

        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.guest)
        self.do_normal_submit_test(group, group.members.first())

    def test_no_files_submitted(self) -> None:
        group = obj_build.make_group()
        group.project.validate_and_update(visible_to_students=True)
        response = self.do_create_object_test(
            ag_models.Submission.objects, self.client, group.members.first(),
            submissions_url(group),
            {'submitted_files': []},
            format='multipart', check_data=False
        )

        submission = ag_models.Submission.objects.get(pk=response.data['pk'])
        self.assertEqual(submission.to_dict(), response.data)

        self.assertEqual([], submission.submitted_filenames)

    def test_any_group_submit_no_closing_time(self):
        self.project.validate_and_update(
            closing_time=None, visible_to_students=True, guests_can_submit=True)

        admin_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.admin)
        self.do_normal_submit_test(admin_group, admin_group.members.first())

        staff_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.staff)
        self.do_normal_submit_test(staff_group, staff_group.members.first())

        student_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.student)
        self.do_normal_submit_test(student_group, student_group.members.first())

        guest_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.guest)
        self.do_normal_submit_test(guest_group, guest_group.members.first())

        handgrader_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.handgrader)
        self.do_normal_submit_test(handgrader_group, handgrader_group.members.first())

    def test_submit_missing_and_discarded_files_tracked(self):
        self.project.validate_and_update(visible_to_students=True)
        self.add_expected_patterns(self.project)
        group = obj_build.make_group(project=self.project)
        self.client.force_authenticate(group.members.first())

        bad_filename = 'not a needed file'
        request_data = {
            'submitted_files': [
                SimpleUploadedFile(bad_filename, b'merp')]}
        response = self.client.post(
            submissions_url(group), request_data, format='multipart')

        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertCountEqual([], response.data['submitted_filenames'])
        self.assertCountEqual([bad_filename],
                              response.data['discarded_files'])
        self.assertIn('*.txt', response.data['missing_files'])
        self.assertIn('spam.cpp', response.data['missing_files'])

    # Note that non-group members in this case includes staff, admin, and handgrader.
    def test_non_group_member_submit_permission_denied(self) -> None:
        self.project.validate_and_update(visible_to_students=True)
        group = obj_build.make_group(project=self.project)
        other_user = obj_build.make_student_user(self.course)

        admin = obj_build.make_admin_user(self.course)
        staff = obj_build.make_staff_user(self.course)
        student = obj_build.make_student_user(self.course)
        guest = obj_build.make_user()
        handgrader = obj_build.make_handgrader_user(self.course)

        for user in admin, staff, student, guest, handgrader:
            self.do_permission_denied_submit_test(group, user)

    def test_handgraders_that_are_also_students_submit(self) -> None:
        self.project.validate_and_update(visible_to_students=True)
        group = obj_build.make_group(project=self.project)
        handgrader = group.members.last()
        self.project.course.handgraders.add(handgrader)
        self.do_normal_submit_test(group, handgrader)

    def test_student_submit_hidden_project_permission_denied(self):
        self.project.validate_and_update(visible_to_students=False, guests_can_submit=True)
        group = obj_build.make_group(project=self.project)
        self.do_permission_denied_submit_test(group, group.members.first())

    def test_guest_submit_hidden_project_permission_denied(self):
        self.project.validate_and_update(visible_to_students=False, guests_can_submit=True)
        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.guest)
        self.do_permission_denied_submit_test(group, group.members.first())

    def test_guest_submit_private_project_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=False)
        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.guest)
        self.do_permission_denied_submit_test(group, group.members.first())

    def test_non_staff_submit_deadline_past(self):
        self.project.validate_and_update(
            closing_time=timezone.now() + timezone.timedelta(seconds=-1),
            visible_to_students=True, guests_can_submit=True)

        student_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.student)
        response = self.do_bad_request_submit_test(student_group, student_group.members.first())
        self.assertIn('submission', response.data)

        guest_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.guest)
        response = self.do_bad_request_submit_test(guest_group, guest_group.members.first())
        self.assertIn('submission', response.data)

    def test_non_staff_submit_deadline_past_but_has_extension(self):
        closing_time = timezone.now() + timezone.timedelta(seconds=-1)
        self.project.validate_and_update(
            visible_to_students=True, guests_can_submit=True,
            closing_time=closing_time)

        student_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.student)
        guest_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.guest)

        for group in student_group, guest_group:
            extension = timezone.now() + timezone.timedelta(minutes=1)
            group.validate_and_update(extended_due_date=extension)
            self.do_normal_submit_test(group, group.members.last())

    def test_non_staff_submit_deadline_and_extension_past(self) -> None:
        closing_time = timezone.now() + timezone.timedelta(minutes=-1)
        self.project.validate_and_update(
            visible_to_students=True, guests_can_submit=True,
            closing_time=closing_time)

        student_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.student)
        guest_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.guest)

        for group in student_group, guest_group:
            extension = timezone.now() + timezone.timedelta(seconds=-1)
            group.validate_and_update(extended_due_date=extension)
            response = self.do_bad_request_submit_test(group, group.members.first())
            self.assertIn('submission', response.data)

    def test_non_staff_submit_submissions_disallowed(self) -> None:
        self.project.validate_and_update(
            visible_to_students=True, guests_can_submit=True,
            disallow_student_submissions=True)

        student_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.student)
        guest_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.guest)

        future_closing_time = timezone.now() + timezone.timedelta(minutes=1)

        for group in student_group, guest_group:
            for closing_time in None, future_closing_time:
                self.project.validate_and_update(closing_time=closing_time)
                response = self.do_bad_request_submit_test(group, group.members.first())
                self.assertIn('submission', response.data)

    def test_any_group_already_has_submission_being_processed(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        for group in self._all_roles_groups():
            ag_models.Submission.objects.validate_and_create([], group=group)
            response = self.do_bad_request_submit_test(group, group.members.last())
            self.assertIn('submission', response.data)

    def _all_roles_groups(self) -> List[ag_models.Group]:
        return [
            obj_build.make_group(
                project=self.project, members_role=obj_build.UserRole.admin),
            obj_build.make_group(
                project=self.project, members_role=obj_build.UserRole.staff),
            obj_build.make_group(
                project=self.project, members_role=obj_build.UserRole.student),
            obj_build.make_group(
                project=self.project, members_role=obj_build.UserRole.guest),
        ]

    def test_can_resubmit_non_being_processed_status(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        resubmittable_statuses = list(
            set(ag_models.Submission.GradingStatus.values)
            - set(ag_models.Submission.GradingStatus.active_statuses)
        )

        for group in self._all_roles_groups():
            for grading_status in resubmittable_statuses:
                obj_build.make_submission(group=group, status=grading_status)
                self.do_normal_submit_test(group, group.members.first())

    def test_no_submission_limit(self) -> None:
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        self.assertIsNone(self.project.submission_limit_per_day)
        for group in self._all_roles_groups():
            for i in range(5):
                self.do_normal_submit_test(group, group.members.first())

    def test_submission_not_past_limit(self) -> None:
        limit = 3
        self.project.validate_and_update(
            submission_limit_per_day=limit, visible_to_students=True, guests_can_submit=True)

        for group in self._all_roles_groups():
            for i in range(limit):
                self.do_normal_submit_test(group, group.members.last())

    def test_submission_past_limit_allowed(self) -> None:
        limit = 3
        self.project.validate_and_update(
            submission_limit_per_day=limit,
            allow_submissions_past_limit=True,
            visible_to_students=True, guests_can_submit=True)
        for group in self._all_roles_groups():
            for i in range(limit):
                submission = self.do_normal_submit_test(group, group.members.last())
                self.assertFalse(submission.is_past_daily_limit)

            for i in range(2):
                past_limit = self.do_normal_submit_test(group, group.members.last())
                self.assertTrue(past_limit)

    def test_submission_past_limit_not_allowed_bad_request(self) -> None:
        limit = 2
        self.project.validate_and_update(
            submission_limit_per_day=limit,
            allow_submissions_past_limit=False,
            visible_to_students=True, guests_can_submit=True)

        student_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.student)
        guest_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.guest)

        for group in student_group, guest_group:
            for i in range(limit):
                self.do_normal_submit_test(group, group.members.first())

            for i in range(3):
                response = self.do_bad_request_submit_test(group, group.members.first())
                self.assertIn('submission', response.data)
            self.assertEqual(limit, group.submissions.count())

            for sub in group.submissions.all():
                self.assertFalse(sub.is_past_daily_limit)

    def test_submission_past_limit_not_allowed_but_group_has_bonus_submission(self):
        num_bonus_submissions = 2
        limit = 3
        project = obj_build.make_project(
            visible_to_students=True,
            submission_limit_per_day=limit,
            allow_submissions_past_limit=False,
            num_bonus_submissions=num_bonus_submissions
        )
        group = obj_build.make_group(project=project)
        self.assertEqual(num_bonus_submissions, group.bonus_submissions_remaining)
        for i in range(limit + num_bonus_submissions):
            self.do_normal_submit_test(group, group.members.first())

        response = self.do_bad_request_submit_test(group, group.members.first())
        self.assertIn('submission', response.data)

    def test_admin_or_staff_submissions_never_count_towards_limit(self):
        limit = 1
        num_submissions = limit + 4
        self.project.validate_and_update(submission_limit_per_day=limit)

        admin_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.admin)
        staff_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.staff)

        for group in admin_group, staff_group:
            for i in range(num_submissions):
                self.do_normal_submit_test(group, group.members.last())

            self.assertEqual(num_submissions, group.submissions.count())

    def test_group_members_combine_submissions_per_day(self):
        self.project.validate_and_update(
            groups_combine_daily_submissions=True,
            submission_limit_per_day=1,
            allow_submissions_past_limit=False,
            visible_to_students=True, guests_can_submit=True)

        alone = obj_build.make_group(num_members=1, project=self.project)
        partner = obj_build.make_group(num_members=2, project=self.project)
        trio = obj_build.make_group(num_members=3, project=self.project)

        self.do_normal_submit_test(alone, alone.members.first())
        self.do_bad_request_submit_test(alone, alone.members.first())

        for i in range(2):
            self.do_normal_submit_test(partner, partner.members.first())
        self.do_bad_request_submit_test(partner, partner.members.first())

        for i in range(3):
            self.do_normal_submit_test(trio, trio.members.first())
        self.do_bad_request_submit_test(trio, trio.members.first())

    def test_group_members_combine_submissions_per_day_allow_past_limit(self):
        self.project.validate_and_update(
            groups_combine_daily_submissions=True,
            submission_limit_per_day=1,
            allow_submissions_past_limit=True,
            visible_to_students=True, guests_can_submit=True)

        alone = obj_build.make_group(num_members=1, project=self.project)
        partner = obj_build.make_group(num_members=2, project=self.project)
        trio = obj_build.make_group(num_members=3, project=self.project)

        submission = self.do_normal_submit_test(alone, alone.members.first())
        self.assertFalse(submission.is_past_daily_limit)
        past_limit = self.do_normal_submit_test(alone, alone.members.first())
        self.assertTrue(past_limit.is_past_daily_limit)

        for i in range(2):
            submission = self.do_normal_submit_test(partner, partner.members.first())
            self.assertFalse(submission.is_past_daily_limit)

        past_limit = self.do_normal_submit_test(partner, partner.members.first())
        self.assertTrue(past_limit.is_past_daily_limit)

        for i in range(3):
            submission = self.do_normal_submit_test(trio, trio.members.first())
            self.assertFalse(submission.is_past_daily_limit)

        past_limit = self.do_normal_submit_test(trio, trio.members.first())
        self.assertTrue(past_limit.is_past_daily_limit)

    def test_invalid_fields_fields_other_than_submitted_files_in_request(self):
        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.admin)
        response = self.do_invalid_create_object_test(
            group.submissions, self.client,
            group.members.first(),
            submissions_url(group),
            {'submitted_files': self.files_to_submit, 'count_towards_total_limit': False},
            format='multipart')
        self.assertIn('invalid_fields', response.data)
        self.assertIn('count_towards_total_limit', response.data['invalid_fields'])

    def do_normal_submit_test(self, group, user) -> ag_models.Submission:
        self.add_expected_patterns(group.project)
        response = self.do_create_object_test(
            ag_models.Submission.objects, self.client, user,
            submissions_url(group),
            {'submitted_files': self.files_to_submit},
            format='multipart', check_data=False)

        submission = ag_models.Submission.objects.get(pk=response.data['pk'])
        self.assertEqual(submission.to_dict(), response.data)

        # We don't know the exact timestamp assigned by the server, so
        # make sure it's reasonably close to what it should be.
        timestamp_difference = submission.timestamp - timezone.now()
        self.assertLess(timestamp_difference, timezone.timedelta(seconds=2))

        self.assertEqual(group.pk, response.data['group'])
        self.assertEqual(ag_models.Submission.GradingStatus.received,
                         response.data['status'])
        self.assertCountEqual([file_.name for file_ in self.files_to_submit],
                              response.data['submitted_filenames'])
        self.assertCountEqual([], response.data['missing_files'])
        self.assertCountEqual([], response.data['discarded_files'])
        self.assertEqual(user.username, response.data['submitter'])

        submission.status = ag_models.Submission.GradingStatus.finished_grading
        submission.save()

        return submission

    @property
    def files_to_submit(self):
        return [
            SimpleUploadedFile('spam.cpp', b'steve'),
            SimpleUploadedFile('egg.txt', b'stave'),
            SimpleUploadedFile('sausage.txt', b'stove')
        ]

    def add_expected_patterns(self, project):
        if project.expected_student_files.count():
            return

        ag_models.ExpectedStudentFile.objects.validate_and_create(
            pattern='spam.cpp', project=project)
        ag_models.ExpectedStudentFile.objects.validate_and_create(
            pattern='*.txt', project=project, max_num_matches=3)

    def do_permission_denied_submit_test(self, group, user):
        self.add_expected_patterns(group.project)
        return self.do_permission_denied_create_test(
            ag_models.Submission.objects, self.client,
            user, submissions_url(group),
            {'submitted_files': self.files_to_submit}, format='multipart')

    def do_bad_request_submit_test(self, group, user):
        self.add_expected_patterns(group.project)
        return self.do_invalid_create_object_test(
            group.submissions, self.client, user,
            submissions_url(group),
            {'submitted_files': self.files_to_submit}, format='multipart')


class CreateSubmissionWithLateDaysTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.client = APIClient()

        self.num_late_days = 3
        self.course = obj_build.make_course(num_late_days=self.num_late_days)

        self.closing_time = timezone.now()
        self.project = obj_build.make_project(
            self.course, closing_time=self.closing_time, visible_to_students=True,
            allow_late_days=True)
        self.group = obj_build.make_group(2, project=self.project)

    def test_submission_uses_late_day(self):
        submitter = self.group.members.first()
        self.submit(self.group, submitter,
                    self.closing_time + datetime.timedelta(hours=1),
                    expect_failure=False)
        self.group.refresh_from_db()

        for user in self.group.members.all():
            self.assertEqual(1, self.group.late_days_used[user.username])

            remaining = ag_models.LateDaysRemaining.objects.get(user=user, course=self.course)
            self.assertEqual(self.num_late_days - 1, remaining.late_days_remaining)

    def test_multiple_submissions_in_one_late_day(self):
        submitter = self.group.members.first()
        self.submit(self.group, submitter,
                    self.closing_time + datetime.timedelta(hours=1),
                    expect_failure=False)
        self.group.refresh_from_db()

        for user in self.group.members.all():
            self.assertEqual(1, self.group.late_days_used[user.username])

            remaining = ag_models.LateDaysRemaining.objects.get(user=user, course=self.course)
            self.assertEqual(self.num_late_days - 1, remaining.late_days_remaining)

        self.submit(self.group, submitter,
                    self.closing_time + datetime.timedelta(hours=2),
                    expect_failure=False)
        self.group.refresh_from_db()

        for user in self.group.members.all():
            self.assertEqual(1, self.group.late_days_used[user.username])

            remaining = ag_models.LateDaysRemaining.objects.get(user=user, course=self.course)
            self.assertEqual(self.num_late_days - 1, remaining.late_days_remaining)

    def test_multiple_late_days_used_one_at_a_time_same_project(self):
        submitter = self.group.members.first()
        self.submit(self.group, submitter,
                    self.closing_time + datetime.timedelta(hours=1),
                    expect_failure=False)
        self.group.refresh_from_db()

        for user in self.group.members.all():
            self.assertEqual(1, self.group.late_days_used[user.username])

            remaining = ag_models.LateDaysRemaining.objects.get(user=user, course=self.course)
            self.assertEqual(self.num_late_days - 1, remaining.late_days_remaining)

        self.submit(self.group, submitter,
                    self.closing_time + datetime.timedelta(days=1, hours=1),
                    expect_failure=False)
        self.group.refresh_from_db()

        for user in self.group.members.all():
            self.assertEqual(2, self.group.late_days_used[user.username])

            remaining = ag_models.LateDaysRemaining.objects.get(user=user, course=self.course)
            self.assertEqual(self.num_late_days - 2, remaining.late_days_remaining)

    def test_multiple_late_days_used_by_one_submission(self):
        submitter = self.group.members.first()
        self.submit(self.group, submitter,
                    self.closing_time + datetime.timedelta(days=1, hours=1),
                    expect_failure=False)
        self.group.refresh_from_db()

        for user in self.group.members.all():
            self.assertEqual(2, self.group.late_days_used[user.username])

            remaining = ag_models.LateDaysRemaining.objects.get(user=user, course=self.course)
            self.assertEqual(self.num_late_days - 2, remaining.late_days_remaining)

    def test_multiple_late_days_used_different_projects(self):
        other_project = obj_build.make_project(
            self.course, closing_time=self.closing_time, visible_to_students=True,
            allow_late_days=True)
        other_group = ag_models.Group.objects.validate_and_create(
            members=list(self.group.members.all()),
            check_group_size_limits=False,
            project=other_project
        )

        submitter = self.group.members.first()
        self.submit(self.group, submitter,
                    self.closing_time + datetime.timedelta(hours=1),
                    expect_failure=False)
        self.group.refresh_from_db()

        for user in self.group.members.all():
            self.assertEqual(1, self.group.late_days_used[user.username])

            remaining = ag_models.LateDaysRemaining.objects.get(user=user, course=self.course)
            self.assertEqual(self.num_late_days - 1, remaining.late_days_remaining)

        self.submit(other_group, submitter,
                    self.closing_time + datetime.timedelta(hours=1),
                    expect_failure=False)
        self.group.refresh_from_db()
        other_group.refresh_from_db()

        for user in other_group.members.all():
            self.assertEqual(1, self.group.late_days_used[user.username])
            self.assertEqual(1, other_group.late_days_used[user.username])

            remaining = ag_models.LateDaysRemaining.objects.get(user=user, course=self.course)
            self.assertEqual(self.num_late_days - 2, remaining.late_days_remaining)

    def test_late_days_used_on_top_of_extension(self):
        extension = self.closing_time + datetime.timedelta(days=2)
        self.group.validate_and_update(extended_due_date=extension)

        submitter = self.group.members.first()
        self.submit(self.group, submitter,
                    self.closing_time + datetime.timedelta(hours=1),
                    expect_failure=False)
        self.group.refresh_from_db()
        self.assertEqual({}, self.group.late_days_used)

        self.submit(self.group, submitter, extension + datetime.timedelta(hours=1),
                    expect_failure=False)
        self.group.refresh_from_db()

        for user in self.group.members.all():
            self.assertEqual(1, self.group.late_days_used[user.username])

            remaining = ag_models.LateDaysRemaining.objects.get(user=user, course=self.course)
            self.assertEqual(self.num_late_days - 1, remaining.late_days_remaining)

    def test_user_with_no_late_days_in_group_cannot_submit_after_deadline(self):
        submitter = self.group.members.first()
        late_days_remaining = ag_models.LateDaysRemaining.objects.validate_and_create(
            user=submitter, course=self.course)
        late_days_remaining.late_days_used = self.num_late_days
        late_days_remaining.save()

        self.submit(self.group, submitter,
                    self.closing_time + datetime.timedelta(hours=1),
                    expect_failure=True)
        self.group.refresh_from_db()

        self.assertNotIn(submitter.username, self.group.late_days_used)
        actual_remaining = ag_models.LateDaysRemaining.objects.get(
            user=submitter, course=self.course)
        self.assertEqual(0, actual_remaining.late_days_remaining)

        for user in self.group.members.exclude(pk=submitter.pk):
            self.assertNotIn(user.username, self.group.late_days_used)

            self.assertFalse(
                ag_models.LateDaysRemaining.objects.filter(user=user, course=self.course).exists())

    def test_user_with_not_enough_late_days_in_group_cannot_submit_after_deadline(self):
        submitter = self.group.members.first()
        late_days_remaining = ag_models.LateDaysRemaining.objects.validate_and_create(
            user=submitter, course=self.course)
        late_days_remaining.late_days_used = self.num_late_days - 1
        late_days_remaining.save()

        self.group.late_days_used[submitter.username] = 1
        self.group.save()

        self.submit(self.group, submitter,
                    self.closing_time + datetime.timedelta(days=2, hours=1),
                    expect_failure=True)
        self.group.refresh_from_db()

        actual_remaining = ag_models.LateDaysRemaining.objects.get(
            user=submitter, course=self.course)
        self.assertEqual(1, actual_remaining.late_days_remaining)

    def test_non_submitting_member_has_no_late_days_submission_does_not_count_for_them(self):
        submitter = self.group.members.first()
        non_submitter = self.group.members.exclude(pk=submitter.pk).first()
        late_days_remaining = ag_models.LateDaysRemaining.objects.validate_and_create(
            user=non_submitter, course=self.course)
        late_days_remaining.late_days_used = self.num_late_days
        late_days_remaining.save()

        submission = self.submit(self.group, submitter,
                                 self.closing_time + datetime.timedelta(hours=1),
                                 expect_failure=False)
        self.assertEqual([non_submitter.username], submission.does_not_count_for)

        self.group.refresh_from_db()

        self.assertEqual(1, self.group.late_days_used[submitter.username])

        remaining = ag_models.LateDaysRemaining.objects.get(user=submitter, course=self.course)
        self.assertEqual(self.num_late_days - 1, remaining.late_days_remaining)

        non_submitter_remaining = ag_models.LateDaysRemaining.objects.get(
            user=non_submitter, course=self.course)
        self.assertEqual(0, non_submitter_remaining.late_days_remaining)

    def test_non_submitting_member_has_too_few_late_days_submission_does_not_count_for_them(self):
        submitter = self.group.members.first()
        non_submitter = self.group.members.exclude(pk=submitter.pk).first()
        late_days_remaining = ag_models.LateDaysRemaining.objects.validate_and_create(
            user=non_submitter, course=self.course)
        late_days_remaining.late_days_used = self.num_late_days - 1
        late_days_remaining.save()

        submission = self.submit(self.group, submitter,
                                 self.closing_time + datetime.timedelta(days=1, hours=1),
                                 expect_failure=False)
        self.assertEqual([non_submitter.username], submission.does_not_count_for)

        self.group.refresh_from_db()

        self.assertEqual(2, self.group.late_days_used[submitter.username])

        remaining = ag_models.LateDaysRemaining.objects.get(user=submitter, course=self.course)
        self.assertEqual(self.num_late_days - 2, remaining.late_days_remaining)

        non_submitter_remaining = ag_models.LateDaysRemaining.objects.get(
            user=non_submitter, course=self.course)
        self.assertEqual(1, non_submitter_remaining.late_days_remaining)

        self.assertNotIn(non_submitter.username, self.group.late_days_used)

    def test_group_with_no_late_days_cannot_submit_past_deadline(self):
        for user in self.group.members.all():
            late_days_remaining = ag_models.LateDaysRemaining.objects.validate_and_create(
                user=user, course=self.course)
            late_days_remaining.late_days_used = self.num_late_days
            late_days_remaining.save()

            self.submit(self.group, user,
                        self.closing_time + datetime.timedelta(hours=1),
                        expect_failure=True)

    def test_submit_far_past_deadline_not_enough_late_days_late_day_total_preserved(self):
        for user in self.group.members.all():
            ag_models.LateDaysRemaining.objects.validate_and_create(user=user, course=self.course)

        for user in self.group.members.all():
            self.submit(self.group, user,
                        self.closing_time + datetime.timedelta(days=self.num_late_days, hours=1),
                        expect_failure=True)
            self.group.refresh_from_db()

            self.assertNotIn(user.username, self.group.late_days_used)

            remaining = ag_models.LateDaysRemaining.objects.get(user=user, course=self.course)
            self.assertEqual(self.num_late_days, remaining.late_days_remaining)

    def test_late_day_use_disallowed_for_project(self):
        self.project.validate_and_update(allow_late_days=False)
        for user in self.group.members.all():
            self.submit(self.group, user,
                        self.closing_time + datetime.timedelta(hours=1),
                        expect_failure=True)
            self.group.refresh_from_db()

            self.assertNotIn(user.username, self.group.late_days_used)

            self.assertFalse(
                ag_models.LateDaysRemaining.objects.filter(user=user, course=self.course).exists())

    def test_late_days_allowed_but_no_closing_time(self):
        self.project.validate_and_update(closing_time=None, soft_closing_time=timezone.now())

        submitter = self.group.members.first()
        self.submit(self.group, submitter,
                    timezone.now() + datetime.timedelta(hours=1),
                    expect_failure=False)
        self.group.refresh_from_db()

        for user in self.group.members.all():
            self.assertNotIn(user.username, self.group.late_days_used)

            self.assertFalse(
                ag_models.LateDaysRemaining.objects.filter(user=user, course=self.course).exists())

    def test_bonus_submission_used_on_late_day(self):
        self.project.validate_and_update(
            submission_limit_per_day=1, allow_submissions_past_limit=False)
        self.group.validate_and_update(bonus_submissions_remaining=1)
        submitter = self.group.members.first()
        submission1 = self.submit(
            self.group, submitter, self.closing_time + datetime.timedelta(hours=1),
            expect_failure=False)
        self.assertFalse(submission1.is_past_daily_limit)
        self.assertFalse(submission1.is_bonus_submission)

        submission2 = self.submit(
            self.group, submitter, self.closing_time + datetime.timedelta(hours=1),
            expect_failure=False)
        self.assertFalse(submission2.is_past_daily_limit)
        self.assertTrue(submission2.is_bonus_submission)

        self.group.refresh_from_db()

        for user in self.group.members.all():
            self.assertEqual(1, self.group.late_days_used[user.username])

            remaining = ag_models.LateDaysRemaining.objects.get(user=user, course=self.course)
            self.assertEqual(self.num_late_days - 1, remaining.late_days_remaining)

    def test_group_out_of_daily_submissions_no_late_days_used(self):
        self.project.validate_and_update(
            submission_limit_per_day=1, allow_submissions_past_limit=False)

        submitter = self.group.members.first()
        self.submit(
            self.group, submitter, self.closing_time - datetime.timedelta(days=2),
            expect_failure=False)

        self.submit(
            self.group, submitter, self.closing_time - datetime.timedelta(days=2),
            expect_failure=True)

        self.group.refresh_from_db()

        for user in self.group.members.all():
            self.assertNotIn(user.username, self.group.late_days_used)

            self.assertFalse(
                ag_models.LateDaysRemaining.objects.filter(user=user, course=self.course).exists())

    def submit(self, group: ag_models.Group, user: User, timestamp: datetime.datetime,
               *, expect_failure: bool) -> Optional[ag_models.Submission]:
        with mock.patch('autograder.rest_api.views.submission_views.submission_views.timezone.now',
                        new=lambda: timestamp):
            self.client.force_authenticate(user)
            response = self.client.post(reverse('submissions', kwargs={'pk': group.pk}),
                                        {'submitted_files': []}, format='multipart')
            if expect_failure:
                self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
                self.assertIn('submission', response.data)
            else:
                self.assertEqual(status.HTTP_201_CREATED, response.status_code, msg=response.data)

                submission = ag_models.Submission.objects.get(pk=response.data['pk'])
                submission.status = ag_models.Submission.GradingStatus.finished_grading
                submission.save()

                return submission


class CreateSubmissionDailyLimitBookkeepingTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project(
            visible_to_students=True, allow_submissions_past_limit=True)
        self.group = obj_build.make_group(project=self.project)

        # We want to make sure that only submissions for the specified
        # group are counted, so we'll create an extra other submission
        # to make sure it isn't counted.
        other_group = obj_build.build_group()
        self.assertNotEqual(other_group, self.group)
        ag_models.Submission.objects.validate_and_create([], group=other_group)

    def test_no_daily_limit(self):
        self.assertIsNone(self.project.submission_limit_per_day)
        for i in range(10):
            sub = self._create_submission(group=self.group)
            self.assertEqual(i + 1, self.group.num_submits_towards_limit)
            self.assertFalse(sub.is_past_daily_limit)

    def test_not_past_daily_limit(self):
        limit = random.randint(2, 5)
        self.project.validate_and_update(submission_limit_per_day=limit)
        timestamp = timezone.datetime.combine(
            timezone.now().date(), self.project.submission_limit_reset_time)
        timestamp = timestamp.replace(tzinfo=timezone.now().tzinfo)
        for i in range(limit):
            sub = self._create_submission(group=self.group, timestamp=timestamp)
            self.assertEqual(i + 1, self.group.num_submits_towards_limit)
            self.assertFalse(sub.is_past_daily_limit)

        # Place submission at exact beginning of next cycle
        next_cycle_timestamp = timestamp + timezone.timedelta(days=1)
        sub = self._create_submission(group=self.group, timestamp=next_cycle_timestamp)
        self.assertFalse(sub.is_past_daily_limit)

    def test_past_daily_limit(self):
        limit = random.randint(2, 5)
        self.project.validate_and_update(submission_limit_per_day=limit)
        not_past_limit = []
        for i in range(limit):
            not_past_limit.append(self._create_submission(group=self.group))

        for i in range(2):
            sub = self._create_submission(group=self.group)
            self.assertEqual(limit + i + 1, self.group.num_submits_towards_limit)
            self.assertTrue(sub.is_past_daily_limit)

        # Verify that the status of earlier submissions hasn't changed
        for sub in not_past_limit:
            self.assertFalse(sub.is_past_daily_limit)

    def test_submissions_from_past_day_dont_affect_current_towards_limit_count(self):
        timestamp = timezone.now() - timezone.timedelta(days=3)
        limit = 2
        self.project.validate_and_update(submission_limit_per_day=limit)
        submissions = []
        for i in range(limit):
            sub = self._create_submission(group=self.group, timestamp=timestamp)
            submissions.append(sub)
            self.assertEqual(0, self.group.num_submits_towards_limit)

        for sub in submissions:
            self.assertFalse(sub.is_past_daily_limit)

    def test_num_submits_towards_limit(self):
        limit = random.randint(3, 5)
        self.project.validate_and_update(submission_limit_per_day=limit)
        total_num_submissions = limit + 2
        for i in range(total_num_submissions):
            self.assertEqual(i, self.group.num_submits_towards_limit)
            sub = self._create_submission(group=self.group)
            self.assertEqual(i + 1, self.group.num_submits_towards_limit)
            if i > limit:
                self.assertTrue(sub.is_past_daily_limit)

        self.assertEqual(total_num_submissions, self.group.num_submits_towards_limit)

    def test_num_submits_towards_limit_non_default_timezone(self):
        local_timezone = 'America/Chicago'
        now = timezone.now()
        now_local = now.astimezone(timezone.pytz.timezone(local_timezone))

        self.project.validate_and_update(
            submission_limit_reset_time=now_local - timezone.timedelta(minutes=5),
            submission_limit_reset_timezone=local_timezone)

        before_reset_time_submission = self._create_submission(
            group=self.group,
            timestamp=now - timezone.timedelta(hours=1))
        after_reset_time_submission = self._create_submission(
            group=self.group,
            timestamp=now + timezone.timedelta(hours=1))

        self.assertEqual(1, self.group.num_submits_towards_limit)

    def test_non_default_limit_reset_time_and_timezone(self):
        reset_timezone = 'America/Detroit'
        reset_datetime = timezone.now().astimezone(
            timezone.pytz.timezone(reset_timezone)
        ).replace(hour=22)
        self.project.validate_and_update(
            submission_limit_reset_time=reset_datetime.time(),
            submission_limit_reset_timezone=reset_timezone,
            submission_limit_per_day=1)

        within_limit_timestamp = reset_datetime + timezone.timedelta(hours=-23)
        within_limit_submission = self._create_submission(
            group=self.group,
            timestamp=within_limit_timestamp)
        self.assertEqual(1, self.group.num_submits_towards_limit)
        self.assertFalse(within_limit_submission.is_past_daily_limit)

        past_limit_timestamp = reset_datetime + timezone.timedelta(hours=-1)
        past_limit_submission = self._create_submission(
            group=self.group,
            timestamp=past_limit_timestamp)
        self.assertEqual(2, self.group.num_submits_towards_limit)
        self.assertTrue(past_limit_submission.is_past_daily_limit)

        next_cycle_timestamp = reset_datetime
        next_cycle_submission = self._create_submission(
            group=self.group,
            timestamp=next_cycle_timestamp)
        self.assertEqual(2, self.group.num_submits_towards_limit)
        self.assertFalse(next_cycle_submission.is_past_daily_limit)

    def test_statuses_counted_towards_limit(self):
        count_towards_limit_statuses = [
            ag_models.Submission.GradingStatus.received,
            ag_models.Submission.GradingStatus.queued,
            ag_models.Submission.GradingStatus.being_graded,
            ag_models.Submission.GradingStatus.waiting_for_deferred,
            ag_models.Submission.GradingStatus.finished_grading
        ]
        self.assertCountEqual(
            count_towards_limit_statuses,
            ag_models.Submission.GradingStatus.count_towards_limit_statuses)
        num_statuses = len(count_towards_limit_statuses)
        self.project.validate_and_update(submission_limit_per_day=1)

        not_past_limit = self._create_submission(group=self.group)
        self.assertEqual(1, self.group.num_submits_towards_limit)
        self.assertFalse(not_past_limit.is_past_daily_limit)

        for status in count_towards_limit_statuses:
            self.assertEqual(1, self.group.num_submits_towards_limit)
            submission = self._create_submission(group=self.group)
            submission.status = status
            submission.save()
            self.assertEqual(2, self.group.num_submits_towards_limit)
            self.assertTrue(submission.is_past_daily_limit)
            submission.delete()

    def test_statuses_not_counted_towards_limit(self):
        self.project.validate_and_update(submission_limit_per_day=2)
        first_sub = self._create_submission(group=self.group)
        self.assertEqual(1, self.group.num_submits_towards_limit)
        self.assertFalse(first_sub.is_past_daily_limit)

        removed_sub = self._create_submission(group=self.group)
        removed_sub.status = ag_models.Submission.GradingStatus.removed_from_queue
        removed_sub.save()
        self.assertEqual(1, self.group.num_submits_towards_limit)
        self.assertFalse(removed_sub.is_past_daily_limit)

        error_sub = self._create_submission(group=self.group)
        error_sub.status = ag_models.Submission.GradingStatus.error
        error_sub.save()
        self.assertEqual(1, self.group.num_submits_towards_limit)
        self.assertFalse(error_sub.is_past_daily_limit)

        second_sub = self._create_submission(group=self.group)
        self.assertEqual(2, self.group.num_submits_towards_limit)
        self.assertFalse(second_sub.is_past_daily_limit)

        third_sub = self._create_submission(group=self.group)
        self.assertEqual(3, self.group.num_submits_towards_limit)
        self.assertTrue(third_sub.is_past_daily_limit)

    def test_group_uses_bonus_submissions(self):
        num_bonus_submissions = 3
        limit = 5
        project = obj_build.make_project(
            visible_to_students=True,
            submission_limit_per_day=limit,
            num_bonus_submissions=num_bonus_submissions
        )
        group = obj_build.make_group(project=project)
        self.assertEqual(num_bonus_submissions, group.bonus_submissions_remaining)

        for i in range(limit):
            submission = self._create_submission(group)
            self.assertFalse(submission.is_bonus_submission)
            self.assertFalse(submission.is_past_daily_limit)

        self.assertEqual(limit, group.num_submits_towards_limit)

        for i in range(num_bonus_submissions):
            submission = self._create_submission(group)
            self.assertTrue(submission.is_bonus_submission)
            self.assertFalse(submission.is_past_daily_limit)

            group.refresh_from_db()
            self.assertEqual(num_bonus_submissions - (i + 1), group.bonus_submissions_remaining)

        self.assertEqual(limit + num_bonus_submissions, group.num_submits_towards_limit)
        self.assertEqual(0, group.bonus_submissions_remaining)

        num_past_limit = 2
        for i in range(num_past_limit):
            submission = self._create_submission(group)
            self.assertFalse(submission.is_bonus_submission)
            self.assertTrue(submission.is_past_daily_limit)

        self.assertEqual(limit + num_bonus_submissions + num_past_limit,
                         group.num_submits_towards_limit)

    def _create_submission(self, group: ag_models.Group,
                           timestamp: Optional[datetime.datetime]=None) -> ag_models.Submission:
        client = APIClient()
        client.force_authenticate(group.members.first())

        if timestamp is None:
            timestamp = timezone.now()

        with mock.patch('autograder.rest_api.views.submission_views.submission_views.timezone.now',
                        new=lambda: timestamp):
            response = client.post(reverse('submissions', kwargs={'pk': group.pk}),
                                   {'submitted_files': []}, format='multipart')
        self.assertEqual(status.HTTP_201_CREATED, response.status_code, msg=response.data)

        submission = ag_models.Submission.objects.get(pk=response.data['pk'])
        submission.status = ag_models.Submission.GradingStatus.finished_grading
        submission.save()
        return submission


class CreateSubmissionTotalLimitTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.submission_limit = 2
        self.project = obj_build.make_project(
            total_submission_limit=self.submission_limit,
            visible_to_students=True,
            guests_can_submit=True
        )

        self.client = APIClient()

    def test_staff_submit_no_limit(self):
        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.staff)

        for i in range(self.submission_limit + 1):
            self._do_and_check_valid_create_submission(group)

    def test_student_run_out_of_submissions(self):
        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.student)

        for i in range(self.submission_limit):
            self._do_and_check_valid_create_submission(group)

        self._do_and_check_invalid_create_submission(group)

    def test_guest_run_out_of_submissions(self):
        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.guest)

        for i in range(self.submission_limit):
            self._do_and_check_valid_create_submission(group)

        self._do_and_check_invalid_create_submission(group)

    def test_student_has_refunded_submission(self):
        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.student)

        for i in range(self.submission_limit):
            self._do_and_check_valid_create_submission(group)

        self._do_and_check_invalid_create_submission(group)

        # Refund a submission
        refunded_submission: ag_models.Submission = group.submissions.first()
        refunded_submission.validate_and_update(count_towards_total_limit=False)

        self._do_and_check_valid_create_submission(group)

    def test_total_submission_limit_changed_late_new_submits_rejected(self):
        # This should only ever happen if the user makes a mistake.

        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.student)
        self.project.validate_and_update(total_submission_limit=None)

        self._do_and_check_valid_create_submission(group)
        self._do_and_check_valid_create_submission(group)

        self.project.validate_and_update(total_submission_limit=1)

        self._do_and_check_invalid_create_submission(group)

    def _do_and_check_valid_create_submission(self, group: ag_models.Group):
        url = reverse('submissions', kwargs={'pk': group.pk})
        self.client.force_authenticate(group.members.first())

        response = self.client.post(url, {'submitted_files': []}, format='multipart')
        self.assertEqual(status.HTTP_201_CREATED, response.status_code, msg=response.data)
        self.assertTrue(response.data['count_towards_total_limit'])

        ag_models.Submission.objects.filter(
            pk=response.data['pk']
        ).update(status=ag_models.Submission.GradingStatus.finished_grading)

    def _do_and_check_invalid_create_submission(self, group: ag_models.Group):
        url = reverse('submissions', kwargs={'pk': group.pk})
        self.client.force_authenticate(group.members.first())

        response = self.client.post(url, {'submitted_files': []}, format='multipart')
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('submission', response.data)


class RetrieveSubmissionAndFileTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.project = obj_build.make_project()
        self.course = self.project.course

    def _make_submission_with_files(self, user_role: obj_build.UserRole) -> ag_models.Submission:
        group = obj_build.make_group(project=self.project, members_role=user_role)
        return obj_build.make_submission(
            group,
            submitted_files=[
                SimpleUploadedFile('spam.cpp', b'stevenroiestanriosta'),
                SimpleUploadedFile('egg.txt', b'stavenrst'),
                SimpleUploadedFile('sausage.txt', b'stoveqwfophn')
            ]
        )

    def test_admin_or_staff_view_any_submission(self):
        admin = obj_build.make_admin_user(self.course)
        staff = obj_build.make_staff_user(self.course)

        admin_submission = self._make_submission_with_files(obj_build.UserRole.admin)
        staff_submission = self._make_submission_with_files(obj_build.UserRole.staff)
        student_submission = self._make_submission_with_files(obj_build.UserRole.student)
        guest_submission = self._make_submission_with_files(obj_build.UserRole.guest)

        for submission in admin_submission, staff_submission, student_submission, guest_submission:
            for user in admin, staff:
                self.do_get_object_test(
                    self.client, user, submission_detail_url(submission),
                    submission.to_dict())
                self.do_get_files_test_case(submission, user)

    def test_student_view_submission(self):
        self.project.validate_and_update(visible_to_students=True)
        submission = self._make_submission_with_files(obj_build.UserRole.student)
        user = submission.group.members.first()
        self.do_get_object_test(
            self.client, user, submission_detail_url(submission),
            submission.to_dict())
        self.do_get_files_test_case(submission, user)

    def test_guest_view_submission(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        submission = self._make_submission_with_files(obj_build.UserRole.guest)
        user = submission.group.members.first()
        self.do_get_object_test(
            self.client, user, submission_detail_url(submission),
            submission.to_dict())
        self.do_get_files_test_case(submission, user)

    def test_non_member_view_submission_forbidden(self):
        self.project.validate_and_update(visible_to_students=True)
        submission = self._make_submission_with_files(obj_build.UserRole.student)

        user = obj_build.make_student_user(self.course)

        self.do_permission_denied_get_test(
            self.client, user, submission_detail_url(submission))
        self.do_get_files_permission_denied_test_case(submission, user)

    def test_student_view_submission_project_hidden_forbidden(self):
        self.project.validate_and_update(visible_to_students=False, guests_can_submit=True)
        submission = self._make_submission_with_files(obj_build.UserRole.student)
        user = submission.group.members.first()

        self.do_permission_denied_get_test(self.client, user, submission_detail_url(submission))
        self.do_get_files_permission_denied_test_case(submission, user)

    def test_guest_view_submission_project_hidden_forbidden(self):
        self.project.validate_and_update(visible_to_students=False, guests_can_submit=True)
        submission = self._make_submission_with_files(obj_build.UserRole.guest)
        user = submission.group.members.first()

        self.do_permission_denied_get_test(self.client, user, submission_detail_url(submission))
        self.do_get_files_permission_denied_test_case(submission, user)

    def test_guest_view_submission_project_private_forbidden(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=False)
        submission = self._make_submission_with_files(obj_build.UserRole.guest)
        user = submission.group.members.first()

        self.do_permission_denied_get_test(self.client, user, submission_detail_url(submission))
        self.do_get_files_permission_denied_test_case(submission, user)

    def test_get_malicious_filename_not_found(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        submission = self._make_submission_with_files(obj_build.UserRole.student)

        filename = os.path.abspath(__file__)

        self.client.force_authenticate(submission.group.members.first())
        url = file_url(submission, filename)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_get_file_missing_filename_param(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        submission = self._make_submission_with_files(obj_build.UserRole.student)

        self.client.force_authenticate(submission.group.members.first())
        response = self.client.get(
            reverse('submission-file', kwargs={'pk': submission.pk}))
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def do_get_files_test_case(self, submission, user):
        for filename in submission.submitted_filenames:
            self.do_get_content_test(
                self.client, user, file_url(submission, filename),
                submission.get_file(filename).read())

    def do_get_files_permission_denied_test_case(self, submission, user):
        for filename in submission.submitted_filenames:
            self.do_permission_denied_get_test(
                self.client, user, file_url(submission, filename),
                format='multipart')

    def do_get_content_test(self, client, user, url, expected_content):
        client.force_authenticate(user)
        response = client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertIn('Content-Length', response)
        self.assertEqual(
            expected_content,
            b''.join((chunk for chunk in response.streaming_content)))


class ListSubmissionsWithResultsTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.ag_test_cmd = obj_build.make_full_ag_test_command(
            normal_fdbk_config={
                'show_points': True,
                'return_code_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'stdout_fdbk_level': ag_models.ValueFeedbackLevel.no_feedback,
                'stderr_fdbk_level': ag_models.ValueFeedbackLevel.no_feedback,
            },
            past_limit_submission_fdbk_config={
                'show_points': True,
                'return_code_fdbk_level': ag_models.ValueFeedbackLevel.no_feedback,
                'stdout_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'stderr_fdbk_level': ag_models.ValueFeedbackLevel.no_feedback,
            },
            staff_viewer_fdbk_config={
                'show_points': True,
                'return_code_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'stdout_fdbk_level': ag_models.ValueFeedbackLevel.no_feedback,
                'stderr_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
            }
        )
        self.project = self.ag_test_cmd.ag_test_case.ag_test_suite.project
        self.project.validate_and_update(visible_to_students=True)

        self.student_group = obj_build.make_group(project=self.project)
        self.student_normal_submission = obj_build.make_finished_submission(
            group=self.student_group)
        obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_normal_submission)

        self.student_normal_submission = update_denormalized_ag_test_results(
            self.student_normal_submission.pk)

        self.student_past_limit_submission = obj_build.make_finished_submission(
            group=self.student_group, is_past_daily_limit=True)
        obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_past_limit_submission)

        self.student_past_limit_submission = update_denormalized_ag_test_results(
            self.student_past_limit_submission.pk)

    def test_student_has_normal_and_past_limit_submissions(self) -> None:
        url = reverse('list-submissions-with-results',
                      kwargs={'pk': self.student_group.pk})

        self.client.force_authenticate(self.student_group.members.first())
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        self._compare_submission_data(
            [self.student_past_limit_submission, self.student_normal_submission],
            response)

        self.assertIsNone(
            self._get_cmd_result(response.data[0])['return_code_correct'])
        self.assertTrue(
            self._get_cmd_result(response.data[0])['stdout_correct'])

        self.assertTrue(
            self._get_cmd_result(response.data[1])['return_code_correct'])
        self.assertIsNone(
            self._get_cmd_result(response.data[1])['stdout_correct'])

    def test_staff_request_student_submissions(self) -> None:
        url = reverse('list-submissions-with-results',
                      kwargs={'pk': self.student_group.pk})

        self.client.force_authenticate(obj_build.make_staff_user(self.project.course))
        response = self.client.get(url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        self._compare_submission_data(
            [self.student_past_limit_submission, self.student_normal_submission],
            response)

        self.assertIsNone(
            self._get_cmd_result(response.data[0])['stdout_correct'])
        self.assertTrue(
            self._get_cmd_result(response.data[0])['stderr_correct'])

        self.assertIsNone(
            self._get_cmd_result(response.data[1])['stdout_correct'])
        self.assertTrue(
            self._get_cmd_result(response.data[1])['stderr_correct'])

    def test_staff_request_own_submissions(self) -> None:
        staff_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.staff)

        staff_submission1 = obj_build.make_finished_submission(
            group=staff_group)
        obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=staff_submission1)

        staff_submission1 = update_denormalized_ag_test_results(staff_submission1.pk)

        staff_submission2 = obj_build.make_finished_submission(
            group=staff_group, is_past_limit=True)
        obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=staff_submission2)

        staff_submission2 = update_denormalized_ag_test_results(staff_submission2.pk)

        url = reverse('list-submissions-with-results', kwargs={'pk': staff_group.pk})
        self.client.force_authenticate(staff_group.members.first())
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        self._compare_submission_data([staff_submission2, staff_submission1], response)

        self.assertTrue(
            self._get_cmd_result(response.data[0])['return_code_correct'])
        self.assertTrue(
            self._get_cmd_result(response.data[0])['stdout_correct'])
        self.assertTrue(
            self._get_cmd_result(response.data[0])['stderr_correct'])

        self.assertTrue(
            self._get_cmd_result(response.data[1])['return_code_correct'])
        self.assertTrue(
            self._get_cmd_result(response.data[1])['stdout_correct'])
        self.assertTrue(
            self._get_cmd_result(response.data[1])['stderr_correct'])

    def test_admin_override_fdbk_category(self) -> None:
        url = reverse('list-submissions-with-results',
                      kwargs={'pk': self.student_group.pk})
        url += f'?feedback_category={ag_models.FeedbackCategory.ultimate_submission.value}'

        admin = obj_build.make_admin_user(self.project.course)
        self.client.force_authenticate(admin)
        response = self.client.get(url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        self._compare_submission_data(
            [self.student_past_limit_submission, self.student_normal_submission],
            response)

        self.assertEqual(self.ag_test_cmd.ultimate_submission_fdbk_config.to_dict(),
                         self._get_cmd_result(response.data[0])['fdbk_settings'])
        self.assertEqual(self.ag_test_cmd.ultimate_submission_fdbk_config.to_dict(),
                         self._get_cmd_result(response.data[1])['fdbk_settings'])

    def _compare_submission_data(self, submissions: Iterable[ag_models.Submission], response):
        self.assertEqual(
            [utils.exclude_dict(submission.to_dict(), 'results') for submission in submissions],
            [utils.exclude_dict(submission, 'results') for submission in response.data]
        )

        self.assertEqual(1, len(response.data[0]['results']['ag_test_suite_results']))
        self.assertEqual(1, len(response.data[1]['results']['ag_test_suite_results']))

        self.assertNotEqual(0, response.data[0]['results']['total_points'])
        self.assertNotEqual(0, response.data[1]['results']['total_points'])

    def _get_cmd_result(self, submission_dict: dict):
        return submission_dict['results'][
            'ag_test_suite_results'][0][
            'ag_test_case_results'][0][
            'ag_test_command_results'][0]


class UpdateSubmissionTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.submission = obj_build.make_submission()
        self.group = self.submission.group
        self.project = self.group.project
        self.course = self.project.course

    def test_admin_edit_count_towards_total_limit(self) -> None:
        admin = obj_build.make_admin_user(self.course)

        self.assertTrue(self.submission.count_towards_total_limit)
        for val in False, True:
            self.do_patch_object_test(
                self.submission, self.client, admin,
                submission_detail_url(self.submission),
                {'count_towards_total_limit': val})

    def test_admin_edit_submission_invalid_fields(self) -> None:
        admin = obj_build.make_admin_user(self.course)
        self.do_patch_object_invalid_args_test(
            self.submission, self.client, admin,
            submission_detail_url(self.submission),
            {'is_past_daily_limit': False})

    def test_non_admin_edit_count_towards_total_limit_permission_denied(self) -> None:
        self.do_patch_object_permission_denied_test(
            self.submission, self.client,
            obj_build.make_staff_user(self.course),
            submission_detail_url(self.submission),
            {'count_towards_total_limit': False})

        self.do_patch_object_permission_denied_test(
            self.submission, self.client,
            self.group.members.first(),
            submission_detail_url(self.submission),
            {'count_towards_total_limit': False})

        self.do_patch_object_permission_denied_test(
            self.submission, self.client,
            obj_build.make_handgrader_user(self.course),
            submission_detail_url(self.submission),
            {'count_towards_total_limit': False})


class RemoveSubmissionFromQueueTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.project = obj_build.make_project()
        self.course = self.project.course

    def test_admin_or_staff_remove_own_from_queue(self):
        self._do_remove_own_submission_from_queue_test(obj_build.UserRole.admin)
        self._do_remove_own_submission_from_queue_test(obj_build.UserRole.staff)

    def test_student_remove_own_from_queue(self):
        self.project.validate_and_update(visible_to_students=True)
        self._do_remove_own_submission_from_queue_test(obj_build.UserRole.student)

    def test_guest_remove_own_from_queue(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        self._do_remove_own_submission_from_queue_test(obj_build.UserRole.guest)

    def _do_remove_own_submission_from_queue_test(self, user_role: obj_build.UserRole) -> None:
        group = obj_build.make_group(project=self.project, members_role=user_role)
        submission = obj_build.make_submission(group)
        self.do_valid_remove_from_queue_test(submission)

    def test_remove_bonus_submission_from_queue_refund_bonus_submission(self):
        project = obj_build.make_project(submission_limit_per_day=1,
                                         num_bonus_submissions=1, visible_to_students=True)
        group = obj_build.make_group(project=project)

        # Make sure other groups' bonus submission counts don't change.
        other_group = obj_build.make_group(project=project)

        self.assertEqual(1, group.bonus_submissions_remaining)
        self.assertEqual(1, other_group.bonus_submissions_remaining)

        self.client.force_authenticate(group.members.first())
        response = self.client.post(reverse('submissions', kwargs={'pk': group.pk}),
                                    {'submitted_files': []}, format='multipart')
        self.assertEqual(status.HTTP_201_CREATED, response.status_code, msg=response.data)

        group.refresh_from_db()
        self.assertEqual(1, group.bonus_submissions_remaining)
        self.assertEqual(1, other_group.bonus_submissions_remaining)

        submission = ag_models.Submission.objects.get(pk=response.data['pk'])
        self.assertFalse(submission.is_bonus_submission)

        submission.status = ag_models.Submission.GradingStatus.finished_grading
        submission.save()

        response = self.client.post(reverse('submissions', kwargs={'pk': group.pk}),
                                    {'submitted_files': []}, format='multipart')
        group.refresh_from_db()
        self.assertEqual(0, group.bonus_submissions_remaining)
        self.assertEqual(1, other_group.bonus_submissions_remaining)

        bonus_submission = ag_models.Submission.objects.get(pk=response.data['pk'])
        self.assertTrue(bonus_submission.is_bonus_submission)

        response = self.client.post(submission_remove_from_queue_url(bonus_submission))
        self.assertEqual(status.HTTP_200_OK, response.status_code, msg=response.data)

        group.refresh_from_db()
        self.assertEqual(1, group.bonus_submissions_remaining)
        self.assertEqual(1, other_group.bonus_submissions_remaining)

        bonus_submission.refresh_from_db()
        self.assertFalse(bonus_submission.is_bonus_submission)
        self.assertFalse(response.data['is_bonus_submission'])

    def test_remove_non_bonus_submission_from_queue_no_refund(self):
        project = obj_build.make_project(submission_limit_per_day=1,
                                         num_bonus_submissions=1, visible_to_students=True)
        group = obj_build.make_group(project=project)

        self.assertEqual(1, group.bonus_submissions_remaining)

        self.client.force_authenticate(group.members.first())
        response = self.client.post(reverse('submissions', kwargs={'pk': group.pk}),
                                    {'submitted_files': []}, format='multipart')
        self.assertEqual(status.HTTP_201_CREATED, response.status_code, msg=response.data)

        group.refresh_from_db()
        self.assertEqual(1, group.bonus_submissions_remaining)

        submission = ag_models.Submission.objects.get(pk=response.data['pk'])
        self.assertFalse(submission.is_bonus_submission)

        response = self.client.post(submission_remove_from_queue_url(submission))
        self.assertEqual(status.HTTP_200_OK, response.status_code, msg=response.data)

        group.refresh_from_db()
        self.assertEqual(1, group.bonus_submissions_remaining)

        submission.refresh_from_db()
        self.assertFalse(submission.is_bonus_submission)

    def test_student_remove_from_queue_project_hidden_permission_denied(self):
        self.project.validate_and_update(visible_to_students=False, guests_can_submit=True)
        group = obj_build.make_group(project=self.project)
        submission = obj_build.make_submission(group)

        self.do_permission_denied_remove_from_queue_test(submission, group.members.first())

    def test_guest_remove_from_queue_project_hidden_permission_denied(self):
        self.project.validate_and_update(visible_to_students=False, guests_can_submit=True)
        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.guest)
        submission = obj_build.make_submission(group)

        self.do_permission_denied_remove_from_queue_test(submission, group.members.first())

    def test_handgrader_remove_student_submission_from_queue_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        group = obj_build.make_group(project=self.project)
        submission = obj_build.make_submission(group)

        self.do_permission_denied_remove_from_queue_test(
            submission, obj_build.make_handgrader_user(self.course))

    def test_guest_remove_from_queue_project_private_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=False)

        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.guest)
        submission = obj_build.make_submission(group)

        self.do_permission_denied_remove_from_queue_test(submission, group.members.first())

    def test_remove_others_submission_from_queue_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.guest)
        submission = obj_build.make_submission(group)

        self.do_permission_denied_remove_from_queue_test(
            submission, obj_build.make_admin_user(self.course))

    def test_error_remove_submission_not_in_queue(self):
        statuses = set(ag_models.Submission.GradingStatus.values)
        statuses.remove(ag_models.Submission.GradingStatus.queued)
        statuses.remove(ag_models.Submission.GradingStatus.received)

        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.admin)
        submission = obj_build.make_submission(group)

        for grading_status in statuses:
            submission.status = grading_status
            submission.save()
            self.do_invalid_remove_from_queue_test(submission)

    def do_valid_remove_from_queue_test(self, submission, user=None):
        for grading_status in (ag_models.Submission.GradingStatus.received,
                               ag_models.Submission.GradingStatus.queued):
            submission.status = grading_status
            submission.save()

            if user is None:
                user = submission.group.members.first()

            self.client.force_authenticate(user)
            response = self.client.post(
                submission_remove_from_queue_url(submission))
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertEqual(ag_models.Submission.GradingStatus.removed_from_queue,
                             response.data['status'])

            submission.refresh_from_db()

            self.assertEqual(ag_models.Submission.GradingStatus.removed_from_queue,
                             submission.status)

    def do_permission_denied_remove_from_queue_test(self, submission, user):
        self._do_bad_remove_from_queue_test(
            submission, user, status.HTTP_403_FORBIDDEN)

    def do_invalid_remove_from_queue_test(self, submission, user=None):
        self._do_bad_remove_from_queue_test(
            submission, user, status.HTTP_400_BAD_REQUEST)

    def _do_bad_remove_from_queue_test(self, submission, user, expected_status):
        original_status = submission.status
        if user is None:
            user = submission.group.members.first()

        self.client.force_authenticate(user)
        response = self.client.post(submission_remove_from_queue_url(submission))
        self.assertEqual(expected_status, response.status_code)

        submission.refresh_from_db()

        self.assertEqual(original_status, submission.status)


def submission_remove_from_queue_url(submission):
    return reverse('remove-submission-from-queue',
                   kwargs={'pk': submission.pk})


def submission_detail_url(submission):
    return reverse('submission-detail', kwargs={'pk': submission.pk})


def file_url(submission, filename):
    query_params = QueryDict(mutable=True)
    query_params.update({'filename': filename})
    return (reverse('submission-file', kwargs={'pk': submission.pk})
            + '?' + query_params.urlencode())
