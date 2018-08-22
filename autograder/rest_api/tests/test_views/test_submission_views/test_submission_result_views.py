import json

from django.http import FileResponse, QueryDict
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.models.ag_test.ag_test_command import MAX_AG_TEST_COMMAND_FDBK_SETTINGS
from autograder.core.models.get_ultimate_submissions import get_ultimate_submission
from autograder.core.submission_feedback import update_denormalized_ag_test_results
from autograder.core.tests.test_submission_feedback.fdbk_getter_shortcuts import (
    get_suite_fdbk, get_cmd_fdbk, get_submission_fdbk)
from autograder.grading_tasks.tasks import mark_submission_as_finished
from autograder.utils.testing import UnitTestBase


class SubmissionResultTestCase(UnitTestBase):
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
        self.project.validate_and_update(
            submission_limit_per_day=2, visible_to_students=True,
            hide_ultimate_submission_fdbk=False)
        self.course = self.project.course

        # --------- student 1 --------------
        self.student_group1 = obj_build.make_group(project=self.project)
        self.student1 = self.student_group1.members.first()

        self.student_group1_normal_submission = obj_build.make_finished_submission(
            group=self.student_group1)
        self.student1_normal_res = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_group1_normal_submission)
        self.student_group1_normal_submission = update_denormalized_ag_test_results(
            self.student_group1_normal_submission.pk)

        self.student_group1_best_submission = obj_build.make_finished_submission(
            group=self.student_group1)
        self.student1_best_res = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_group1_best_submission)
        self.student_group1_best_submission = update_denormalized_ag_test_results(
            self.student_group1_best_submission.pk)

        self.student_group1_past_limit_submission = obj_build.make_finished_submission(
            group=self.student_group1, is_past_daily_limit=True)
        self.student1_past_limit_res = obj_build.make_incorrect_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_group1_past_limit_submission)
        self.student_group1_past_limit_submission = update_denormalized_ag_test_results(
            self.student_group1_past_limit_submission.pk)

        self.student_group1_most_recent_submission = self.student_group1_past_limit_submission
        self.student1_most_recent_res = self.student1_past_limit_res

        # --------- student 2 --------------
        self.student_group2 = obj_build.make_group(project=self.project)
        self.student2 = self.student_group2.members.first()

        # --------- staff --------------
        self.staff_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.staff)
        self.staff = self.staff_group.members.first()

        self.staff_normal_submission = obj_build.make_finished_submission(
            group=self.staff_group)
        self.staff_normal_res = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.staff_normal_submission)
        self.staff_normal_submission = update_denormalized_ag_test_results(
            self.staff_normal_submission.pk)

        self.staff_best_submission = obj_build.make_finished_submission(
            group=self.staff_group)
        self.staff_best_res = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.staff_best_submission)
        self.staff_best_submission = update_denormalized_ag_test_results(
            self.staff_best_submission.pk)

        self.staff_past_limit_submission = obj_build.make_finished_submission(
            group=self.staff_group, is_past_daily_limit=True)
        self.staff_past_limit_res = obj_build.make_incorrect_ag_test_command_result(
            self.ag_test_cmd, submission=self.staff_past_limit_submission)
        self.staff_past_limit_submission = update_denormalized_ag_test_results(
            self.staff_past_limit_submission.pk)

        self.staff_most_recent_submission = self.staff_past_limit_submission
        self.staff_most_recent_res = self.staff_past_limit_res

        self.assertFalse(self.project.hide_ultimate_submission_fdbk)
        self.assertTrue(self.project.visible_to_students)
        self.assertTrue(self.student_group1_past_limit_submission.is_past_daily_limit)
        self.assertTrue(self.staff_past_limit_submission.is_past_daily_limit)

    def test_staff_get_any_fdbk_on_owned_submission(self):
        self.project.validate_and_update(
            closing_time=timezone.now() - timezone.timedelta(minutes=2))
        self.client.force_authenticate(self.staff)
        for submission, res in [(self.staff_normal_submission, self.staff_normal_res),
                                (self.staff_best_submission, self.staff_best_res),
                                (self.staff_past_limit_submission, self.staff_past_limit_res)]:
            self.do_get_fdbk_test(self.client, submission, ag_models.FeedbackCategory.normal)

            self.do_get_output_and_diff_test(self.client, submission, res,
                                             ag_models.FeedbackCategory.normal)

    def test_invalid_fdbk_category_requested(self):
        self.client.force_authenticate(self.staff)
        query_params = QueryDict(mutable=True)
        query_params.update({'feedback_category': 'not a value'})
        url = (reverse('submission-results', kwargs={'pk': self.staff_normal_submission.pk})
               + '?' + query_params.urlencode())
        response = self.client.get(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('feedback_category', response.data)

    def test_missing_fdbk_category(self):
        self.client.force_authenticate(self.staff)
        url = reverse('submission-results',
                      kwargs={'pk': self.staff_normal_submission.pk})
        response = self.client.get(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('feedback_category', response.data)

    # -------------------- Normal fdbk ----------------------------------

    def test_student_get_normal_fdbk_on_owned_submission(self):
        self.client.force_authenticate(self.student1)
        self.do_get_fdbk_test(self.client, self.student_group1_normal_submission,
                              ag_models.FeedbackCategory.normal)

        self.do_get_output_and_diff_test(self.client, self.student_group1_normal_submission,
                                         self.student1_normal_res,
                                         ag_models.FeedbackCategory.normal)

    def test_student_get_normal_fdbk_on_non_owned_submission_permission_denied(self):
        self.client.force_authenticate(self.student2)
        self.do_get_fdbk_permission_denied_test(self.client, self.student_group1_normal_submission,
                                                ag_models.FeedbackCategory.normal)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_normal_submission,
            self.student1_normal_res, ag_models.FeedbackCategory.normal)

    def test_handgrader_get_normal_fdbk_on_student_submission_permission_denied(self):
        handgrader = obj_build.create_dummy_user()
        self.course.handgraders.add(handgrader)
        self.client.force_authenticate(handgrader)
        self.do_get_fdbk_permission_denied_test(self.client,
                                                self.student_group1_normal_submission,
                                                ag_models.FeedbackCategory.normal)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_normal_submission,
            self.student1_normal_res, ag_models.FeedbackCategory.normal)

    def test_student_get_normal_fdbk_on_owned_past_limit_submission_permission_denied(self):
        self.client.force_authenticate(self.student1)
        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_past_limit_submission,
            ag_models.FeedbackCategory.normal)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_past_limit_submission,
            self.student1_past_limit_res,
            ag_models.FeedbackCategory.normal)

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
        self.client.force_authenticate(self.student1)
        self.do_get_fdbk_test(self.client, self.student_group1_past_limit_submission,
                              ag_models.FeedbackCategory.past_limit_submission)

        self.do_get_output_and_diff_test(self.client, self.student_group1_past_limit_submission,
                                         self.student1_past_limit_res,
                                         ag_models.FeedbackCategory.past_limit_submission)

    def test_student_get_past_limit_fdbk_non_owned_past_limit_submission_permission_denied(self):
        self.client.force_authenticate(self.student2)
        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_past_limit_submission,
            ag_models.FeedbackCategory.past_limit_submission)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_past_limit_submission,
            self.student1_past_limit_res,
            ag_models.FeedbackCategory.past_limit_submission)

    def test_student_get_past_limit_fdbk_owned_non_past_limit_submission_permission_denied(self):
        self.client.force_authenticate(self.student1)
        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_normal_submission,
            ag_models.FeedbackCategory.past_limit_submission)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_normal_submission,
            self.student1_past_limit_res,
            ag_models.FeedbackCategory.past_limit_submission)

    def test_staff_get_past_limit_fdbk_on_non_owned_past_limit_submission_permission_denied(self):
        self.client.force_authenticate(self.staff)
        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_past_limit_submission,
            ag_models.FeedbackCategory.past_limit_submission)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_past_limit_submission,
            self.student1_past_limit_res,
            ag_models.FeedbackCategory.past_limit_submission)

    # -------------------- Ultimate fdbk ----------------------------------

    def test_student_get_ultimate_fdbk_on_owned_ultimate_submission(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
        self.client.force_authenticate(self.student1)

        self.do_get_fdbk_test(self.client, self.student_group1_most_recent_submission,
                              ag_models.FeedbackCategory.ultimate_submission)
        self.do_get_output_and_diff_test(self.client, self.student_group1_most_recent_submission,
                                         self.student1_most_recent_res,
                                         ag_models.FeedbackCategory.ultimate_submission)

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)
        self.do_get_fdbk_test(self.client, self.student_group1_best_submission,
                              ag_models.FeedbackCategory.ultimate_submission)
        self.do_get_output_and_diff_test(self.client, self.student_group1_best_submission,
                                         self.student1_best_res,
                                         ag_models.FeedbackCategory.ultimate_submission)

        past_deadline = timezone.now() - timezone.timedelta(2)
        past_extension = timezone.now() - timezone.timedelta(2)
        for closing_time, extension in [(past_deadline, None),
                                        (past_deadline, past_extension)]:
            self.project.validate_and_update(closing_time=closing_time)
            self.student_group1.validate_and_update(extended_due_date=extension)
            self.do_get_fdbk_test(self.client, self.student_group1_best_submission,
                                  ag_models.FeedbackCategory.ultimate_submission)
            self.do_get_output_and_diff_test(self.client, self.student_group1_best_submission,
                                             self.student1_best_res,
                                             ag_models.FeedbackCategory.ultimate_submission)

    def test_student_get_ultimate_fdbk_on_owned_non_ultimate_submission_permission_denied(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
        self.client.force_authenticate(self.student1)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_best_submission,
            ag_models.FeedbackCategory.ultimate_submission)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_best_submission,
            self.student1_best_res, ag_models.FeedbackCategory.ultimate_submission)

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)
        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.ultimate_submission)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.ultimate_submission)

    def test_student_get_ultimate_fdbk_on_non_owned_ultimate_submission_permission_denied(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
        self.client.force_authenticate(self.student2)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.ultimate_submission)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.ultimate_submission)

    def test_student_get_ultimate_fdbk_but_ultimate_fdbk_hidden_permission_denied(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
        self.project.validate_and_update(hide_ultimate_submission_fdbk=True)
        self.client.force_authenticate(self.student1)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.ultimate_submission)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.ultimate_submission)

    def test_student_get_ultimate_fdbk_but_deadline_not_past_permission_denied(self):
        self.project.validate_and_update(
            closing_time=timezone.now() + timezone.timedelta(minutes=3))

        self.client.force_authenticate(self.student1)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.ultimate_submission)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.ultimate_submission)

    def test_student_get_ultimate_fdbk_but_extension_not_past_permission_denied(self):
        self.project.validate_and_update(
            closing_time=timezone.now() - timezone.timedelta(minutes=2))
        self.student_group1.validate_and_update(
            extended_due_date=timezone.now() + timezone.timedelta(minutes=3))

        self.client.force_authenticate(self.student1)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.ultimate_submission)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.ultimate_submission)

    def test_staff_get_ultimate_fdbk_on_non_owned_ultimate_submission_permission_denied(self):
        self.client.force_authenticate(self.staff)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.ultimate_submission)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.ultimate_submission)

    # -------------------- Max fdbk ----------------------------------

    def test_student_get_max_fdbk_permission_denied(self):
        self.client.force_authenticate(self.student1)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.max)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.max)

    def test_staff_get_max_fdbk_on_non_owned_ultimate_submission(self):
        self.client.force_authenticate(self.staff)
        for closing_time in None, timezone.now() - timezone.timedelta(minutes=5):
            self.project.validate_and_update(
                closing_time=closing_time,
                ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.most_recent)

            self.do_get_fdbk_test(self.client, self.student_group1_most_recent_submission,
                                  ag_models.FeedbackCategory.max)
            self.do_get_output_and_diff_test(
                self.client, self.student_group1_most_recent_submission,
                self.student1_most_recent_res, ag_models.FeedbackCategory.max)

            self.project.validate_and_update(
                ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)

            self.do_get_fdbk_test(self.client, self.student_group1_best_submission,
                                  ag_models.FeedbackCategory.max)
            self.do_get_output_and_diff_test(
                self.client, self.student_group1_best_submission,
                self.student1_best_res, ag_models.FeedbackCategory.max)

    def test_staff_get_max_fdbk_non_owned_ultimate_submission_despite_ultimate_fdbk_hidden(self):
        self.client.force_authenticate(self.staff)
        self.project.validate_and_update(hide_ultimate_submission_fdbk=True)

        self.do_get_fdbk_test(self.client, self.student_group1_most_recent_submission,
                              ag_models.FeedbackCategory.max)
        self.do_get_output_and_diff_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.max)

    def test_staff_get_max_fdbk_on_non_owned_non_ultimate_submission_permission_denied(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)

        self.client.force_authenticate(self.staff)
        self.do_get_fdbk_permission_denied_test(self.client, self.student_group1_best_submission,
                                                ag_models.FeedbackCategory.max)
        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_best_submission,
            self.student1_best_res, ag_models.FeedbackCategory.max)

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.max)
        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.max)

    def test_staff_get_max_fdbk_non_owned_ultimate_subm_before_deadline_permission_denied(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)

        self.client.force_authenticate(self.staff)
        self.project.validate_and_update(
            closing_time=timezone.now() + timezone.timedelta(minutes=5))
        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.max)
        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.max)

    def test_staff_get_max_fdbk_non_owned_ultimate_subm_before_extension_permission_denied(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)

        self.client.force_authenticate(self.staff)
        self.project.validate_and_update(
            closing_time=timezone.now() - timezone.timedelta(minutes=2))
        self.student_group1.validate_and_update(
            extended_due_date=timezone.now() + timezone.timedelta(minutes=2))

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.max)
        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.max)

    # -------------------------------------------------------------

    def test_cmd_result_output_or_diff_requested_on_cmd_in_not_visible_suite(self):
        self.ag_test_suite.validate_and_update(normal_fdbk_config={'visible': False})
        self.client.force_authenticate(self.student1)
        self.do_get_output_and_diff_on_hidden_ag_test_test(
            self.client, self.student_group1_normal_submission,
            self.student1_normal_res, ag_models.FeedbackCategory.normal)

    def test_cmd_result_output_or_diff_requested_on_cmd_in_not_visible_case(self):
        self.ag_test_case.validate_and_update(normal_fdbk_config={'visible': False})
        self.client.force_authenticate(self.student1)
        self.do_get_output_and_diff_on_hidden_ag_test_test(
            self.client, self.student_group1_normal_submission,
            self.student1_normal_res, ag_models.FeedbackCategory.normal)

    def test_cmd_result_output_or_diff_requested_on_not_visible_cmd(self):
        self.ag_test_cmd.validate_and_update(normal_fdbk_config={'visible': False})
        self.client.force_authenticate(self.student1)
        self.do_get_output_and_diff_on_hidden_ag_test_test(
            self.client, self.student_group1_normal_submission,
            self.student1_normal_res, ag_models.FeedbackCategory.normal)

    def test_cmd_result_output_or_diff_requested_individual_cmds_not_shown(self):
        self.ag_test_case.validate_and_update(
            normal_fdbk_config={'show_individual_commands': False})
        self.client.force_authenticate(self.student1)
        self.do_get_output_and_diff_on_hidden_ag_test_test(
            self.client, self.student_group1_normal_submission,
            self.student1_normal_res, ag_models.FeedbackCategory.normal)

    def test_cmd_result_output_or_diff_requested_individual_cases_not_shown(self):
        self.ag_test_suite.validate_and_update(normal_fdbk_config={'show_individual_tests': False})
        self.client.force_authenticate(self.student1)
        self.do_get_output_and_diff_on_hidden_ag_test_test(
            self.client, self.student_group1_normal_submission,
            self.student1_normal_res, ag_models.FeedbackCategory.normal)

    def test_cmd_diff_with_non_utf_chars(self):
        non_utf_bytes = b'\x80 and some other stuff just because\n'
        output = 'some stuff'
        self.ag_test_cmd.validate_and_update(
            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stdout_text=output,
            expected_stderr_source=ag_models.ExpectedOutputSource.text,
            expected_stderr_text=output,
        )
        with open(self.staff_normal_res.stdout_filename, 'wb') as f:
            f.write(non_utf_bytes)
        with open(self.staff_normal_res.stderr_filename, 'wb') as f:
            f.write(non_utf_bytes)
        self.client.force_authenticate(self.staff)
        url = (reverse('ag-test-cmd-result-stdout-diff',
                       kwargs={'pk': self.staff_normal_submission.pk,
                               'result_pk': self.staff_normal_res.pk})
               + '?feedback_category=max')

        expected_diff = ['- ' + output, '+ ' + non_utf_bytes.decode('utf-8', 'surrogateescape')]
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(expected_diff, json.loads(response.content.decode('utf-8')))

        url = (reverse('ag-test-cmd-result-stderr-diff',
                       kwargs={'pk': self.staff_normal_submission.pk,
                               'result_pk': self.staff_normal_res.pk})
               + '?feedback_category=max')
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(expected_diff, json.loads(response.content.decode('utf-8')))

    def test_cmd_result_output_or_diff_requested_cmd_doesnt_exist_404(self):
        urls_and_field_names = self.get_output_and_diff_test_urls(
            self.staff_normal_submission,
            self.staff_normal_res,
            ag_models.FeedbackCategory.max)

        self.ag_test_cmd.delete()

        self.client.force_authenticate(self.staff)
        for url, field_name in urls_and_field_names:
            response = self.client.get(url)
            self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    # -------------------------------------------------------------

    def test_get_suite_result_setup_output_visible(self):
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.show_setup_stdout)
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.show_setup_stderr)
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.visible)

        self.client.force_authenticate(self.student1)

        suite_res = self.student1_normal_res.ag_test_case_result.ag_test_suite_result
        self._do_suite_result_output_test(self.client, suite_res.submission, suite_res,
                                          ag_models.FeedbackCategory.normal)

    def test_get_suite_result_setup_output_hidden(self):
        self.ag_test_suite.validate_and_update(normal_fdbk_config={'show_setup_stdout': False})
        self.ag_test_suite.validate_and_update(normal_fdbk_config={'show_setup_stderr': False})
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.visible)

        self.client.force_authenticate(self.student1)

        suite_res = self.student1_normal_res.ag_test_case_result.ag_test_suite_result
        self._do_suite_result_output_test(self.client, suite_res.submission, suite_res,
                                          ag_models.FeedbackCategory.normal)

    def test_suite_result_output_requested_on_not_visible_suite(self):
        self.ag_test_suite.validate_and_update(normal_fdbk_config={'visible': False})
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.show_setup_stdout)
        self.assertTrue(self.ag_test_suite.normal_fdbk_config.show_setup_stderr)

        self.client.force_authenticate(self.student1)

        suite_res = self.student1_normal_res.ag_test_case_result.ag_test_suite_result
        self._do_suite_result_output_test(self.client, suite_res.submission, suite_res,
                                          ag_models.FeedbackCategory.normal)

    def test_suite_result_output_requested_suite_doesnt_exist_404(self):
        self.client.force_authenticate(self.staff)

        suite_result = self.staff_normal_res.ag_test_case_result.ag_test_suite_result

        with suite_result.open_setup_stdout('w') as f:
            f.write('weee')
        with suite_result.open_setup_stderr('w') as f:
            f.write('wooo')

        field_names = ['setup_stdout', 'setup_stderr']
        url_lookups = [
            'ag-test-suite-result-stdout',
            'ag-test-suite-result-stderr'
        ]

        suite_result_pk = suite_result.pk
        self.ag_test_suite.delete()

        for field_name, url_lookup in zip(field_names, url_lookups):
            url_kwargs = {
                'pk': self.staff_normal_submission.pk,
                'result_pk': suite_result_pk}
            url = (reverse(url_lookup, kwargs=url_kwargs)
                   + f'?feedback_category={ag_models.FeedbackCategory.max.value}')
            response = self.client.get(url)
            self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def _do_suite_result_output_test(self, client, submission, suite_result, fdbk_category,
                                     expect_404=False):
        with suite_result.open_setup_stdout('w') as f:
            f.write('adkjfaksdjf;akjsdf;')
        with suite_result.open_setup_stderr('w') as f:
            f.write('qewiruqpewpuir')

        field_names = ['setup_stdout', 'setup_stderr']
        url_lookups = [
            'ag-test-suite-result-stdout',
            'ag-test-suite-result-stderr'
        ]
        for field_name, url_lookup in zip(field_names, url_lookups):
            print(url_lookup)
            url = (reverse(url_lookup,
                           kwargs={'pk': submission.pk, 'result_pk': suite_result.pk})
                   + '?feedback_category={}'.format(fdbk_category.value))
            response = client.get(url)
            if expect_404:
                self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)
                continue

            fdbk = get_suite_fdbk(suite_result, fdbk_category)
            expected = getattr(fdbk, field_name)
            if expected is None or not fdbk.fdbk_conf.visible:
                self.assertIsNone(response.data)
            else:
                self.assertEqual(expected.read(),
                                 b''.join((chunk for chunk in response.streaming_content)))

    # -------------------------------------------------------------

    def test_get_fdbk_user_cannot_view_project_permission_denied(self):
        self.project.validate_and_update(visible_to_students=False)
        self.client.force_authenticate(self.student1)
        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_normal_submission,
            ag_models.FeedbackCategory.normal)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_normal_submission,
            self.student1_normal_res, ag_models.FeedbackCategory.normal)

    # -------------------------------------------------------------

    OUTPUT_AND_DIFF_FIELDS_TO_URL_LOOKUPS = {
        'stdout': 'ag-test-cmd-result-stdout',
        'stderr': 'ag-test-cmd-result-stderr',
        'stdout_diff': 'ag-test-cmd-result-stdout-diff',
        'stderr_diff': 'ag-test-cmd-result-stderr-diff',
    }

    def do_get_fdbk_test(self, client,
                         submission: ag_models.Submission,
                         fdbk_category: ag_models.FeedbackCategory):
        query_params = QueryDict(mutable=True)
        query_params.update({'feedback_category': fdbk_category.value})
        url = (reverse('submission-results', kwargs={'pk': submission.pk})
               + '?' + query_params.urlencode())
        response = client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(get_submission_fdbk(submission, fdbk_category).to_dict(),
                         response.data)

    def do_get_fdbk_permission_denied_test(self, client,
                                           submission: ag_models.Submission,
                                           fdbk_category: ag_models.FeedbackCategory):
        query_params = QueryDict(mutable=True)
        query_params.update({'feedback_category': fdbk_category.value})
        url = (reverse('submission-results', kwargs={'pk': submission.pk})
               + '?' + query_params.urlencode())
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
            expected = getattr(get_cmd_fdbk(cmd_result, fdbk_category), field_name)
            if isinstance(expected, core_ut.DiffResult):
                self.assertEqual(expected.diff_content,
                                 json.loads(response.content.decode('utf-8')))
            else:
                if not isinstance(response, FileResponse):
                    self.assertIsNone(response.data)
                else:
                    self.assertEqual(
                        expected.read(), b''.join((chunk for chunk in response.streaming_content)))

    def do_get_output_and_diff_on_hidden_ag_test_test(self, client,
                                                      submission: ag_models.Submission,
                                                      cmd_result: ag_models.AGTestCommandResult,
                                                      fdbk_category: ag_models.FeedbackCategory):
        urls_and_field_names = self.get_output_and_diff_test_urls(
            submission, cmd_result, fdbk_category)
        for url, field_name in urls_and_field_names:
            response = client.get(url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertIsNone(response.data)

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
        for field_name, url_lookup in self.OUTPUT_AND_DIFF_FIELDS_TO_URL_LOOKUPS.items():
            query_params = QueryDict(mutable=True)
            query_params.update({
                'feedback_category': fdbk_category.value
            })
            url = (reverse(url_lookup,
                           kwargs={'pk': submission.pk, 'result_pk': cmd_result.pk})
                   + '?' + query_params.urlencode())
            result.append((url, field_name))

        return result


class StudentTestSuiteResultsTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()
        self.student_suite = ag_models.StudentTestSuite.objects.validate_and_create(
            name='suitte', project=self.project,
            buggy_impl_names=['bug{}'.format(i) for i in range(4)],
            setup_command={
                'cmd': 'echo "hello world"'
            },
            points_per_exposed_bug=2,
            normal_fdbk_config={
                'bugs_exposed_fdbk_level': ag_models.BugsExposedFeedbackLevel.num_bugs_exposed,
                'show_invalid_test_names': True,
            }
        )  # type: ag_models.StudentTestSuite

        self.submission = obj_build.make_submission(
            group=obj_build.make_group(
                project=self.project, members_role=obj_build.UserRole.admin))

        self.setup_stdout = 'setupp stdouttt'
        self.setup_stderr = 'sortoop stdear'
        self.get_test_names_stdout = 'test narmes stdout'
        self.get_test_names_stderr = 'test nurmes stderr'
        self.validity_check_stdout = 'valooditee chorck stdout'
        self.validity_check_stderr = 'valaerditi charck stderr'
        self.buggy_impls_stdout = 'borgy oomples stdout'
        self.buggy_impls_stderr = 'baergy eyemples stderr'

        setup_result = ag_models.AGCommandResult.objects.validate_and_create(
            return_code=0
        )  # type: ag_models.AGCommandResult
        with open(setup_result.stdout_filename, 'w') as f:
            f.write(self.setup_stdout)
        with open(setup_result.stderr_filename, 'w') as f:
            f.write(self.setup_stderr)

        get_test_names_result = ag_models.AGCommandResult.objects.validate_and_create(
            return_code=0
        )  # type: ag_models.AGCommandResult
        with open(get_test_names_result.stdout_filename, 'w') as f:
            f.write(self.get_test_names_stdout)
        with open(get_test_names_result.stderr_filename, 'w') as f:
            f.write(self.get_test_names_stderr)

        student_tests = ['test{}'.format(i) for i in range(5)]
        self.student_suite_result = ag_models.StudentTestSuiteResult.objects.validate_and_create(
            student_test_suite=self.student_suite,
            submission=self.submission,
            student_tests=student_tests,
            invalid_tests=student_tests[:-1],
            timed_out_tests=student_tests[:1],
            bugs_exposed=self.student_suite.buggy_impl_names[:-1],
            setup_result=setup_result,
            get_test_names_result=get_test_names_result
        )  # type: ag_models.StudentTestSuiteResult

        with open(self.student_suite_result.validity_check_stdout_filename, 'w') as f:
            f.write(self.validity_check_stdout)
        with open(self.student_suite_result.validity_check_stderr_filename, 'w') as f:
            f.write(self.validity_check_stderr)
        with open(self.student_suite_result.grade_buggy_impls_stdout_filename, 'w') as f:
            f.write(self.buggy_impls_stdout)
        with open(self.student_suite_result.grade_buggy_impls_stderr_filename, 'w') as f:
            f.write(self.buggy_impls_stderr)

        self.client = APIClient()
        self.admin = self.submission.group.members.first()

        self.setup_stdout_base_url = reverse(
            'student-suite-setup-stdout',
            kwargs={'pk': self.submission.pk, 'result_pk': self.student_suite_result.pk})
        self.setup_stderr_base_url = reverse(
            'student-suite-setup-stderr',
            kwargs={'pk': self.submission.pk, 'result_pk': self.student_suite_result.pk})
        self.get_test_names_stdout_base_url = reverse(
            'student-suite-get-student-test-names-stdout',
            kwargs={'pk': self.submission.pk, 'result_pk': self.student_suite_result.pk})
        self.get_test_names_stderr_base_url = reverse(
            'student-suite-get-student-test-names-stderr',
            kwargs={'pk': self.submission.pk, 'result_pk': self.student_suite_result.pk})
        self.validity_check_stdout_base_url = reverse(
            'student-suite-validity-check-stdout',
            kwargs={'pk': self.submission.pk, 'result_pk': self.student_suite_result.pk})
        self.validity_check_stderr_base_url = reverse(
            'student-suite-validity-check-stderr',
            kwargs={'pk': self.submission.pk, 'result_pk': self.student_suite_result.pk})
        self.buggy_impls_stdout_base_url = reverse(
            'student-suite-grade-buggy-impls-stdout',
            kwargs={'pk': self.submission.pk, 'result_pk': self.student_suite_result.pk})
        self.buggy_impls_stderr_base_url = reverse(
            'student-suite-grade-buggy-impls-stderr',
            kwargs={'pk': self.submission.pk, 'result_pk': self.student_suite_result.pk})

        self.base_urls = [
            self.setup_stdout_base_url,
            self.setup_stderr_base_url,
            self.get_test_names_stdout_base_url,
            self.get_test_names_stderr_base_url,
            self.validity_check_stdout_base_url,
            self.validity_check_stderr_base_url,
            self.buggy_impls_stdout_base_url,
            self.buggy_impls_stderr_base_url,
        ]

        self.submission.refresh_from_db()

    def test_suite_results_included_in_submission_detail_response(self):
        self.client.force_authenticate(self.admin)

        self.maxDiff = None
        self.assertNotEqual(0, self.submission.student_test_suite_results.count())

        query_params = QueryDict(mutable=True)
        query_params.update({'feedback_category': ag_models.FeedbackCategory.max.value})
        url = (reverse('submission-results', kwargs={'pk': self.submission.pk})
               + '?' + query_params.urlencode())

        response = self.client.get(url)
        expected_content = [
            self.student_suite_result.get_fdbk(ag_models.FeedbackCategory.max).to_dict()]
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(expected_content, response.data['student_test_suite_results'])

    def test_get_setup_output(self):
        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, self.setup_stdout, self.setup_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.normal,
            status.HTTP_200_OK, None, self.setup_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, self.setup_stderr, self.setup_stderr_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.normal,
            status.HTTP_200_OK, None, self.setup_stderr_base_url)

    def test_get_setup_output_no_setup_cmd(self):
        self.student_suite.validate_and_update(use_setup_command=False)
        self.student_suite_result.setup_result = None
        self.student_suite_result.save()

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, None, self.setup_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, None, self.setup_stderr_base_url)

    def test_get_get_test_names_result_output(self):
        # NOTE: Whether a user can view the get_test_names output does not
        # depend on feedback configuration. Instead, this output
        # is always available to staff.
        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, self.get_test_names_stdout, self.get_test_names_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.normal,
            status.HTTP_200_OK, None, self.get_test_names_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, self.get_test_names_stderr, self.get_test_names_stderr_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.normal,
            status.HTTP_200_OK, None, self.get_test_names_stderr_base_url)

    def test_get_validity_check_output(self):
        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, self.validity_check_stdout, self.validity_check_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.normal,
            status.HTTP_200_OK, None, self.validity_check_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, self.validity_check_stderr, self.validity_check_stderr_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.normal,
            status.HTTP_200_OK, None, self.validity_check_stderr_base_url)

    def test_get_buggy_impls_output(self):
        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, self.buggy_impls_stdout, self.buggy_impls_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.normal,
            status.HTTP_200_OK, None, self.buggy_impls_stdout_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.max,
            status.HTTP_200_OK, self.buggy_impls_stderr, self.buggy_impls_stderr_base_url)

        self.do_get_output_test(
            self.client, self.admin, ag_models.FeedbackCategory.normal,
            status.HTTP_200_OK, None, self.buggy_impls_stderr_base_url)

    def test_get_output_suite_hidden(self):
        self.maxDiff = None
        max_fdbk_settings = self.student_suite_result.get_fdbk(
            ag_models.FeedbackCategory.max).fdbk_settings
        staff_viewer_fdbk_settings = self.student_suite_result.get_fdbk(
            ag_models.FeedbackCategory.staff_viewer).fdbk_settings
        self.assertEqual(max_fdbk_settings, staff_viewer_fdbk_settings)

        self.student_suite.validate_and_update(staff_viewer_fdbk_config={
            'visible': False
        })

        for url in self.base_urls:
            self.do_get_output_test(
                self.client, self.admin, ag_models.FeedbackCategory.staff_viewer,
                status.HTTP_200_OK, None, url)

    def test_get_output_suite_not_found(self):
        url_lookups = [
            'student-suite-setup-stdout',
            'student-suite-setup-stderr',
            'student-suite-get-student-test-names-stdout',
            'student-suite-get-student-test-names-stderr',
            'student-suite-validity-check-stdout',
            'student-suite-validity-check-stderr',
            'student-suite-grade-buggy-impls-stdout',
            'student-suite-grade-buggy-impls-stderr',
        ]

        for url_lookup in url_lookups:
            url_with_bad_pk = reverse(url_lookup, kwargs={'pk': 9001, 'result_pk': 9002})
            self.do_get_output_test(
                self.client, self.admin, ag_models.FeedbackCategory.max,
                status.HTTP_404_NOT_FOUND, None, url_with_bad_pk)

    def do_get_output_test(self, client: APIClient, user, fdbk_category,
                           expected_status, expected_output, base_url):
        client.force_authenticate(user)
        query_params = QueryDict(mutable=True)
        query_params.update({'feedback_category': fdbk_category.value})

        url = base_url + '?' + query_params.urlencode()
        response = client.get(url)

        self.assertEqual(expected_status, response.status_code)
        if response.status_code != status.HTTP_200_OK:
            return

        if expected_output is None:
            self.assertIsNone(response.data)
        else:
            self.assertEqual(expected_output,
                             ''.join((chunk.decode() for chunk in response.streaming_content)))


class SubmissionResultsCachingTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_submission_normal_fdbk_results_cached_by_default(self):
        self.maxDiff = None
        cmd = obj_build.make_full_ag_test_command(
            normal_fdbk_config=MAX_AG_TEST_COMMAND_FDBK_SETTINGS)
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
            normal_fdbk_config=MAX_AG_TEST_COMMAND_FDBK_SETTINGS,
            ultimate_submission_fdbk_config=MAX_AG_TEST_COMMAND_FDBK_SETTINGS,
            past_limit_submission_fdbk_config=MAX_AG_TEST_COMMAND_FDBK_SETTINGS)
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
            normal_fdbk_config=MAX_AG_TEST_COMMAND_FDBK_SETTINGS,
            ultimate_submission_fdbk_config=MAX_AG_TEST_COMMAND_FDBK_SETTINGS,
            past_limit_submission_fdbk_config=MAX_AG_TEST_COMMAND_FDBK_SETTINGS)
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
            normal_fdbk_config=MAX_AG_TEST_COMMAND_FDBK_SETTINGS)
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
            normal_fdbk_config=MAX_AG_TEST_COMMAND_FDBK_SETTINGS,
            ag_test_case=obj_build.make_ag_test_case(
                ag_test_suite=obj_build.make_ag_test_suite(project=project1)))

        project2 = obj_build.make_project(course)
        project2_cmd = obj_build.make_full_ag_test_command(
            normal_fdbk_config=MAX_AG_TEST_COMMAND_FDBK_SETTINGS,
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
                  fdbk_category: ag_models.FeedbackCategory=ag_models.FeedbackCategory.normal,
                  use_cache=True):
        return _make_submission_result_url(submission, fdbk_category, use_cache)


