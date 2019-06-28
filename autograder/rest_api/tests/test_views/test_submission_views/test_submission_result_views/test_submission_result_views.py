import datetime
import json

from django.http import FileResponse, QueryDict
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from typing import Optional, BinaryIO

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.models.get_ultimate_submissions import get_ultimate_submission
from autograder.core.submission_feedback import update_denormalized_ag_test_results
from autograder.core.tests.test_submission_feedback.fdbk_getter_shortcuts import (
    get_cmd_fdbk, get_submission_fdbk)
from autograder.utils.testing import UnitTestBase

from .get_output_and_diff_test_urls import get_output_and_diff_test_urls, make_result_output_url


class _FeedbackTestsBase(UnitTestBase):
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
            },
            staff_viewer_fdbk_config={
                'stderr_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
                'show_points': True,
                'show_actual_stdout': True,
            }
        )
        self.ag_test_case = self.ag_test_cmd.ag_test_case
        self.ag_test_suite = self.ag_test_case.ag_test_suite
        # self.ag_test_suite.validate_and_update(
        #     normal_fdbk_config={
        #         'show_setup_stdout': True,
        #         'show_setup_stderr': True,
        #     },
        #     past_limit_submission_fdbk_config={
        #         'show_setup_stdout': True,
        #         'show_setup_stderr': False,
        #     },
        #     ultimate_submission_fdbk_config={
        #         'show_setup_stdout': False,
        #         'show_setup_stderr': True,
        #     },
        #     staff_viewer_fdbk_config={
        #         'show_setup_stdout': False,
        #         'show_setup_stderr': False,
        #     },
        # )
        self.project = self.ag_test_suite.project
        self.project.validate_and_update(
            visible_to_students=True,
            hide_ultimate_submission_fdbk=False,
            closing_time=timezone.now() + datetime.timedelta(days=1)
        )
        self.course = self.project.course

        self.student_group1 = obj_build.make_group(project=self.project)
        self.student1 = self.student_group1.members.first()

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
        cmd_fdbk = get_cmd_fdbk(cmd_result, fdbk_category)

        stdout_url = make_result_output_url(
            'ag-test-cmd-result-stdout', submission, cmd_result, fdbk_category)
        stderr_url = make_result_output_url(
            'ag-test-cmd-result-stderr', submission, cmd_result, fdbk_category)

        self.do_get_output_test(client, stdout_url, cmd_fdbk.stdout)
        self.do_get_output_test(client, stderr_url, cmd_fdbk.stderr)

        stdout_diff_url = make_result_output_url(
            'ag-test-cmd-result-stdout-diff', submission, cmd_result, fdbk_category)
        stderr_diff_url = make_result_output_url(
            'ag-test-cmd-result-stderr-diff', submission, cmd_result, fdbk_category)

        self.do_get_diff_test(client, stdout_diff_url, cmd_fdbk.stdout_diff)
        self.do_get_diff_test(client, stderr_diff_url, cmd_fdbk.stderr_diff)

        cmd_output_size_url = make_result_output_url(
            'ag-test-cmd-result-output-size', submission, cmd_result, fdbk_category)
        response = client.get(cmd_output_size_url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        expected = {
            'stdout_size': cmd_fdbk.get_stdout_size(),
            'stderr_size': cmd_fdbk.get_stderr_size(),
            'stdout_diff_size': cmd_fdbk.get_stdout_diff_size(),
            'stderr_diff_size': cmd_fdbk.get_stderr_diff_size(),
        }
        self.assertEqual(expected, response.data)

    def do_get_output_test(self, client, url, expected: Optional[BinaryIO]):
        response = client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        if expected is None:
            self.assertIsNone(response.data)
        else:
            self.assertEqual(
                expected.read(), b''.join((chunk for chunk in response.streaming_content)))

    def do_get_diff_test(self, client, url, expected: Optional[core_ut.DiffResult]):
        response = client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        if expected is None:
            self.assertIsNone(response.data)
        else:
            actual = ('' if response.content == b''
                      else json.loads(response.content.decode('utf-8')))
            self.assertEqual(expected.diff_content, actual)

    def do_get_output_and_diff_permission_denied_test(self, client,
                                                      submission: ag_models.Submission,
                                                      cmd_result: ag_models.AGTestCommandResult,
                                                      fdbk_category: ag_models.FeedbackCategory):
        urls_and_field_names = get_output_and_diff_test_urls(
            submission, cmd_result, fdbk_category)
        for url, field_name in urls_and_field_names:
            response = client.get(url)
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        cmd_output_size_url = make_result_output_url(
            'ag-test-cmd-result-output-size', submission, cmd_result, fdbk_category)
        response = client.get(cmd_output_size_url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class NormalSubmissionFeedbackTestCase(_FeedbackTestsBase):
    def setUp(self):
        super().setUp()

        self.student_group_normal_submission = obj_build.make_finished_submission(
            group=self.student_group1)
        self.normal_submission_result = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_group_normal_submission)
        self.student_group_normal_submission = update_denormalized_ag_test_results(
            self.student_group_normal_submission.pk)

    def test_student_get_own_normal_submission_normal_fdbk(self):
        self.client.force_authenticate(self.student1)
        self.do_get_fdbk_test(self.client, self.student_group_normal_submission,
                              ag_models.FeedbackCategory.normal)

        self.do_get_output_and_diff_test(self.client, self.student_group_normal_submission,
                                         self.normal_submission_result,
                                         ag_models.FeedbackCategory.normal)

    def test_student_get_own_normal_submission_non_normal_fdbk_permission_denied(self):
        self.client.force_authenticate(self.student1)

        # past_limit_submission
        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_normal_submission,
            ag_models.FeedbackCategory.past_limit_submission)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result,
            ag_models.FeedbackCategory.past_limit_submission)

        # ultimate_submission
        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_normal_submission,
            ag_models.FeedbackCategory.ultimate_submission)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result,
            ag_models.FeedbackCategory.ultimate_submission)

        # staff_viewer
        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_normal_submission,
            ag_models.FeedbackCategory.staff_viewer)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result,
            ag_models.FeedbackCategory.staff_viewer)

        # max
        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_normal_submission,
            ag_models.FeedbackCategory.max)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result,
            ag_models.FeedbackCategory.max)

    def test_student_get_other_student_submission_normal_fdbk_permission_denied(self):
        student2 = obj_build.make_student_user(self.course)
        self.client.force_authenticate(student2)

        self.do_get_fdbk_permission_denied_test(self.client, self.student_group_normal_submission,
                                                ag_models.FeedbackCategory.normal)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result, ag_models.FeedbackCategory.normal)

    def test_student_get_normal_submission_max_or_staff_viewer_fdbk_permission_denied(self):
        self.client.force_authenticate(self.student1)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_normal_submission,
            ag_models.FeedbackCategory.max)
        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result, ag_models.FeedbackCategory.max)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_normal_submission,
            ag_models.FeedbackCategory.staff_viewer)
        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result, ag_models.FeedbackCategory.staff_viewer)

    def test_student_get_normal_submission_fdbk_project_not_visible_permission_denied(self):
        self.project.validate_and_update(visible_to_students=False)
        self.client.force_authenticate(self.student1)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_normal_submission,
            ag_models.FeedbackCategory.normal)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result, ag_models.FeedbackCategory.normal)

        self.course.students.clear()
        self.project.validate_and_update(guests_can_submit=True)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_normal_submission,
            ag_models.FeedbackCategory.normal)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result, ag_models.FeedbackCategory.normal)

    def test_staff_get_student_normal_submission_normal_fdbk_permission_denied(self):
        staff = obj_build.make_staff_user(self.course)
        self.client.force_authenticate(staff)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_normal_submission,
            ag_models.FeedbackCategory.normal)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result,
            ag_models.FeedbackCategory.normal)

    def test_handgrader_get_student_normal_submission_normal_fdbk_permission_denied(self):
        handgrader = obj_build.make_handgrader_user(self.course)
        self.client.force_authenticate(handgrader)

        self.do_get_fdbk_permission_denied_test(self.client,
                                                self.student_group_normal_submission,
                                                ag_models.FeedbackCategory.normal)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result, ag_models.FeedbackCategory.normal)


