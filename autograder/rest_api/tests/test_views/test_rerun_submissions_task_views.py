from typing import Tuple
from unittest import mock

from django.test import tag
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
from autograder.grading_tasks.tasks.grade_submission import grade_submission
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.caching import get_cached_submission_feedback, submission_fdbk_cache_key
from autograder.core.submission_feedback import AGTestPreLoader, SubmissionResultFeedback
from autograder.core.tests.test_submission_feedback.fdbk_getter_shortcuts import \
    get_submission_fdbk
from autograder.grading_tasks import tasks
from autograder.grading_tasks.tasks.rerun_submission import SubmissionRerunner, rerun_submission
from autograder.rest_api.tests.test_views.ag_view_test_base import AGViewTestBase
from autograder.utils.testing import TransactionUnitTestBase


class _MockException(Exception):
    pass


class ListRerunSubmissionsTasksTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()

        self.project = obj_build.make_project()
        [self.admin] = obj_build.make_admin_users(self.project.course, 1)

        self.task1 = ag_models.RerunSubmissionsTask.objects.validate_and_create(
            creator=self.admin,
            project=self.project,
        )  # type: ag_models.RerunSubmissionsTask

        self.task2 = ag_models.RerunSubmissionsTask.objects.validate_and_create(
            creator=self.admin,
            project=self.project,
        )  # type: ag_models.RerunSubmissionsTask

        self.client = APIClient()
        self.url = reverse('rerun_submissions_tasks', kwargs={'project_pk': self.project.pk})

    def test_admin_valid_list_rerun_tasks(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertCountEqual([self.task1.to_dict(), self.task2.to_dict()], response.data)

    def test_non_admin_list_rerun_tasks_permission_denied(self):
        student = obj_build.make_student_user(self.project.course)
        self.client.force_authenticate(student)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


@tag('slow', 'sandbox')
@mock.patch('autograder.utils.retry.sleep')
class CreateAndGetRerunSubmissionsTasksTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()

        self.project = obj_build.make_project()
        self.submission1 = obj_build.make_submission(
            group=obj_build.make_group(project=self.project))
        self.submission2 = obj_build.make_submission(
            group=obj_build.make_group(project=self.project))
        [self.admin] = obj_build.make_admin_users(self.project.course, 1)

        self.ag_test_suite1 = obj_build.make_ag_test_suite(self.project)

        self.ag_test_case1 = obj_build.make_ag_test_case(self.ag_test_suite1)
        self.ag_test_cmd1 = ag_models.AGTestCommand.objects.validate_and_create(
            ag_test_case=self.ag_test_case1,
            name='cmd1',
            cmd='false',  # Always exits nonzero
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            points_for_correct_return_code=1
        )  # type: ag_models.AGTestCommand
        self.ag_test_case2 = obj_build.make_ag_test_case(self.ag_test_suite1)
        self.ag_test_cmd2 = ag_models.AGTestCommand.objects.validate_and_create(
            ag_test_case=self.ag_test_case2,
            name='cmd2',
            cmd='false',
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            points_for_correct_return_code=2
        )  # type: ag_models.AGTestCommand

        self.ag_test_case1_points_possible = 1
        self.ag_test_case2_points_possible = 2
        self.ag_test_suite1_points_possible = (
            self.ag_test_case1_points_possible + self.ag_test_case2_points_possible)

        self.ag_test_suite2 = obj_build.make_ag_test_suite(self.project)
        self.ag_test_case3 = obj_build.make_ag_test_case(self.ag_test_suite2)
        self.ag_test_cmd3 = ag_models.AGTestCommand.objects.validate_and_create(
            ag_test_case=self.ag_test_case3,
            name='cmd3',
            cmd='false',
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            points_for_correct_return_code=4
        )  # type: ag_models.AGTestCommand

        self.ag_test_case3_points_possible = 4
        self.ag_test_suite2_points_possible = self.ag_test_case3_points_possible

        self.mutation_suite1 = obj_build.make_mutation_test_suite(
            self.project,
            buggy_impl_names=['bug1', 'bug2'],
            get_student_test_names_command={
                'cmd': 'echo test1 test2'
            },
            student_test_validity_check_command={
                'cmd': 'bash -c "echo ${student_test_name}; true"'
            },
            grade_buggy_impl_command={
                # Won't expose any bugs
                'cmd': 'bash -c "echo ${student_test_name} ${buggy_impl_name}; true"'
            },
            points_per_exposed_bug=1)

        self.mutation_suite1_points_possible = 2

        self.mutation_suite2 = obj_build.make_mutation_test_suite(
            self.project,
            buggy_impl_names=['bug1', 'bug2'],
            get_student_test_names_command={
                'cmd': 'echo test1 test2'
            },
            student_test_validity_check_command={
                'cmd': 'bash -c "echo ${student_test_name}; true"'
            },
            grade_buggy_impl_command={
                # Won't expose any bugs
                'cmd': 'bash -c "echo ${student_test_name} ${buggy_impl_name}; true"'
            },
            points_per_exposed_bug=2)

        self.mutation_suite2_points_possible = 4

        self.mutation_suite_total_points_possible = (
            self.mutation_suite1_points_possible + self.mutation_suite2_points_possible)

        self.total_points_possible = (self.ag_test_suite1_points_possible
                                      + self.ag_test_suite2_points_possible
                                      + self.mutation_suite_total_points_possible)

        tasks.grade_submission_task(self.submission1.pk)
        tasks.grade_submission_task(self.submission2.pk)
        self.submission1.refresh_from_db()
        self.submission2.refresh_from_db()

        self.ag_test_cmd1.validate_and_update(cmd='true')  # Always exits zero
        self.ag_test_cmd2.validate_and_update(cmd='true')
        self.ag_test_cmd3.validate_and_update(cmd='true')

        self.mutation_suite1.validate_and_update(
            grade_buggy_impl_command={
                # Will expose all the bugs
                'cmd': 'bash -c "echo ${student_test_name} ${buggy_impl_name}; false"'
            })

        self.mutation_suite2.validate_and_update(
            grade_buggy_impl_command={
                'cmd': 'bash -c "echo ${student_test_name} ${buggy_impl_name}; false"'
            })

        fdbk1 = get_submission_fdbk(self.submission1, ag_models.FeedbackCategory.max)
        self.assertEqual(0, fdbk1.total_points)
        self.assertEqual(self.total_points_possible, fdbk1.total_points_possible)

        fdbk2 = get_submission_fdbk(self.submission2, ag_models.FeedbackCategory.max)
        self.assertEqual(0, fdbk2.total_points)
        self.assertEqual(self.total_points_possible, fdbk2.total_points_possible)

        self.client = APIClient()
        self.url = reverse('rerun_submissions_tasks', kwargs={'project_pk': self.project.pk})

        # Create another project with some test cases to make sure that the rerun
        # doesn't accidentally pick it up.
        self.other_project = obj_build.make_project()
        self.other_submission = obj_build.make_submission(
            group=obj_build.make_group(project=self.other_project))

        self.other_ag_test_suite = obj_build.make_ag_test_suite(self.other_project)
        self.other_ag_test_case = obj_build.make_ag_test_case(self.other_ag_test_suite)
        self.other_ag_test_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            ag_test_case=self.other_ag_test_case,
            name='other_cmd',
            cmd='false',  # Always exits nonzero
            expected_return_code=ag_models.ExpectedReturnCode.zero,
            points_for_correct_return_code=1
        )  # type: ag_models.AGTestCommand

        tasks.grade_submission_task(self.other_submission.pk)
        self.other_submission.refresh_from_db()

        other_fdbk = get_submission_fdbk(self.other_submission, ag_models.FeedbackCategory.max)
        self.assertEqual(0, other_fdbk.total_points)
        self.assertEqual(1, other_fdbk.total_points_possible)
        self.other_ag_test_cmd.validate_and_update(cmd='true')

    def test_admin_rerun_everything(self, *args):
        self.do_rerun_submissions_test_case(
            {}, (self.submission1, self.total_points_possible),
            (self.submission2, self.total_points_possible))

    def test_rerun_specific_submissions(self, *args):
        request_body = {
            'rerun_all_submissions': False,
            'submission_pks': [self.submission1.pk]
        }
        self.do_rerun_submissions_test_case(
            request_body, (self.submission1, self.total_points_possible), (self.submission2, 0))

    def test_non_finished_submissions_not_rerun_with_rerun_all_submissions_true(self, _) -> None:
        # These are the statuses we care most about not being rerun as part
        # of an "all submissions" rerun.
        self.submission1.status = ag_models.Submission.GradingStatus.error
        self.submission1.save()
        self.submission2.status = ag_models.Submission.GradingStatus.removed_from_queue
        self.submission2.save()

        self.do_rerun_submissions_test_case({
            'rerun_all_submissions': True,
        })

        self.submission1.refresh_from_db()
        self.assertEqual(
            ag_models.Submission.GradingStatus.error,
            self.submission1.status)
        self.submission2.refresh_from_db()
        self.assertEqual(
            ag_models.Submission.GradingStatus.removed_from_queue,
            self.submission2.status)

    def test_submissions_marked_as_finished_when_all_tests_rerun(self, *args) -> None:
        self.submission1.status = ag_models.Submission.GradingStatus.error
        self.submission1.save()
        self.submission2.status = ag_models.Submission.GradingStatus.waiting_for_deferred
        self.submission2.save()

        self.do_rerun_submissions_test_case({
            'rerun_all_submissions': False,
            'submission_pks': [self.submission1.pk]
        })

        self.submission1.refresh_from_db()
        self.assertEqual(
            ag_models.Submission.GradingStatus.finished_grading,
            self.submission1.status)
        self.submission2.refresh_from_db()
        self.assertEqual(
            ag_models.Submission.GradingStatus.waiting_for_deferred,
            self.submission2.status)

        self.submission1.status = ag_models.Submission.GradingStatus.error
        self.submission1.save()

        self.do_rerun_submissions_test_case({
            'rerun_all_submissions': False,
            'submission_pks': [self.submission1.pk, self.submission2.pk]
        })

        self.submission1.refresh_from_db()
        self.assertEqual(
            ag_models.Submission.GradingStatus.finished_grading,
            self.submission1.status)
        self.submission2.refresh_from_db()
        self.assertEqual(
            ag_models.Submission.GradingStatus.finished_grading,
            self.submission2.status)

    def test_submission_status_unchanged_when_not_all_tests_rerun(self, *args) -> None:
        self.submission1.status = ag_models.Submission.GradingStatus.error
        self.submission1.save()

        self.do_rerun_submissions_test_case({
            'rerun_all_submissions': False,
            'submission_pks': [self.submission1.pk],
            'rerun_all_ag_test_suites': False,
            'ag_test_suite_data': {str(self.ag_test_suite1.pk): []},
        })

        self.submission1.refresh_from_db()
        self.assertEqual(
            ag_models.Submission.GradingStatus.error,
            self.submission1.status)

        self.do_rerun_submissions_test_case({
            'rerun_all_submissions': False,
            'submission_pks': [self.submission1.pk],
            'rerun_all_ag_test_suites': True,
            'rerun_all_mutation_test_suites': False,
            'mutation_suite_pks': [self.mutation_suite1.pk]
        })

        self.submission1.refresh_from_db()
        self.assertEqual(
            ag_models.Submission.GradingStatus.error,
            self.submission1.status)

    def test_admin_rerun_specific_ag_suites(self, *args):
        request_body = {
            'rerun_all_ag_test_suites': False,
            'ag_test_suite_data': {str(self.ag_test_suite1.pk): []},
            'rerun_all_mutation_test_suites': False
        }
        self.do_rerun_submissions_test_case(
            request_body, (self.submission1, self.ag_test_suite1_points_possible),
            (self.submission2, self.ag_test_suite1_points_possible))

    def test_admin_rerun_specific_ag_tests(self, *args):
        request_body = {
            'rerun_all_ag_test_suites': False,
            'ag_test_suite_data': {str(self.ag_test_suite1.pk): [self.ag_test_case1.pk]},
            'rerun_all_mutation_test_suites': False
        }
        self.do_rerun_submissions_test_case(
            request_body, (self.submission1, self.ag_test_case1_points_possible),
            (self.submission2, self.ag_test_case1_points_possible))

    def test_admin_rerun_specific_mutation_suites(self, *args):
        request_body = {
            'rerun_all_ag_test_suites': False,
            'rerun_all_mutation_test_suites': False,
            'mutation_suite_pks': [self.mutation_suite1.pk]
        }
        self.do_rerun_submissions_test_case(
            request_body, (self.submission1, self.mutation_suite1_points_possible),
            (self.submission2, self.mutation_suite1_points_possible))

    def test_admin_rerun_fatal_error_in_ag_test_suite(self, *args):
        target = 'autograder.grading_tasks.tasks.rerun_submission.grade_ag_test_suite_impl'
        with mock.patch(target, new=mock.Mock(side_effect=_MockException)):
            self.client.force_authenticate(self.admin)
            response = self.client.post(self.url, {})

            rerun_task = ag_models.RerunSubmissionsTask.objects.get(pk=response.data['pk'])
            print(rerun_task.error_msg)
            self.assertNotEqual('', rerun_task.error_msg)
            self.assertIn('Error rerunning submission', rerun_task.error_msg)

    def test_admin_rerun_fatal_error_in_deferred_ag_test_suite(self, *args):
        self.ag_test_suite1.validate_and_update(deferred=True)
        self.ag_test_suite2.delete()
        self.mutation_suite1.delete()
        self.mutation_suite2.delete()

        target = 'autograder.grading_tasks.tasks.rerun_submission.grade_ag_test_suite_impl'
        with mock.patch(target, new=mock.Mock(side_effect=_MockException)):
            self.client.force_authenticate(self.admin)

            response = self.client.post(self.url, {})
            rerun_task = ag_models.RerunSubmissionsTask.objects.get(pk=response.data['pk'])
            print(rerun_task.error_msg)
            self.assertNotEqual('', rerun_task.error_msg)
            self.assertIn('Error rerunning submission', rerun_task.error_msg)

    def test_admin_rerun_fatal_error_in_mutation_test_suite(self, *args):
        target = 'autograder.grading_tasks.tasks.rerun_submission.grade_mutation_test_suite_impl'
        with mock.patch(target, new=mock.Mock(side_effect=_MockException)):
            self.client.force_authenticate(self.admin)

            response = self.client.post(self.url, {})
            rerun_task = ag_models.RerunSubmissionsTask.objects.get(pk=response.data['pk'])
            print(rerun_task.error_msg)
            self.assertNotEqual('', rerun_task.error_msg)
            self.assertIn('Error rerunning submission', rerun_task.error_msg)

    def test_admin_rerun_fatal_error_in_deferred_mutation_test_suite(self, *args):
        self.mutation_suite1.validate_and_update(deferred=True)
        self.mutation_suite2.delete()
        self.ag_test_suite1.delete()
        self.ag_test_suite2.delete()

        target = 'autograder.grading_tasks.tasks.rerun_submission.grade_mutation_test_suite_impl'
        with mock.patch(target, new=mock.Mock(side_effect=_MockException)):
            self.client.force_authenticate(self.admin)

            response = self.client.post(self.url, {})
            rerun_task = ag_models.RerunSubmissionsTask.objects.get(pk=response.data['pk'])
            print(rerun_task.error_msg)
            self.assertNotEqual('', rerun_task.error_msg)
            self.assertIn('Error rerunning submission', rerun_task.error_msg)

    def test_one_item_celery_chord(self, *args):
        request_body = {
            'rerun_all_submissions': False,
            'submission_pks': [self.submission1.pk],
            'rerun_all_ag_test_suites': False,
            'ag_test_suite_data': {str(self.ag_test_suite2.pk): [self.ag_test_case3.pk]},
            'rerun_all_mutation_test_suites': False,
        }
        self.do_rerun_submissions_test_case(
            request_body, (self.submission1, self.ag_test_case3_points_possible),
            (self.submission2, 0))

    def test_nothing_to_rerun(self, *args):
        request_body = {
            'rerun_all_submissions': False,
            'rerun_all_ag_test_suites': False,
            'rerun_all_mutation_test_suites': False,
        }
        self.do_rerun_submissions_test_case(
            request_body, (self.submission1, 0), (self.submission2, 0))

    def test_rerun_clears_cache(self, *args):
        fdbk = SubmissionResultFeedback(
            self.submission1, ag_models.FeedbackCategory.normal, AGTestPreLoader(self.project))
        get_cached_submission_feedback(self.submission1, fdbk)

        key = submission_fdbk_cache_key(
            project_pk=self.project.pk, submission_pk=self.submission1.pk)

        with self.assert_cache_key_invalidated(key):
            self.do_rerun_submissions_test_case({}, (self.submission1, self.total_points_possible))

    def do_rerun_submissions_test_case(
            self, request_body: dict,
            *expected_submission_points: Tuple[ag_models.Submission, int]):
        self.client.force_authenticate(self.admin)

        response = self.client.post(self.url, request_body)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        task = ag_models.RerunSubmissionsTask.objects.get(
            pk=response.data['pk']
        )  # type: ag_models.RerunSubmissionsTask

        self.assertEqual(100, task.progress)
        expected_response = task.to_dict()

        if task.num_completed_subtasks != 0:
            # Unless there were no subtasks,
            # the response should return progress of 0.
            expected_response['progress'] = 0

        self.assertEqual(expected_response, response.data)

        for submission, expected_total_points in expected_submission_points:
            original_grading_start_time = submission.grading_start_time
            original_non_deferred_grading_end_time = submission.non_deferred_grading_end_time

            submission.refresh_from_db()
            fdbk = get_submission_fdbk(submission, ag_models.FeedbackCategory.max)
            self.assertEqual(expected_total_points, fdbk.total_points)
            self.assertEqual(self.total_points_possible, fdbk.total_points_possible)

            self.assertEqual(original_grading_start_time, submission.grading_start_time)
            self.assertEqual(
                original_non_deferred_grading_end_time, submission.non_deferred_grading_end_time)

        # Make sure this submission is never rerun.
        self.other_submission.refresh_from_db()
        other_fdbk = get_submission_fdbk(self.other_submission, ag_models.FeedbackCategory.max)
        self.assertEqual(0, other_fdbk.total_points)
        self.assertEqual(1, other_fdbk.total_points_possible)


