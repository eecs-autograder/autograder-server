from typing import Tuple
from unittest import mock

from django.test import tag
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.tests.test_submission_feedback.fdbk_getter_shortcuts import (
    get_submission_fdbk)
from autograder.grading_tasks import tasks
from autograder.utils.testing import UnitTestBase


class ListRerunSubmissionsTasksTestCase(UnitTestBase):
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
        [enrolled] = obj_build.make_student_users(self.project.course, 1)
        self.client.force_authenticate(enrolled)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


@tag('slow', 'sandbox')
@mock.patch('autograder.grading_tasks.tasks.utils.time.sleep')
class CreateAndGetRerunSubmissionsTasksTestCase(UnitTestBase):
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

        self.student_suite1 = obj_build.make_student_test_suite(
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

        self.student_suite1_points_possible = 2

        self.student_suite2 = obj_build.make_student_test_suite(
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

        self.student_suite2_points_possible = 4

        self.student_suite_total_points_possible = (
            self.student_suite1_points_possible + self.student_suite2_points_possible)

        self.total_points_possible = (self.ag_test_suite1_points_possible
                                      + self.ag_test_suite2_points_possible
                                      + self.student_suite_total_points_possible)

        tasks.grade_submission(self.submission1.pk)
        tasks.grade_submission(self.submission2.pk)
        self.submission1.refresh_from_db()
        self.submission2.refresh_from_db()

        self.ag_test_cmd1.validate_and_update(cmd='true')  # Always exits zero
        self.ag_test_cmd2.validate_and_update(cmd='true')
        self.ag_test_cmd3.validate_and_update(cmd='true')

        self.student_suite1.validate_and_update(
            grade_buggy_impl_command={
                # Will expose all the bugs
                'cmd': 'bash -c "echo ${student_test_name} ${buggy_impl_name}; false"'
            })

        self.student_suite2.validate_and_update(
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

        tasks.grade_submission(self.other_submission.pk)
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

    def test_admin_rerun_specific_ag_suites(self, *args):
        request_body = {
            'rerun_all_ag_test_suites': False,
            'ag_test_suite_data': {str(self.ag_test_suite1.pk): []},
            'rerun_all_student_test_suites': False
        }
        self.do_rerun_submissions_test_case(
            request_body, (self.submission1, self.ag_test_suite1_points_possible),
            (self.submission2, self.ag_test_suite1_points_possible))

    def test_admin_rerun_specific_ag_tests(self, *args):
        request_body = {
            'rerun_all_ag_test_suites': False,
            'ag_test_suite_data': {str(self.ag_test_suite1.pk): [self.ag_test_case1.pk]},
            'rerun_all_student_test_suites': False
        }
        self.do_rerun_submissions_test_case(
            request_body, (self.submission1, self.ag_test_case1_points_possible),
            (self.submission2, self.ag_test_case1_points_possible))

    def test_admin_rerun_specific_student_suites(self, *args):
        request_body = {
            'rerun_all_ag_test_suites': False,
            'rerun_all_student_test_suites': False,
            'student_suite_pks': [self.student_suite1.pk]
        }
        self.do_rerun_submissions_test_case(
            request_body, (self.submission1, self.student_suite1_points_possible),
            (self.submission2, self.student_suite1_points_possible))

    def test_admin_rerun_fatal_error_in_ag_test_suite(self, *args):
        class _MockException(Exception):
            pass

        target = ('autograder.rest_api.views.rerun_submissions_task_views.'
                  'tasks.grade_ag_test_suite_impl')
        with mock.patch(target, new=mock.Mock(side_effect=_MockException)):
            self.client.force_authenticate(self.admin)

            response = self.client.post(self.url, {})
            rerun_task = ag_models.RerunSubmissionsTask.objects.get(pk=response.data['pk'])
            print(rerun_task.error_msg)
            self.assertNotEqual('', rerun_task.error_msg)
            self.assertIn('Error rerunning ag test suite', rerun_task.error_msg)

    def test_admin_rerun_fatal_error_in_student_test_suite(self, *args):
        class _MockException(Exception):
            pass

        target = ('autograder.rest_api.views.rerun_submissions_task_views.'
                  'tasks.grade_student_test_suite_impl')
        with mock.patch(target, new=mock.Mock(side_effect=_MockException)):
            self.client.force_authenticate(self.admin)

            response = self.client.post(self.url, {})
            rerun_task = ag_models.RerunSubmissionsTask.objects.get(pk=response.data['pk'])
            print(rerun_task.error_msg)
            self.assertNotEqual('', rerun_task.error_msg)
            self.assertIn('Error rerunning student test suite', rerun_task.error_msg)

    def test_one_item_celery_chord(self, *args):
        request_body = {
            'rerun_all_submissions': False,
            'submission_pks': [self.submission1.pk],
            'rerun_all_ag_test_suites': False,
            'ag_test_suite_data': {str(self.ag_test_suite2.pk): [self.ag_test_case3.pk]},
            'rerun_all_student_test_suites': False,
        }
        self.do_rerun_submissions_test_case(
            request_body, (self.submission1, self.ag_test_case3_points_possible),
            (self.submission2, 0))

    def test_nothing_to_rerun(self, *args):
        request_body = {
            'rerun_all_submissions': False,
            'rerun_all_ag_test_suites': False,
            'rerun_all_student_test_suites': False,
        }
        self.do_rerun_submissions_test_case(
            request_body, (self.submission1, 0), (self.submission2, 0))

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
            # Unless there were no subtasks, there
            # should be a celery group result id, and
            # the response should return progress of 0.
            self.assertIsNotNone(task.celery_group_result_id)
            expected_response['progress'] = 0

        self.assertEqual(expected_response, response.data)

        for submission, expected_total_points in expected_submission_points:
            submission.refresh_from_db()
            fdbk = get_submission_fdbk(submission, ag_models.FeedbackCategory.max)
            self.assertEqual(expected_total_points, fdbk.total_points)
            self.assertEqual(self.total_points_possible, fdbk.total_points_possible)

        # Make sure this submission is never rerun.
        self.other_submission.refresh_from_db()
        other_fdbk = get_submission_fdbk(self.other_submission, ag_models.FeedbackCategory.max)
        self.assertEqual(0, other_fdbk.total_points)
        self.assertEqual(1, other_fdbk.total_points_possible)


class CreateRerunSubmissionsTasksPermissionDeniedTestCase(test_impls.CreateObjectTest,
                                                          UnitTestBase):
    def test_non_admin_create_permission_denied(self):
        project = obj_build.make_project()
        [staff] = obj_build.make_staff_users(project.course, 1)
        self.do_permission_denied_create_test(
            ag_models.RerunSubmissionsTask.objects,
            APIClient(),
            staff,
            reverse('rerun_submissions_tasks', kwargs={'project_pk': project.pk}),
            {})


class GetRerunSubmissionsTaskTestCase(test_impls.GetObjectTest, UnitTestBase):
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