class PastLimitSubmissionFeedbackTestCase(_FeedbackTestsBase):
    def setUp(self):
        super().setUp()

        self.student_group_past_limit_submission = obj_build.make_finished_submission(
            group=self.student_group1, is_past_daily_limit=True)
        self.past_limit_submission_result = obj_build.make_incorrect_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_group_past_limit_submission)

        self.student_group_past_limit_submission = update_denormalized_ag_test_results(
            self.student_group_past_limit_submission.pk)

    def test_student_get_own_past_limit_submission_past_limit_fdbk(self):
        self.client.force_authenticate(self.student1)
        self.do_get_fdbk_test(self.client, self.student_group_past_limit_submission,
                              ag_models.FeedbackCategory.past_limit_submission)

        # print(self.past_limit_submission_result.ag_test_case.ag_test_suite)
        self.do_get_output_and_diff_test(self.client, self.student_group_past_limit_submission,
                                         self.past_limit_submission_result,
                                         ag_models.FeedbackCategory.past_limit_submission)

    def test_student_get_other_student_past_limit_submission_past_limit_fdbk_permissn_denied(self):
        student2 = obj_build.make_student_user(self.course)
        self.client.force_authenticate(student2)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_past_limit_submission,
            ag_models.FeedbackCategory.past_limit_submission)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_past_limit_submission,
            self.past_limit_submission_result,
            ag_models.FeedbackCategory.past_limit_submission)

    def test_student_get_own_past_limit_submission_normal_fdbk_permission_denied(self):
        self.client.force_authenticate(self.student1)
        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_past_limit_submission,
            ag_models.FeedbackCategory.normal)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_past_limit_submission,
            self.past_limit_submission_result,
            ag_models.FeedbackCategory.normal)

    def test_student_get_past_limit_submission_max_or_staff_viewer_fdbk_permission_denied(self):
        self.client.force_authenticate(self.student1)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_past_limit_submission,
            ag_models.FeedbackCategory.max)
        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_past_limit_submission,
            self.past_limit_submission_result, ag_models.FeedbackCategory.max)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_past_limit_submission,
            ag_models.FeedbackCategory.staff_viewer)
        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_past_limit_submission,
            self.past_limit_submission_result, ag_models.FeedbackCategory.staff_viewer)

    def test_staff_get_student_past_limit_submission_past_limit_fdbk_permission_denied(self):
        staff = obj_build.make_staff_user(self.course)
        self.client.force_authenticate(staff)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_past_limit_submission,
            ag_models.FeedbackCategory.past_limit_submission)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_past_limit_submission,
            self.past_limit_submission_result,
            ag_models.FeedbackCategory.past_limit_submission)


