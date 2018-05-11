import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import QueryDict
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.utils.testing.model_obj_builders as obj_build
from autograder import utils
from autograder.core.models import Submission
from autograder.utils.testing import UnitTestBase


class ListSubmissionsTestCase(test_data.Client,
                              test_data.Project,
                              test_data.Group,
                              test_data.Submission,
                              test_impls.ListObjectsTest,
                              UnitTestBase):
    def setUp(self):
        super().setUp()
        self.maxDiff = None

    def test_admin_or_staff_list_submissions(self):
        for project in self.all_projects:
            for group in self.at_least_enrolled_groups(project):
                expected_data = ag_serializers.SubmissionSerializer(
                    self.build_submissions(group), many=True).data
                for user in self.admin, self.staff:
                    self.do_list_objects_test(
                        self.client, user, self.submissions_url(group),
                        expected_data)

        for project in self.hidden_public_project, self.visible_public_project:
            group = self.non_enrolled_group(project)
            expected_data = ag_serializers.SubmissionSerializer(
                self.build_submissions(group), many=True).data
            for user in self.admin, self.staff:
                self.do_list_objects_test(
                    self.client, user, self.submissions_url(group),
                    expected_data)

    def test_enrolled_list_submissions(self):
        for project in self.visible_projects:
            group = self.enrolled_group(project)
            expected_data = ag_serializers.SubmissionSerializer(
                self.build_submissions(group), many=True).data
            self.do_list_objects_test(
                self.client, self.enrolled, self.submissions_url(group),
                expected_data)

    def test_handgrader_list_student_group_submissions_permission_denied(self):
        for project in self.visible_projects:
            group = self.enrolled_group(project)
            expected_data = ag_serializers.SubmissionSerializer(
                self.build_submissions(group), many=True).data
            self.do_permission_denied_get_test(
                self.client, self.handgrader, self.submissions_url(group), expected_data)

    def test_non_enrolled_list_submissions(self):
        group = self.non_enrolled_group(self.visible_public_project)
        expected_data = ag_serializers.SubmissionSerializer(
            self.build_submissions(group), many=True).data
        self.do_list_objects_test(
            self.client, self.nobody, self.submissions_url(group),
            expected_data)

    def test_non_group_member_list_submissions_permission_denied(self):
        group = self.enrolled_group(self.visible_public_project)
        self.build_submissions(group)
        non_member = self.clone_user(self.enrolled)
        for user in non_member, self.nobody:
            self.do_permission_denied_get_test(
                self.client, user, self.submissions_url(group))

    def test_enrolled_list_submissions_project_hidden_permission_denied(self):
        for project in self.hidden_projects:
            group = self.enrolled_group(project)
            self.build_submissions(group)
            self.do_permission_denied_get_test(
                self.client, self.enrolled, self.submissions_url(group))

    def test_non_enrolled_list_submissions_project_hidden_permission_denied(self):
        group = self.non_enrolled_group(self.hidden_public_project)
        self.build_submissions(group)
        self.do_permission_denied_get_test(
            self.client, self.nobody, self.submissions_url(group))

    def test_non_enrolled_list_submissions_project_private_permission_denied(self):
        group = self.non_enrolled_group(self.visible_public_project)
        self.build_submissions(group)
        self.visible_public_project.validate_and_update(
            guests_can_submit=False)
        self.do_permission_denied_get_test(
            self.client, self.nobody, self.submissions_url(group))