class UltimateSubmissionWithLateDaysTestCase(UnitTestBase):
    def test_group_member_with_different_ultimate_submission(self):
        """
        When a group member has a different ultimate submission than the
        rest of the group due to running out of late days,
        we need to make sure that the student can request ultimate
        submission feedback on their ultimate submission.
        """
        project = obj_build.make_project(
            visible_to_students=True, hide_ultimate_submission_fdbk=False,
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.most_recent)
        group = obj_build.make_group(num_members=2, project=project)

        doesnt_count_for_user, counts_for_user = group.members.all()

        first_submission = obj_build.make_finished_submission(group=group)
        most_recent_submission = obj_build.make_finished_submission(
            group=group, does_not_count_for=[doesnt_count_for_user.username])

        self.assertEqual(first_submission,
                         get_ultimate_submission(group, user=doesnt_count_for_user))
        self.assertEqual(most_recent_submission,
                         get_ultimate_submission(group, user=counts_for_user))

        client = APIClient()

        client.force_authenticate(counts_for_user)
        response = client.get(
            _make_submission_result_url(most_recent_submission,
                                        ag_models.FeedbackCategory.ultimate_submission))
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        client.force_authenticate(doesnt_count_for_user)
        # Shouldn't be able to get ultimate submission fdbk on
        # the most recent submission (that doesn't count for this user)
        response = client.get(
            _make_submission_result_url(most_recent_submission,
                                        ag_models.FeedbackCategory.ultimate_submission))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = client.get(
            _make_submission_result_url(first_submission,
                                        ag_models.FeedbackCategory.ultimate_submission))
        self.assertEqual(status.HTTP_200_OK, response.status_code)


def _make_submission_result_url(
        submission: ag_models.Submission,
        fdbk_category: ag_models.FeedbackCategory=ag_models.FeedbackCategory.normal,
        use_cache=True):
    url = reverse('submission-results', kwargs={'pk': submission.pk})
    url += '?feedback_category={}'.format(fdbk_category.value)
    if not use_cache:
        url += '&use_cache=false'

    return url