class UltimateSubmissionFeedbackTestCase(_FeedbackTestsBase):
    def setUp(self):
        super().setUp()

        self.student_group1_best_submission = obj_build.make_finished_submission(
            group=self.student_group1)
        self.student1_best_res = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_group1_best_submission)
        self.student_group1_best_submission = update_denormalized_ag_test_results(
            self.student_group1_best_submission.pk)

        self.student_group1_most_recent_submission = obj_build.make_finished_submission(
            group=self.student_group1)
        self.student1_most_recent_res = obj_build.make_incorrect_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_group1_most_recent_submission)
        self.student_group1_most_recent_submission = update_denormalized_ag_test_results(
            self.student_group1_most_recent_submission.pk)

        self.project.validate_and_update(hide_ultimate_submission_fdbk=False, closing_time=None)

    def test_student_get_own_ultimate_submission_ultimate_fdbk(self):
        now = timezone.now()

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.most_recent)

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

        # Different combinations of the deadline being past and having an extension or not.
        past_deadline = now - timezone.timedelta(2)
        past_extension = now - timezone.timedelta(2)
        for closing_time, extension in [(past_deadline, None),
                                        (past_deadline, past_extension)]:
            self.project.validate_and_update(closing_time=closing_time)
            self.student_group1.validate_and_update(extended_due_date=extension)
            self.do_get_fdbk_test(self.client, self.student_group1_best_submission,
                                  ag_models.FeedbackCategory.ultimate_submission)
            self.do_get_output_and_diff_test(self.client, self.student_group1_best_submission,
                                             self.student1_best_res,
                                             ag_models.FeedbackCategory.ultimate_submission)

        # Late day finished
        self.project.validate_and_update(closing_time=past_deadline)
        self.student_group1.validate_and_update(extended_due_date=None)
        self.student_group1.late_days_used = {self.student1.username: 1}
        self.student_group1.save()

        self.do_get_fdbk_test(self.client, self.student_group1_best_submission,
                              ag_models.FeedbackCategory.ultimate_submission)
        self.do_get_output_and_diff_test(self.client, self.student_group1_best_submission,
                                         self.student1_best_res,
                                         ag_models.FeedbackCategory.ultimate_submission)

        # Extension and late day finished
        self.project.validate_and_update(closing_time=past_deadline)
        self.student_group1.validate_and_update(
            extended_due_date=past_deadline + datetime.timedelta(hours=12))
        self.student_group1.late_days_used = {self.student1.username: 1}
        self.student_group1.save()

        self.do_get_fdbk_test(self.client, self.student_group1_best_submission,
                              ag_models.FeedbackCategory.ultimate_submission)
        self.do_get_output_and_diff_test(self.client, self.student_group1_best_submission,
                                         self.student1_best_res,
                                         ag_models.FeedbackCategory.ultimate_submission)

    def test_student_get_other_student_ultimate_submission_ultimate_fdbk_permission_denied(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)

        student2 = obj_build.make_student_user(self.course)
        self.client.force_authenticate(student2)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.ultimate_submission)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.ultimate_submission)

    def test_student_get_own_ultimate_submission_ultimate_fdbk_hidden_permission_denied(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
        self.assertIsNone(self.project.closing_time)

        self.project.validate_and_update(hide_ultimate_submission_fdbk=True)
        self.client.force_authenticate(self.student1)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.ultimate_submission)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.ultimate_submission)

    def test_student_get_ultimate_fdbk_but_deadline_not_past_permission_denied(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
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
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
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

    def test_student_get_ultimate_fdbk_but_has_unfinished_late_day_permission_denied(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
        self.project.validate_and_update(
            closing_time=timezone.now() - timezone.timedelta(minutes=2))
        self.student_group1.late_days_used = {self.student1.username: 1}
        self.student_group1.save()

        self.client.force_authenticate(self.student1)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.ultimate_submission)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.ultimate_submission)

    def test_student_ultimate_submission_get_max_or_staff_viewer_fdbk_permission_denied(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)

        self.client.force_authenticate(self.student1)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.max)
        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.max)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.staff_viewer)
        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.staff_viewer)

    def test_staff_get_student_ultimate_submission_ultimate_fdbk(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)

        staff = obj_build.make_staff_user(self.course)
        self.client.force_authenticate(staff)

        self.do_get_fdbk_test(self.client, self.student_group1_most_recent_submission,
                              ag_models.FeedbackCategory.ultimate_submission)
        self.do_get_output_and_diff_test(self.client, self.student_group1_most_recent_submission,
                                         self.student1_most_recent_res,
                                         ag_models.FeedbackCategory.ultimate_submission)

    def test_staff_get_student_ultimate_submission_max_fdbk_permission_denied(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)

        staff = obj_build.make_staff_user(self.course)
        self.client.force_authenticate(staff)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.max)

        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.max)