class CreateSubmissionTestCase(test_data.Client,
                               test_data.Project,
                               test_data.Group,
                               test_data.Submission,
                               test_impls.CreateObjectTest,
                               UnitTestBase):
    def test_admin_or_staff_submit(self):
        for project in self.all_projects:
            project.validate_and_update(
                closing_time=timezone.now() + timezone.timedelta(minutes=1))
            for group in (self.admin_group(project),
                          self.staff_group(project)):
                self.do_normal_submit_test(group, group.members.last())

    def test_admin_or_staff_submit_deadline_past(self):
        self.project.validate_and_update(
            closing_time=timezone.now() + timezone.timedelta(seconds=-1))
        for group in (self.admin_group(self.project),
                      self.staff_group(self.project)):
            self.do_normal_submit_test(group, group.members.first())

    def test_admin_or_staff_submit_submissions_disallowed(self):
        self.project.validate_and_update(disallow_student_submissions=True)
        for group in (self.admin_group(self.project),
                      self.staff_group(self.project)):
            self.do_normal_submit_test(group, group.members.last())

    def test_enrolled_submit(self):
        for project in self.visible_projects:
            closing_time = timezone.now() + timezone.timedelta(minutes=1)
            project.validate_and_update(closing_time=closing_time)
            group = self.enrolled_group(project)
            self.do_normal_submit_test(group, group.members.last())

    def test_non_enrolled_submit(self):
        closing_time = timezone.now() + timezone.timedelta(minutes=1)
        self.visible_public_project.validate_and_update(
            closing_time=closing_time)
        group = self.non_enrolled_group(self.visible_public_project)
        self.do_normal_submit_test(group, group.members.first())

    def test_all_submit_no_closing_time(self):
        for group in self.all_groups(self.visible_public_project):
            self.do_normal_submit_test(group, group.members.first())

    def test_submit_missing_and_discarded_files_tracked(self):
        self.add_expected_patterns(self.visible_private_project)
        group = self.enrolled_group(self.visible_private_project)
        self.client.force_authenticate(self.enrolled)
        bad_filename = 'not a needed file'
        request_data = {
            'submitted_files': [
                SimpleUploadedFile(bad_filename, b'merp')]}
        response = self.client.post(
            self.submissions_url(group), request_data, format='multipart')
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertCountEqual([], response.data['submitted_filenames'])
        self.assertCountEqual([bad_filename],
                              response.data['discarded_files'])
        self.assertIn('*.txt', response.data['missing_files'])
        self.assertIn('spam.cpp', response.data['missing_files'])

    # Note that non-group members in this case includes staff, admin, and handgrader.
    def test_non_group_member_submit_permission_denied(self):
        group = self.enrolled_group(self.visible_public_project)
        other_user = self.clone_user(self.enrolled)
        for user in self.admin, self.staff, other_user, self.nobody, self.handgrader:
            self.do_permission_denied_submit_test(group, user)

    def test_handgraders_that_are_also_students_submit(self):
        for project in self.visible_projects:
            group = self.enrolled_group(project)
            project.course.handgraders.add(group.members.last())
            self.do_normal_submit_test(group, group.members.last())

    def test_enrolled_submit_hidden_project_permission_denied(self):
        for project in self.hidden_projects:
            group = self.enrolled_group(project)
            self.do_permission_denied_submit_test(group, group.members.first())

    def test_non_enrolled_submit_hidden_project_permission_denied(self):
        group = self.non_enrolled_group(self.hidden_public_project)
        self.do_permission_denied_submit_test(group, group.members.first())

    def test_non_enrolled_submit_private_project_permission_denied(self):
        group = self.non_enrolled_group(self.visible_public_project)
        self.visible_public_project.validate_and_update(
            guests_can_submit=False)
        for user in group.members.all():
            self.do_permission_denied_submit_test(group, user)

    def test_non_staff_submit_deadline_past(self):
        self.visible_public_project.validate_and_update(
            closing_time=timezone.now() + timezone.timedelta(seconds=-1))
        for group in self.non_staff_groups(self.visible_public_project):
            response = self.do_bad_request_submit_test(
                group, group.members.first())
            self.assertIn('submission', response.data)

    def test_non_staff_submit_deadline_past_but_has_extension(self):
        closing_time = timezone.now() + timezone.timedelta(seconds=-1)
        self.visible_public_project.validate_and_update(
            closing_time=closing_time)
        for group in self.non_staff_groups(self.visible_public_project):
            extension = timezone.now() + timezone.timedelta(minutes=1)
            group.validate_and_update(extended_due_date=extension)
            self.do_normal_submit_test(group, group.members.last())

    def test_non_staff_submit_deadline_and_extension_past(self):
        closing_time = timezone.now() + timezone.timedelta(minutes=-1)
        self.visible_public_project.validate_and_update(
            closing_time=closing_time)
        for group in self.non_staff_groups(self.visible_public_project):
            extension = timezone.now() + timezone.timedelta(seconds=-1)
            group.validate_and_update(extended_due_date=extension)
            response = self.do_bad_request_submit_test(group, group.members.first())
            self.assertIn('submission', response.data)

    def test_non_staff_submit_submissions_disallowed(self):
        self.visible_public_project.validate_and_update(
            disallow_student_submissions=True)
        future_closing_time = timezone.now() + timezone.timedelta(minutes=1)
        for group in self.non_staff_groups(self.visible_public_project):
            for closing_time in None, future_closing_time:
                self.visible_public_project.validate_and_update(
                    closing_time=closing_time)
            response = self.do_bad_request_submit_test(group, group.members.first())
            self.assertIn('submission', response.data)

    def test_all_users_already_has_submission_being_processed(self):
        for group in self.all_groups(self.visible_public_project):
            ag_models.Submission.objects.validate_and_create(
                [], group=group)
            response = self.do_bad_request_submit_test(group, group.members.last())
            self.assertIn('submission', response.data)

    def test_can_resubmit_non_being_processed_status(self):
        for group in self.all_groups(self.visible_public_project):
            for grading_status in ag_models.Submission.GradingStatus.values:
                if grading_status in (
                        ag_models.Submission.GradingStatus.active_statuses):
                    continue

                obj_build.make_submission(group=group, status=grading_status)

                self.do_normal_submit_test(group, group.members.first())

    def test_no_submission_limit(self):
        self.assertIsNone(self.visible_public_project.submission_limit_per_day)
        for group in self.all_groups(self.visible_public_project):
            for i in range(5):
                self.do_normal_submit_test(group, group.members.first())

    def test_submission_not_past_limit(self):
        limit = 3
        self.visible_public_project.validate_and_update(
            submission_limit_per_day=limit)
        for group in self.all_groups(self.visible_public_project):
            for i in range(limit):
                self.do_normal_submit_test(group, group.members.last())
            for sub in group.submissions.all():
                self.assertTrue(sub.count_towards_daily_limit)

    def test_submission_past_limit_allowed(self):
        limit = 3
        self.visible_public_project.validate_and_update(
            submission_limit_per_day=limit,
            allow_submissions_past_limit=True)
        for group in self.all_groups(self.visible_public_project):
            for i in range(limit + 2):
                self.do_normal_submit_test(group, group.members.last())
            num_not_past_limit = utils.count_if(
                group.submissions.all(),
                lambda sub: not sub.is_past_daily_limit)
            self.assertEqual(limit, num_not_past_limit)
            for sub in group.submissions.all():
                self.assertTrue(sub.count_towards_daily_limit)

    def test_submission_past_limit_not_allowed_bad_request(self):
        limit = 2
        self.visible_public_project.validate_and_update(
            submission_limit_per_day=limit,
            allow_submissions_past_limit=False)
        for group in self.non_staff_groups(self.visible_public_project):
            for i in range(limit):
                self.do_normal_submit_test(group, group.members.first())
            for i in range(3):
                response = self.do_bad_request_submit_test(
                    group, group.members.first())
                self.assertIn('submission', response.data)
            self.assertEqual(limit, group.submissions.count())
            for sub in group.submissions.all():
                self.assertTrue(sub.count_towards_daily_limit)
                self.assertFalse(sub.is_past_daily_limit)

    def test_admin_or_staff_submissions_never_count_towards_limit(self):
        limit = 1
        num_submissions = limit + 4
        self.hidden_private_project.validate_and_update(
            submission_limit_per_day=limit)
        for group in self.staff_groups(self.hidden_private_project):
            for i in range(num_submissions):
                self.do_normal_submit_test(group, group.members.last())

            self.assertEqual(num_submissions, group.submissions.count())

    def test_invalid_fields_fields_other_than_submitted_files_in_request(self):
        group = self.admin_group(self.project)
        response = self.do_invalid_create_object_test(
            group.submissions, self.client,
            group.members.first(),
            self.submissions_url(group),
            {'submitted_files': self.files_to_submit,
             'count_towards_daily_limit': False},
            format='multipart')
        self.assertIn('invalid_fields', response.data)
        self.assertIn('count_towards_daily_limit',
                      response.data['invalid_fields'])

    def do_normal_submit_test(self, group, user):
        self.add_expected_patterns(group.project)
        response = self.do_create_object_test(
            ag_models.Submission.objects, self.client, user,
            self.submissions_url(group),
            {'submitted_files': self.files_to_submit},
            format='multipart', check_data=False)

        loaded = ag_models.Submission.objects.get(pk=response.data['pk'])
        self.assertEqual(loaded.to_dict(), response.data)

        # We don't know the exact timestamp assigned by the server, so
        # make sure it's reasonably close to what it should be.
        timestamp_difference = loaded.timestamp - timezone.now()
        self.assertLess(timestamp_difference, timezone.timedelta(seconds=2))

        self.assertEqual(group.pk, response.data['group'])
        self.assertEqual(ag_models.Submission.GradingStatus.received,
                         response.data['status'])
        self.assertCountEqual([file_.name for file_ in self.files_to_submit],
                              response.data['submitted_filenames'])
        self.assertCountEqual([], response.data['missing_files'])
        self.assertCountEqual([], response.data['discarded_files'])
        self.assertEqual(user.username, response.data['submitter'])

        loaded.status = ag_models.Submission.GradingStatus.finished_grading
        loaded.save()

    def do_permission_denied_submit_test(self, group, user):
        self.add_expected_patterns(group.project)
        return self.do_permission_denied_create_test(
            ag_models.Submission.objects, self.client,
            user, self.submissions_url(group),
            {'submitted_files': self.files_to_submit}, format='multipart')

    def do_bad_request_submit_test(self, group, user):
        self.add_expected_patterns(group.project)
        return self.do_invalid_create_object_test(
            group.submissions, self.client, user,
            self.submissions_url(group),
            {'submitted_files': self.files_to_submit}, format='multipart')


