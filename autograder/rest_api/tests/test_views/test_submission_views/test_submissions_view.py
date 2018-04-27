from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from rest_framework import status

from autograder import utils

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls


class ListGroupSubmissionsTestCase(test_data.Client,
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

                obj_build.build_submission(group=group, status=grading_status)

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