class StaffOwnSubmissionFeedbackTestCase(_FeedbackTestsBase):
    def test_staff_get_own_submission_any_fdbk(self):
        self.project.validate_and_update(
            visible_to_students=False,
            hide_ultimate_submission_fdbk=True)

        staff_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.staff)
        staff = staff_group.members.first()

        staff_submission = obj_build.make_finished_submission(group=staff_group)
        result = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=staff_submission)
        staff_submission = update_denormalized_ag_test_results(staff_submission.pk)

        self.client.force_authenticate(staff)

        self.do_get_fdbk_test(self.client, staff_submission, ag_models.FeedbackCategory.normal)
        self.do_get_output_and_diff_test(self.client, staff_submission, result,
                                         ag_models.FeedbackCategory.normal)

        self.do_get_fdbk_test(self.client, staff_submission,
                              ag_models.FeedbackCategory.past_limit_submission)
        self.do_get_output_and_diff_test(self.client, staff_submission, result,
                                         ag_models.FeedbackCategory.past_limit_submission)

        self.do_get_fdbk_test(self.client, staff_submission,
                              ag_models.FeedbackCategory.staff_viewer)
        self.do_get_output_and_diff_test(self.client, staff_submission, result,
                                         ag_models.FeedbackCategory.staff_viewer)

        self.do_get_fdbk_test(self.client, staff_submission,
                              ag_models.FeedbackCategory.ultimate_submission)
        self.do_get_output_and_diff_test(self.client, staff_submission, result,
                                         ag_models.FeedbackCategory.ultimate_submission)

        self.do_get_fdbk_test(self.client, staff_submission, ag_models.FeedbackCategory.max)
        self.do_get_output_and_diff_test(self.client, staff_submission, result,
                                         ag_models.FeedbackCategory.max)


