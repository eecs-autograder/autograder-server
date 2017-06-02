import os

from django.core.urlresolvers import reverse
from django.http import QueryDict

from rest_framework import status
from rest_framework.test import APIClient

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

    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.ag_test_cmd = obj_build.make_full_ag_test_command(
            set_arbitrary_points=True,
            normal_fdbk_config={
                'return_code_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'show_points': True,
                'show_actual_stdout': True,
            },
            past_limit_submission_fdbk_config={
                'stdout_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'show_points': True,
                'show_actual_stderr': True,
            },
            ultimate_submission_fdbk_config={
                'stdout_fdbk_level': ag_models.ValueFeedbackLevel.expected_and_actual,
                'stderr_fdbk_level': ag_models.ValueFeedbackLevel.expected_and_actual
            }
        )
        self.ag_test_case = self.ag_test_cmd.ag_test_case
        self.ag_test_suite = self.ag_test_case.ag_test_suite
        self.project = self.ag_test_suite.project
        self.project.validate_and_update(submission_limit_per_day=2)
        self.course = self.project.course

        # --------- student 1 --------------
        self.student_group1 = obj_build.make_group(project=self.project)
        self.student1 = self.student_group1.members.first()

        self.student_group1_normal_submission = obj_build.build_submission(
            submission_group=self.student_group1)
        self.student1_normal_res = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_group1_normal_submission)

        self.student_group1_best_submission = obj_build.build_submission(
            submission_group=self.student_group1)
        self.student1_best_res = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_group1_best_submission)

        self.student_group1_past_limit_submission = obj_build.build_submission(
            submission_group=self.student_group1)
        self.student1_past_limit_res = obj_build.make_incorrect_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_group1_past_limit_submission)

        # --------- student 2 --------------
        self.student_group2 = obj_build.make_group(project=self.project)
        self.student2 = submission = self.student_group2.members.first()

        self.student_group2_submission = obj_build.build_submission(
            submission_group=self.student_group2)
        self.student2_res = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_group2_submission)

        # --------- staff --------------
        self.staff_group = obj_build.make_group(
            project=self.project, members_role=ag_models.UserRole.staff)
        self.staff = self.staff_group.members.first()

        self.staff_normal_submission = obj_build.build_submission(
            submission_group=self.staff_group)
        self. staff_normal_res = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.staff_normal_submission)

        self.staff_best_submission = obj_build.build_submission(
            submission_group=self.staff_group)
        self. staff_best_res = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.staff_best_submission)

        self.staff_past_limit_submission = obj_build.build_submission(
            submission_group=self.staff_group)
        self. staff_past_limit_res = obj_build.make_incorrect_ag_test_command_result(
            self.ag_test_cmd, submission=self.staff_past_limit_submission)

    # -------------------- Normal fdbk ----------------------------------

    def test_student_get_normal_fdbk_on_owned_submission(self):
        self.client.force_authenticate(self.student1)
        self.do_get_fdbk_test(self.client, self.student_group1_normal_submission,
                              ag_models.FeedbackCategory.normal)

        self.do_get_output_and_diff_test(self.client, self.student_group1_normal_submission,
                                         self.student1_normal_res,
                                         ag_models.FeedbackCategory.normal)

    def test_student_get_normal_fdbk_on_non_owned_submission_permission_denied(self):
        self.client.force_authenticate(self.student1)
        self.do_get_fdbk_permission_denied_test(self.client, self.student_group2_submission,
                                                ag_models.FeedbackCategory.normal)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group2_submission,
            self.student2_res, ag_models.FeedbackCategory.normal)

    def test_student_get_normal_fdbk_on_owned_past_limit_submission_permission_denied(self):
        self.client.force_authenticate(self.student1)
        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_past_limit_submission,
            ag_models.FeedbackCategory.normal)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_past_limit_submission,
            self.student1_past_limit_res,
            ag_models.FeedbackCategory.normal)

    def test_staff_get_normal_fdbk_on_owned_submission(self):
        self.fail()

    def test_staff_get_normal_fdbk_on_owned_past_limit_submission(self):
        self.fail()

    def test_staff_get_normal_fdbk_on_non_owned_submission_permission_denied(self):
        self.client.force_authenticate(self.staff)
        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_normal_submission,
            ag_models.FeedbackCategory.normal)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_normal_submission,
            self.student1_normal_res,
            ag_models.FeedbackCategory.normal)

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

    # -------------------------------------------------------------

    def test_output_or_diff_requested_on_cmd_in_not_visible_suite(self):
        self.fail()

    def test_output_or_diff_requested_on_cmd_in_not_visible_case(self):
        self.fail()

    def test_output_or_diff_requested_on_not_visible_cmd(self):
        self.fail()

    # -------------------------------------------------------------

    def test_get_fdbk_user_can_view_project(self):
        self.fail()

    def test_get_fdbk_user_cannot_view_project_permission_denied(self):
        self.fail()

    # -------------------------------------------------------------

    OUTPUT_AND_DIFF_FIELDS_TO_QUERY_PARAMS = {
        'stdout': 'stdout_for_cmd_result',
        'stderr': 'stderr_for_cmd_result',
        'stdout_diff': 'stdout_diff_for_cmd_result',
        'stderr_diff': 'stderr_diff_for_cmd_result',
    }

    def do_get_fdbk_test(self, client,
                         submission: ag_models.Submission,
                         fdbk_category: ag_models.FeedbackCategory):
        query_params = QueryDict(mutable=True)
        query_params.update({'feedback_category': fdbk_category.value})
        url = (reverse('submission-feedback', kwargs={'pk': submission.pk}) + '?' +
               query_params.urlencode())
        response = client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(submission.get_fdbk(fdbk_category), response.data)

    def do_get_fdbk_permission_denied_test(self, client,
                                           submission: ag_models.Submission,
                                           fdbk_category: ag_models.FeedbackCategory):
        query_params = QueryDict(mutable=True)
        query_params.update({'feedback_category': fdbk_category.value})
        url = (reverse('submission-feedback', kwargs={'pk': submission.pk}) + '?' +
               query_params.urlencode())
        response = client.get(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def do_get_output_and_diff_test(self, client,
                                    submission: ag_models.Submission,
                                    cmd_result: ag_models.AGTestCommandResult,
                                    fdbk_category: ag_models.FeedbackCategory):
        urls_and_field_names = self.get_output_and_diff_test_urls(
            submission, cmd_result, fdbk_category)
        for url, field_name in urls_and_field_names:
            response = client.get(url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertEqual(getattr(submission.get_fdbk(fdbk_category), field_name),
                             response.data)

    def do_get_output_and_diff_permission_denied_test(self, client,
                                                      submission: ag_models.Submission,
                                                      cmd_result: ag_models.AGTestCommandResult,
                                                      fdbk_category: ag_models.FeedbackCategory):
        urls_and_field_names = self.get_output_and_diff_test_urls(
            submission, cmd_result, fdbk_category)
        for url, field_name in urls_and_field_names:
            response = client.get(url)
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def get_output_and_diff_test_urls(self, submission: ag_models.Submission,
                                      cmd_result: ag_models.AGTestCommandResult,
                                      fdbk_category: ag_models.FeedbackCategory):
        result = []
        for field_name, query_param_name in self.OUTPUT_AND_DIFF_FIELDS_TO_QUERY_PARAMS.items():
            query_params = QueryDict(mutable=True)
            query_params.update({
                query_param_name: cmd_result.pk,
                'feedback_category': fdbk_category.value
            })
            url = (reverse('submission-feedback', kwargs={'pk': submission.pk}) + '?' +
                   query_params.urlencode())
            result.append((url, field_name))

        return result


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