class RetrieveSubmissionAndFileTestCase(test_data.Client,
                                        test_data.Project,
                                        test_data.Submission,
                                        test_impls.GetObjectTest,
                                        UnitTestBase):
    def test_admin_or_staff_view_submission(self):
        for project in self.all_projects:
            for submission in self.at_least_enrolled_submissions(project):
                for user in self.admin, self.staff:
                    self.do_get_object_test(
                        self.client, user, submission_url(submission),
                        submission.to_dict())
                    self.do_get_files_test_case(submission, user)

        for project in self.public_projects:
            submission = self.non_enrolled_submission(project)
            for user in self.admin, self.staff:
                self.do_get_object_test(
                    self.client, user, submission_url(submission),
                    submission.to_dict())
                self.do_get_files_test_case(submission, user)

    def test_enrolled_view_submission(self):
        for project in self.visible_projects:
            submission = self.enrolled_submission(project)
            for user in submission.group.members.all():
                self.do_get_object_test(
                    self.client, user, submission_url(submission),
                    submission.to_dict())
                self.do_get_files_test_case(submission, user)

    def test_non_enrolled_view_submission(self):
        submission = self.enrolled_submission(self.visible_public_project)
        for user in submission.group.members.all():
            self.do_get_object_test(
                self.client, user, submission_url(submission),
                submission.to_dict())
            self.do_get_files_test_case(submission, user)

    def test_non_member_view_submission_forbidden(self):
        submission = self.enrolled_submission(self.visible_public_project)
        other_user = self.clone_user(self.enrolled)
        for user in other_user, self.nobody, self.handgrader:
            self.do_permission_denied_get_test(
                self.client, user, submission_url(submission))
            self.do_get_files_permission_denied_test_case(submission, user)

    def test_enrolled_view_submission_project_hidden_forbidden(self):
        for project in self.hidden_projects:
            submission = self.enrolled_submission(project)
            self.do_permission_denied_get_test(
                self.client, self.enrolled, submission_url(submission))
            self.do_get_files_permission_denied_test_case(
                submission, self.enrolled)

    def test_non_enrolled_view_submission_project_hidden_forbidden(self):
        submission = self.non_enrolled_submission(self.hidden_public_project)
        self.do_permission_denied_get_test(
            self.client, self.nobody, submission_url(submission))
        self.do_get_files_permission_denied_test_case(submission, self.nobody)

    def test_non_enrolled_view_submission_project_private_forbidden(self):
        submission = self.non_enrolled_submission(self.visible_public_project)
        self.visible_public_project.validate_and_update(
            guests_can_submit=False)
        self.do_permission_denied_get_test(
            self.client, self.nobody, submission_url(submission))
        self.do_get_files_permission_denied_test_case(submission, self.nobody)

    def test_get_malicious_filename_not_found(self):
        filename = os.path.abspath(__file__)
        submission = self.enrolled_submission(self.visible_public_project)
        self.client.force_authenticate(self.enrolled)
        url = file_url(submission, filename)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_get_file_missing_filename_param(self):
        submission = self.enrolled_submission(self.visible_public_project)
        self.client.force_authenticate(self.enrolled)
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
        self.assertEqual(
            expected_content,
            b''.join((chunk for chunk in response.streaming_content)))