class CreateRerunSubmissionsTasksPermissionDeniedTestCase(AGViewTestBase):
    def test_non_admin_create_permission_denied(self):
        project = obj_build.make_project()
        [staff] = obj_build.make_staff_users(project.course, 1)
        self.do_permission_denied_create_test(
            ag_models.RerunSubmissionsTask.objects,
            APIClient(),
            staff,
            reverse('rerun_submissions_tasks', kwargs={'project_pk': project.pk}),
            {})


class RerunSubmissionsTaskDetailViewSetTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()

        self.project = obj_build.make_project()
        [self.admin] = obj_build.make_admin_users(self.project.course, 1)
        self.submission = obj_build.make_submission(group=obj_build.make_group())

        # Create a rerun task using the api so that it gets run and we have a
        # real celery task ID to look up.
        create_client = APIClient()
        create_client.force_authenticate(self.admin)
        create_url = reverse('rerun_submissions_tasks', kwargs={'project_pk': self.project.pk})

        create_response = create_client.post(create_url, {})
        self.rerun_task = ag_models.RerunSubmissionsTask.objects.get(pk=create_response.data['pk'])

        self.client = APIClient()
        self.url = reverse('rerun-submissions-task-detail', kwargs={'pk': self.rerun_task.pk})

    def test_admin_valid_get_rerun_task(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self.rerun_task.to_dict(), response.data)

    def test_non_admin_get_rerun_task_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.project.course, 1)
        self.client.force_authenticate(staff)
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_admin_cancel_task(self) -> None:
        self.client.force_authenticate(self.admin)
        url = reverse('cancel-rerun-submissions-task', kwargs={'pk': self.rerun_task.pk})
        response = self.client.post(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        self.rerun_task.refresh_from_db()
        self.assertTrue(self.rerun_task.is_cancelled)
        self.assertEqual(self.rerun_task.to_dict(), response.data)

    def test_non_admin_cancel_task_permission_denied(self) -> None:
        staff = obj_build.make_staff_user(self.project.course)
        self.client.force_authenticate(staff)

        url = reverse('cancel-rerun-submissions-task', kwargs={'pk': self.rerun_task.pk})
        response = self.client.post(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.rerun_task.refresh_from_db()
        self.assertFalse(self.rerun_task.is_cancelled)


@mock.patch('autograder.utils.retry.sleep')
class NoRetryOnObjectNotFoundTestCase(TransactionUnitTestBase):
    def setUp(self):
        super().setUp()

        self.submission = obj_build.make_finished_submission()
        self.group = self.submission.group
        self.project = self.group.project
        self.rerun_task = ag_models.RerunSubmissionsTask.objects.validate_and_create(
            project=self.project,
            creator=obj_build.make_user(),
        )

    def test_ag_test_suite_not_found_no_retry(self, sleep_mock) -> None:
        ag_test_suite = obj_build.make_ag_test_suite(self.project)

        ag_models.AGTestSuite.objects.get(pk=ag_test_suite.pk).delete()

        SubmissionRerunner(self.submission.pk, self.rerun_task.pk).rerun_submission()
        sleep_mock.assert_not_called()

    @mock.patch(
        'autograder.rest_api.views.rerun_submissions_task_views.tasks.grade_ag_test_suite_impl'
    )
    def test_ag_test_case_not_found_no_retry(self, sleep_mock, grade_suite_mock) -> None:
        ag_test_suite = obj_build.make_ag_test_suite(self.project)
        ag_test_case = obj_build.make_ag_test_case(ag_test_suite)
        ag_models.AGTestCase.objects.get(pk=ag_test_case.pk).delete()
        SubmissionRerunner(self.submission.pk, self.rerun_task.pk).rerun_submission()

        grade_suite_mock.assert_not_called()
        sleep_mock.assert_not_called()

    @tag('sandbox')
    def test_ag_test_command_not_found_no_retry(self, sleep_mock) -> None:
        ag_test_suite = obj_build.make_ag_test_suite(self.project)
        ag_test_case = obj_build.make_ag_test_case(ag_test_suite)
        ag_test_command = obj_build.make_full_ag_test_command(
            ag_test_case,
            set_arbitrary_points=False,
            set_arbitrary_expected_vals=False
        )

        suite_result = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=ag_test_case.ag_test_suite,
            submission=self.submission
        )
        test_result = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_case=ag_test_case,
            ag_test_suite_result=suite_result
        )

        ag_models.AGTestCommand.objects.get(pk=ag_test_command.pk).delete()
        SubmissionRerunner(self.submission.pk, self.rerun_task.pk).rerun_submission()

        sleep_mock.assert_not_called()

    def test_mutation_test_suite_not_found_no_retry(self, sleep_mock) -> None:
        mutation_suite = obj_build.make_mutation_test_suite(self.project)

        ag_models.MutationTestSuite.objects.get(pk=mutation_suite.pk).delete()

        SubmissionRerunner(self.submission.pk, self.rerun_task.pk).rerun_submission()
        sleep_mock.assert_not_called()