class StaffStudentLookupFeedbackTestCase(_FeedbackTestsBase):
    def setUp(self):
        super().setUp()

        self.student_group_normal_submission = obj_build.make_finished_submission(
            group=self.student_group1)
        self.normal_submission_result = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_group_normal_submission)
        self.student_group_normal_submission = update_denormalized_ag_test_results(
            self.student_group_normal_submission.pk)

        staff = obj_build.make_staff_user(self.course)
        self.client.force_authenticate(staff)

    def test_staff_get_student_submission_student_lookup_fdbk(self):
        self.do_get_fdbk_test(self.client, self.student_group_normal_submission,
                              ag_models.FeedbackCategory.staff_viewer)
        self.do_get_output_and_diff_test(self.client, self.student_group_normal_submission,
                                         self.normal_submission_result,
                                         ag_models.FeedbackCategory.staff_viewer)

    def test_staff_get_student_submission_non_staff_viewer_fdbk_permission_denied(self):
        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_normal_submission,
            ag_models.FeedbackCategory.normal)
        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result, ag_models.FeedbackCategory.normal)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_normal_submission,
            ag_models.FeedbackCategory.past_limit_submission)
        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result, ag_models.FeedbackCategory.past_limit_submission)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_normal_submission,
            ag_models.FeedbackCategory.ultimate_submission)
        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result, ag_models.FeedbackCategory.ultimate_submission)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group_normal_submission,
            ag_models.FeedbackCategory.max)
        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group_normal_submission,
            self.normal_submission_result, ag_models.FeedbackCategory.max)


class StaffStudentLookupUltimateSubmissionFeedbackTestCase(_FeedbackTestsBase):
    def setUp(self):
        super().setUp()

        staff = obj_build.make_staff_user(self.course)
        self.client.force_authenticate(staff)

        self.student_group1_best_submission = obj_build.make_finished_submission(
            group=self.student_group1)
        self.student1_best_res = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_group1_best_submission)
        self.student_group1_best_submission = update_denormalized_ag_test_results(
            self.student_group1_best_submission.pk)

        self.student_group1_most_recent_submission = obj_build.make_finished_submission(
            group=self.student_group1)
        self.student1_most_recent_res = obj_build.make_incorrect_ag_test_command_result(
            self.ag_test_cmd, submission=self.student_group1_most_recent_submission)
        self.student_group1_most_recent_submission = update_denormalized_ag_test_results(
            self.student_group1_most_recent_submission.pk)

        self.project.validate_and_update(hide_ultimate_submission_fdbk=False, closing_time=None)

    def test_staff_get_student_ultimate_submission_fdbk(self):
        for closing_time in None, timezone.now() - timezone.timedelta(minutes=5):
            self.project.validate_and_update(
                closing_time=closing_time,
                ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.most_recent)

            self.do_get_fdbk_test(self.client, self.student_group1_most_recent_submission,
                                  ag_models.FeedbackCategory.ultimate_submission)
            self.do_get_output_and_diff_test(
                self.client, self.student_group1_most_recent_submission,
                self.student1_most_recent_res, ag_models.FeedbackCategory.ultimate_submission)

            self.project.validate_and_update(
                ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best)

            self.do_get_fdbk_test(self.client, self.student_group1_best_submission,
                                  ag_models.FeedbackCategory.ultimate_submission)
            self.do_get_output_and_diff_test(
                self.client, self.student_group1_best_submission,
                self.student1_best_res, ag_models.FeedbackCategory.ultimate_submission)

    def test_staff_get_student_ultimate_submision_fdbk_pending_late_day(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)

        self.project.validate_and_update(
            closing_time=timezone.now() - timezone.timedelta(minutes=2))
        self.assertIsNone(self.student_group1.extended_due_date)

        self.student_group1.late_days_used = {self.student1.username: 1}
        self.student_group1.save()

        self.do_get_fdbk_test(self.client, self.student_group1_most_recent_submission,
                              ag_models.FeedbackCategory.ultimate_submission)
        self.do_get_output_and_diff_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.ultimate_submission)

    def test_staff_get_student_ultimate_submission_ultimate_fdbk_hidden_permission_denied(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)

        self.project.validate_and_update(hide_ultimate_submission_fdbk=True)

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.ultimate_submission)
        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.ultimate_submission)

    def test_staff_get_student_ultimate_submission_fdbk_before_deadline_permission_denied(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)

        self.project.validate_and_update(
            closing_time=timezone.now() + timezone.timedelta(minutes=5))

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.ultimate_submission)
        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.ultimate_submission)

    def test_staff_get_student_ultimate_submission_fdbk_before_extension_permission_denied(self):
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)

        self.project.validate_and_update(
            closing_time=timezone.now() - timezone.timedelta(minutes=2))
        self.student_group1.validate_and_update(
            extended_due_date=timezone.now() + timezone.timedelta(minutes=2))

        self.do_get_fdbk_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            ag_models.FeedbackCategory.ultimate_submission)
        self.do_get_output_and_diff_permission_denied_test(
            self.client, self.student_group1_most_recent_submission,
            self.student1_most_recent_res, ag_models.FeedbackCategory.ultimate_submission)