class UpdateSubmissionTestCase(test_data.Client,
                               test_data.Project,
                               test_data.Submission,
                               test_impls.UpdateObjectTest,
                               UnitTestBase):
    def test_admin_edit_count_towards_limit(self):
        for project in self.all_projects:
            for submission in self.at_least_enrolled_submissions(project):
                self.assertTrue(submission.count_towards_daily_limit)
                for val in False, True:
                    self.do_patch_object_test(
                        submission, self.client, self.admin,
                        submission_url(submission),
                        {'count_towards_daily_limit': val})

        for project in self.visible_public_project, self.hidden_public_project:
            submission = self.non_enrolled_submission(project)
            self.assertTrue(submission.count_towards_daily_limit)
            for val in False, True:
                self.do_patch_object_test(
                    submission, self.client, self.admin,
                    submission_url(submission),
                    {'count_towards_daily_limit': val})

    def test_admin_edit_submission_invalid_fields(self):
        for submission in self.all_submissions(self.visible_public_project):
            self.do_patch_object_invalid_args_test(
                submission, self.client, self.admin,
                submission_url(submission), {'is_past_daily_limit': False})

    def test_other_edit_count_towards_limit_permission_denied(self):
        submissions = (
            self.staff_submission(self.visible_public_project),
            self.enrolled_submission(self.visible_public_project),
            self.non_enrolled_submission(self.visible_public_project))
        for submission in submissions:
            self.do_patch_object_permission_denied_test(
                submission, self.client,
                submission.group.members.first(),
                submission_url(submission),
                {'count_towards_daily_limit': False})

    def test_handgrader_edit_submission_permission_denied(self):
        submissions = (
            self.staff_submission(self.visible_public_project),
            self.enrolled_submission(self.visible_public_project),
            self.non_enrolled_submission(self.visible_public_project))
        for submission in submissions:
            self.do_patch_object_permission_denied_test(
                submission, self.client,
                self.handgrader,
                submission_url(submission),
                {'count_towards_daily_limit': False})


