import os

from django.core.urlresolvers import reverse
from django.http import QueryDict

from rest_framework import status

import autograder.core.models as ag_models
from autograder.core.models import Submission

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


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
            for user in submission.submission_group.members.all():
                self.do_get_object_test(
                    self.client, user, submission_url(submission),
                    submission.to_dict())
                self.do_get_files_test_case(submission, user)

    def test_non_enrolled_view_submission(self):
        submission = self.enrolled_submission(self.visible_public_project)
        for user in submission.submission_group.members.all():
            self.do_get_object_test(
                self.client, user, submission_url(submission),
                submission.to_dict())
            self.do_get_files_test_case(submission, user)

    def test_non_member_view_submission_forbidden(self):
        submission = self.enrolled_submission(self.visible_public_project)
        other_user = self.clone_user(self.enrolled)
        for user in other_user, self.nobody:
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
            allow_submissions_from_non_enrolled_students=False)
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
                submission.submission_group.members.first(),
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
                submission, submission.submission_group.members.first())

    def test_non_enrolled_remove_from_queue_project_hidden_permission_denied(self):
        submission = self.non_enrolled_submission(self.hidden_public_project)
        self.do_permission_denied_remove_from_queue_test(
            submission, submission.submission_group.members.first())

    def test_non_enrolled_remove_from_queue_project_private_permission_denied(self):
        submission = self.non_enrolled_submission(self.visible_public_project)
        self.visible_public_project.validate_and_update(
            allow_submissions_from_non_enrolled_students=False)
        self.do_permission_denied_remove_from_queue_test(
            submission, submission.submission_group.members.first())

    def test_remove_others_submission_from_queue_permission_denied(self):
        for submission in self.all_submissions(self.visible_public_project):
            for user in self.admin, self.staff, self.enrolled, self.nobody:
                group = submission.submission_group
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
                user = submission.submission_group.members.first()

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
            user = submission.submission_group.members.first()

        self.client.force_authenticate(user)
        response = self.client.post(submission_remove_from_queue_url(submission))
        self.assertEqual(expected_status, response.status_code)

        submission.refresh_from_db()

        self.assertEqual(original_status, submission.status)