class AdminLookupStudentSubmissionTestCase(_FeedbackTestsBase):
    def test_admin_get_student_submission_any_fdbk(self):
        self.project.validate_and_update(
            visible_to_students=False,
            hide_ultimate_submission_fdbk=True)

        student_group = obj_build.make_group(project=self.project)

        student_submission = obj_build.make_finished_submission(group=student_group)
        result = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd, submission=student_submission)
        student_submission = update_denormalized_ag_test_results(student_submission.pk)

        admin = obj_build.make_admin_user(self.course)
        self.client.force_authenticate(admin)

        self.do_get_fdbk_test(self.client, student_submission, ag_models.FeedbackCategory.normal)
        self.do_get_output_and_diff_test(self.client, student_submission, result,
                                         ag_models.FeedbackCategory.normal)

        self.do_get_fdbk_test(self.client, student_submission,
                              ag_models.FeedbackCategory.past_limit_submission)
        self.do_get_output_and_diff_test(self.client, student_submission, result,
                                         ag_models.FeedbackCategory.past_limit_submission)

        self.do_get_fdbk_test(self.client, student_submission,
                              ag_models.FeedbackCategory.staff_viewer)
        self.do_get_output_and_diff_test(self.client, student_submission, result,
                                         ag_models.FeedbackCategory.staff_viewer)

        self.do_get_fdbk_test(self.client, student_submission,
                              ag_models.FeedbackCategory.ultimate_submission)
        self.do_get_output_and_diff_test(self.client, student_submission, result,
                                         ag_models.FeedbackCategory.ultimate_submission)

        self.do_get_fdbk_test(self.client, student_submission, ag_models.FeedbackCategory.max)
        self.do_get_output_and_diff_test(self.client, student_submission, result,
                                         ag_models.FeedbackCategory.max)


class MiscSubmissionFeedbackTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.client = APIClient()

        project = obj_build.make_project()
        self.course = project.course

        staff_group = obj_build.make_group(
            project=project, members_role=obj_build.UserRole.staff)
        self.staff = staff_group.members.first()
        self.staff_normal_submission = obj_build.make_finished_submission(group=staff_group)

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
            self._make_submission_result_url(most_recent_submission,
                                             ag_models.FeedbackCategory.ultimate_submission))
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        client.force_authenticate(doesnt_count_for_user)
        # Shouldn't be able to get ultimate submission fdbk on
        # the most recent submission (that doesn't count for this user)
        response = client.get(
            self._make_submission_result_url(most_recent_submission,
                                             ag_models.FeedbackCategory.ultimate_submission))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = client.get(
            self._make_submission_result_url(first_submission,
                                             ag_models.FeedbackCategory.ultimate_submission))
        self.assertEqual(status.HTTP_200_OK, response.status_code)

    def _make_submission_result_url(
            self,
            submission: ag_models.Submission,
            fdbk_category: ag_models.FeedbackCategory=ag_models.FeedbackCategory.normal):
        url = reverse('submission-results', kwargs={'pk': submission.pk})
        url += '?feedback_category={}'.format(fdbk_category.value)

        return url