class RemoveFromQueueTestCase(test_data.Client,
                              test_data.Project,
                              test_data.Submission,
                              UnitTestBase):
    def test_admin_or_staff_remove_own_from_queue(self):
        for project in self.all_projects:
            for submission in self.staff_submissions(project):
                self.do_valid_remove_from_queue_test(submission)

    def test_enrolled_remove_own_from_queue(self):
        for project in self.visible_projects:
            submission = self.enrolled_submission(project)
            self.do_valid_remove_from_queue_test(submission)

    def test_non_enrolled_remove_own_from_queue(self):
        submission = self.non_enrolled_submission(self.visible_public_project)
        self.do_valid_remove_from_queue_test(submission)

    def test_enrolled_remove_from_queue_project_hidden_permission_denied(self):
        for project in self.hidden_projects:
            submission = self.enrolled_submission(project)
            self.do_permission_denied_remove_from_queue_test(
                submission, submission.group.members.first())

    def test_non_enrolled_remove_from_queue_project_hidden_permission_denied(self):
        submission = self.non_enrolled_submission(self.hidden_public_project)
        self.do_permission_denied_remove_from_queue_test(
            submission, submission.group.members.first())

    def test_handgrader_remove_student_submission_from_queue_permission_denied(self):
        self.do_permission_denied_remove_from_queue_test(
            self.enrolled_submission(self.visible_projects[0]), self.handgrader)

    def test_non_enrolled_remove_from_queue_project_private_permission_denied(self):
        submission = self.non_enrolled_submission(self.visible_public_project)
        self.visible_public_project.validate_and_update(
            guests_can_submit=False)
        self.do_permission_denied_remove_from_queue_test(
            submission, submission.group.members.first())

    def test_remove_others_submission_from_queue_permission_denied(self):
        for submission in self.all_submissions(self.visible_public_project):
            for user in self.admin, self.staff, self.enrolled, self.nobody:
                group = submission.group
                if group.members.filter(pk=user.pk).exists():
                    continue

                self.do_permission_denied_remove_from_queue_test(
                    submission, user)

    def test_error_remove_submission_not_in_queue(self):
        statuses = set(Submission.GradingStatus.values)
        statuses.remove(Submission.GradingStatus.queued)
        statuses.remove(Submission.GradingStatus.received)
        for submission in self.all_submissions(self.visible_public_project):
            for grading_status in statuses:
                submission.status = grading_status
                submission.save()
                self.do_invalid_remove_from_queue_test(submission)

    def do_valid_remove_from_queue_test(self, submission, user=None):
        for grading_status in (Submission.GradingStatus.received,
                               Submission.GradingStatus.queued):
            submission.status = grading_status
            submission.save()

            if user is None:
                user = submission.group.members.first()

            self.client.force_authenticate(user)
            response = self.client.post(
                submission_remove_from_queue_url(submission))
            self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

            submission.refresh_from_db()

            self.assertEqual(Submission.GradingStatus.removed_from_queue,
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
    return reverse('submission-remove-from-queue',
                   kwargs={'pk': submission.pk})


def submission_url(submission):
    return reverse('submission-detail', kwargs={'pk': submission.pk})


def file_url(submission, filename):
    query_params = QueryDict(mutable=True)
    query_params.update({'filename': filename})
    return (reverse('submission-file', kwargs={'pk': submission.pk})
            + '?' + query_params.urlencode())