class RerunCancelledTestCase(TransactionUnitTestBase):
    def setUp(self):
        super().setUp()

        self.submission = obj_build.make_finished_submission()
        self.group = self.submission.group
        self.project = self.group.project

    def test_ag_test_suite_skipped(self, *args) -> None:
        ag_test_suite = obj_build.make_ag_test_suite(self.project)

        rerun_task = ag_models.RerunSubmissionsTask.objects.validate_and_create(
            project=self.project,
            creator=obj_build.make_user(),
            is_cancelled=True,
        )

        SubmissionRerunner(self.submission.pk, rerun_task.pk).rerun_submission()
        rerun_task.refresh_from_db()
        self.assertEqual(0, rerun_task.progress)

    def test_mutation_test_suite_not_found_no_retry(self, *args) -> None:
        mutation_suite = obj_build.make_mutation_test_suite(self.project)

        rerun_task = ag_models.RerunSubmissionsTask.objects.validate_and_create(
            project=self.project,
            creator=obj_build.make_user(),
            is_cancelled=True,
            total_num_subtasks=1,
        )

        SubmissionRerunner(self.submission.pk, rerun_task.pk).rerun_submission()
        rerun_task.refresh_from_db()
        self.assertEqual(0, rerun_task.progress)


@mock.patch('autograder.utils.retry.sleep')
class RejectSubmissionTestCase(TransactionUnitTestBase):
    def test_submission_reject_in_rerun_does_not_refund_bonus_submission(self, *args) -> None:
        submission = obj_build.make_finished_submission()
        suite = obj_build.make_ag_test_suite(
            submission.project,
            reject_submission_if_setup_fails=True,
            setup_suite_cmd='false'
        )
        test_case = obj_build.make_ag_test_case(suite)

        submission.group.bonus_submissions_used = 1
        submission.group.save()
        submission.is_bonus_submission = True
        submission.save()

        rerun_task = ag_models.RerunSubmissionsTask.objects.validate_and_create(
            project=submission.project,
            creator=obj_build.make_user(),
            total_num_subtasks=1,
        )

        rerun_submission(submission.pk, rerun_task.pk)

        submission.refresh_from_db()
        # Grading status should NOT change to "rejected" in rerun.
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading, submission.status)
        # Bonus submission should NOT be refunded.
        self.assertEqual(1, submission.group.bonus_submissions_used)

        self.assertEqual(
            0,
            ag_models.AGTestCaseResult.objects.filter(
                ag_test_suite_result__submission=submission
            ).count()
        )

    def test_reject_submission_on_rerun_not_recorded_as_error(self, sleep_mock) -> None:
        submission = obj_build.make_submission()
        suite = obj_build.make_ag_test_suite(
            submission.project,
            reject_submission_if_setup_fails=True,
            setup_suite_cmd='false'
        )
        test_case = obj_build.make_ag_test_case(suite)

        # Grade submission so it gets marked as rejected
        grade_submission(submission.pk)
        submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.rejected, submission.status)

        rerun_task = ag_models.RerunSubmissionsTask.objects.validate_and_create(
            project=submission.project,
            creator=obj_build.make_user(),
            total_num_subtasks=1,
        )

        rerun_submission(submission.pk, rerun_task.pk)

        submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.rejected, submission.status)
        rerun_task.refresh_from_db()
        self.assertEqual('', rerun_task.error_msg)
        self.assertEqual(100, rerun_task.progress)

        sleep_mock.assert_not_called()