class SubmissionFeedbackTestCase(UnitTestBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ag_test_cmd = obj_build.make_full_ag_test_command(
            set_arbitrary_points=True,
            normal_fdbk_config={
                'return_code_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'show_points': True,
            },
            past_limit_submission_fdbk_config={
                'stdout_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'show_points': True,
            }
        )
        cls.ag_test_case = cls.ag_test_cmd.ag_test_case
        cls.ag_test_suite = cls.ag_test_case.ag_test_suite
        cls.project = cls.ag_test_suite.project
        cls.project.validate_and_update(submission_limit_per_day=2)
        cls.course = cls.project.course

        # --------- student 1 --------------
        cls.student_group1 = obj_build.make_group(project=cls.project)
        cls.student1 = cls.student_group1.members.first()

        cls.student_group1_normal_submission = obj_build.build_submission(
            submission_group=cls.student_group1)
        obj_build.make_correct_ag_test_command_result(
            cls.ag_test_cmd, submission=cls.student_group1_normal_submission)

        cls.student_group1_best_submission = obj_build.build_submission(
            submission_group=cls.student_group1)
        obj_build.make_correct_ag_test_command_result(
            cls.ag_test_cmd, submission=cls.student_group1_best_submission)

        cls.student_group1_past_limit_submission = obj_build.build_submission(
            submission_group=cls.student_group1)
        obj_build.make_incorrect_ag_test_command_result(
            cls.ag_test_cmd, submission=cls.student_group1_past_limit_submission)

        # --------- student 2 --------------
        cls.student_group2 = obj_build.make_group(project=cls.project)
        cls.student2 = submission=cls.student_group2.members.first()

        cls.student_group2_submission = obj_build.build_submission(
            submission_group=cls.student_group2)
        obj_build.make_correct_ag_test_command_result(
            cls.ag_test_cmd, submission=cls.student_group2_submission)

        # --------- staff --------------
        cls.staff_group = obj_build.make_group(
            project=cls.project, members_role=ag_models.UserRole.staff)
        cls.staff = cls.staff_group.members.first()

        cls.staff_normal_submission = obj_build.build_submission(
            submission_group=cls.staff_group)
        obj_build.make_correct_ag_test_command_result(
            cls.ag_test_cmd, submission=cls.staff_normal_submission)

        cls.staff_best_submission = obj_build.build_submission(
            submission_group=cls.staff_group)
        obj_build.make_correct_ag_test_command_result(
            cls.ag_test_cmd, submission=cls.staff_best_submission)

        cls.staff_past_limit_submission = obj_build.build_submission(
            submission_group=cls.staff_group)
        obj_build.make_incorrect_ag_test_command_result(
            cls.ag_test_cmd, submission=cls.staff_past_limit_submission)

    # -------------------- Normal fdbk ----------------------------------

    def test_student_get_normal_fdbk_on_owned_submission(self):
        self.fail()

    def test_student_get_normal_fdbk_on_non_owned_submission_permission_denied(self):
        self.fail()

    def test_student_get_normal_fdbk_on_owned_past_limit_submission_permission_denied(self):
        self.fail()

    def test_staff_get_normal_fdbk_on_owned_submission(self):
        self.fail()

    def test_staff_get_normal_fdbk_on_owned_past_limit_submission(self):
        self.fail()

    def test_staff_get_normal_fdbk_on_non_owned_submission_permission_denied(self):
        self.fail()

    # -------------------- Past limit fdbk ----------------------------------

    def test_student_get_past_limit_fdbk_on_owned_past_limit_submission(self):
        self.fail()

    def test_student_get_past_limit_fdbk_on_owned_non_past_limit_submission_permission_denied(self):
        self.fail()

    def test_staff_get_past_limit_fdbk_on_owned_submission(self):
        self.fail()

    def test_staff_get_past_limit_fdbk_on_owned_non_past_limit_submission(self):
        self.fail()

    def test_staff_get_past_limit_fdbk_on_non_owned_past_limit_submission_permission_denied(self):
        self.fail()

    # -------------------- Ultimate fdbk ----------------------------------

    def test_student_get_ultimate_fdbk_on_owned_ultimate_submission(self):
        self.fail()

    def test_student_get_ultimate_fdbk_on_owned_non_ultimate_submission_permission_denied(self):
        # most recent
        # best normal (keep?)
        # best max
        self.fail()

    def test_student_get_ultimate_fdbk_but_ultimate_fdbk_hidden_permission_denied(self):
        self.fail()

    def test_student_get_ultimate_fdbk_but_deadline_not_past_permission_denied(self):
        self.fail()

    def test_student_get_ultimate_fdbk_but_extension_not_past_permission_denied(self):
        self.fail()

    def test_staff_get_ultimate_fdbk_on_owned_ultimate_submission(self):
        self.fail()

    def test_staff_get_ultimate_fdbk_on_owned_non_ultimate_submission(self):
        self.fail()

    def test_staff_get_ultimate_fdbk_before_deadline(self):
        self.fail()

    def test_staff_get_ultimate_fdbk_on_non_owned_ultimate_submission_permission_denied(self):
        self.fail()

    # -------------------- Max fdbk ----------------------------------

    def test_student_get_max_fdbk_permission_denied(self):
        self.fail()

    def test_staff_get_max_fdbk_on_owned_submission(self):
        self.fail()

    def test_staff_get_max_fdbk_on_non_owned_ultimate_submission(self):
        self.fail()

    def test_staff_get_max_fdbk_on_non_owned_ultimate_submission_despite_ultimate_fdbk_hidden(self):
        self.fail()

    def test_staff_get_max_fdbk_on_non_owned_non_ultimate_submission_permission_denied(self):
        # most recent
        # best normal (keep?)
        # best max
        self.fail()

    def test_staff_get_max_fdbk_on_non_owned_ultimate_submission_before_deadline_permission_denied(self):
        self.fail()

    def test_staff_get_max_fdbk_on_non_owned_ultimate_submission_before_extension_permission_denied(self):
        self.fail()


def submission_url(submission):
    return reverse('submission-detail', kwargs={'pk': submission.pk})


def submission_remove_from_queue_url(submission):
    return reverse('submission-remove-from-queue',
                   kwargs={'pk': submission.pk})


def file_url(submission, filename):
    query_params = QueryDict(mutable=True)
    query_params.update({'filename': filename})
    return (reverse('submission-file', kwargs={'pk': submission.pk}) + '?' +
            query_params.urlencode())
