import csv
import os
import tempfile
import zipfile

from typing import Iterator

import itertools
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from django.core.urlresolvers import reverse

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.core.models as ag_models


class RetrieveProjectTestCase(test_data.Client, test_data.Project, UnitTestBase):
    def test_admin_get_project(self):
        for project in self.all_projects:
            response = self.do_valid_load_project_test(
                self.admin, project, exclude_closing_time=False)
            self.assertIn('closing_time', response.data)

    def test_staff_get_project(self):
        for project in self.all_projects:
            response = self.do_valid_load_project_test(
                self.staff, project, exclude_closing_time=True)
            self.assertNotIn('closing_time', response.data)

    def test_student_get_project(self):
        for project in self.visible_projects:
            response = self.do_valid_load_project_test(
                self.enrolled, project, exclude_closing_time=True)
            self.assertNotIn('closing_time', response.data)

        for project in self.hidden_projects:
            self.do_permission_denied_test(self.enrolled, project)

    def test_other_get_project(self):
        response = self.do_valid_load_project_test(
            self.nobody, self.visible_public_project, exclude_closing_time=True)
        self.assertNotIn('closing_time', response.data)

        self.do_permission_denied_test(self.nobody,
                                       self.visible_private_project)

        for project in self.hidden_projects:
            self.do_permission_denied_test(self.nobody, project)

    def do_valid_load_project_test(self, user, project, exclude_closing_time):
        self.client.force_authenticate(user)
        response = self.client.get(self.get_proj_url(project))
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        proj_dict = project.to_dict()
        if exclude_closing_time:
            proj_dict.pop('closing_time', None)
        self.assertEqual(proj_dict, response.data)

        return response

    def do_permission_denied_test(self, user, project):
        self.client.force_authenticate(user)
        response = self.client.get(self.get_proj_url(project))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class UpdateProjectTestCase(test_data.Client, test_data.Project, UnitTestBase):
    def setUp(self):
        super().setUp()
        self.url = self.get_proj_url(self.project)

    def test_admin_edit_project(self):
        args = {
            'name': self.project.name + 'waaaaa',
            'min_group_size': self.project.min_group_size + 4,
            'max_group_size': self.project.max_group_size + 5
        }

        self.client.force_authenticate(self.admin)
        response = self.client.patch(self.url, args)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        self.project.refresh_from_db()
        self.assertEqual(self.project.to_dict(), response.data)

        for arg_name, value in args.items():
            self.assertEqual(value, getattr(self.project, arg_name))

    def test_edit_project_invalid_settings(self):
        args = {
            'min_group_size': self.project.min_group_size + 2,
            'max_group_size': self.project.max_group_size + 1
        }

        self.client.force_authenticate(self.admin)
        response = self.client.patch(self.url, args)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        self.project.refresh_from_db()
        for arg_name, value in args.items():
            self.assertNotEqual(value, getattr(self.project, arg_name))

    def test_non_admin_edit_project_permission_denied(self):
        original_name = self.project.name
        for user in self.staff, self.enrolled, self.nobody:
            self.client.force_authenticate(user)
            response = self.client.patch(self.url, {'name': 'steve'})
            self.assertEqual(403, response.status_code)

            self.project.refresh_from_db()
            self.assertEqual(original_name, self.project.name)


class NumQueuedSubmissionsTestCase(test_data.Client, test_data.Project, UnitTestBase):
    def test_get_num_queued_submissions(self):
        course = obj_build.build_course()
        proj_args = {
            'course': course,
            'visible_to_students': True,
            'guests_can_submit': True
        }
        no_submits = obj_build.build_project(proj_args)
        with_submits1 = obj_build.build_project(proj_args)
        with_submits2 = obj_build.build_project(proj_args)

        group_with_submits1 = obj_build.build_submission_group(
            group_kwargs={'project': with_submits1})
        group_with_submits2 = obj_build.build_submission_group(
            group_kwargs={'project': with_submits2})

        g1_statuses = [ag_models.Submission.GradingStatus.queued,
                       ag_models.Submission.GradingStatus.finished_grading,
                       ag_models.Submission.GradingStatus.removed_from_queue,
                       ag_models.Submission.GradingStatus.received,
                       ag_models.Submission.GradingStatus.being_graded,
                       ag_models.Submission.GradingStatus.error]

        for grading_status in g1_statuses:
            obj_build.build_submission(
                status=grading_status,
                submission_group=group_with_submits1)

        for i in range(3):
            obj_build.build_submission(
                status=ag_models.Submission.GradingStatus.queued,
                submission_group=group_with_submits2)

        self.client.force_authenticate(self.admin)
        response = self.client.get(
            reverse('project-num-queued-submissions',
                    kwargs={'pk': no_submits.pk}))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(0, response.data)

        response = self.client.get(
            reverse('project-num-queued-submissions',
                    kwargs={'pk': with_submits1.pk}))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(1, response.data)

        response = self.client.get(
            reverse('project-num-queued-submissions',
                    kwargs={'pk': with_submits2.pk}))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(3, response.data)


@mock.patch(
    'autograder.rest_api.views.project_views.project_detail_view._PROGRESS_UPDATE_FREQUENCY',
    new=1)
class DownloadSubmissionFilesTestCase(test_data.Client, UnitTestBase):
    def setUp(self):
        super().setUp()

        # This submission that belongs to another project shouldn't
        # prevent us from downloading files for our project.
        obj_build.build_submission(status=ag_models.Submission.GradingStatus.being_graded)

        self.files = [
            SimpleUploadedFile('file1.txt', b'adsfadslkfajsdkfj'),
            SimpleUploadedFile('file2.txt', b'asdqeirueinfaksdnfaadf'),
            SimpleUploadedFile('file3.txt', b'cmxcnajsddhadf')
        ]

        self.files_by_name = dict(zip([file_.name for file_ in self.files], self.files))

        max_group_size = 3
        self.project = obj_build.make_project(visible_to_students=True,
                                              max_group_size=max_group_size)
        ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            project=self.project, pattern='*', max_num_matches=3)
        self.student_group1 = obj_build.make_group(project=self.project)
        self.group1_submission1 = obj_build.build_finished_submission(
            submitted_files=self.files[:1],
            submission_group=self.student_group1)
        self.group1_submission2 = obj_build.build_finished_submission(
            submitted_files=self.files[:2],
            submission_group=self.student_group1)

        self.student_group2 = obj_build.make_group(num_members=max_group_size,
                                                   project=self.project)
        self.group2_submission1 = obj_build.build_finished_submission(
            submitted_files=self.files[-1:],
            submission_group=self.student_group2)

        self.staff_group = obj_build.make_group(project=self.project,
                                                members_role=ag_models.UserRole.staff)
        self.staff_submission1 = obj_build.build_finished_submission(
            submitted_files=self.files,
            submission_group=self.staff_group)

        self.no_submissions_group = obj_build.make_group(project=self.project)

        [self.admin] = obj_build.make_admin_users(self.project.course, 1)

    def test_download_all_files(self):
        url = reverse('project-all-submission-files', kwargs={'pk': self.project.pk})
        self.do_download_submissions_test(
            url, [self.group1_submission1, self.group1_submission2, self.group2_submission1])

    def test_download_ultimate_submission_files(self):
        url = reverse('project-ultimate-submission-files', kwargs={'pk': self.project.pk})
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
        most_recent_submissions = [self.group1_submission2, self.group2_submission1]
        self.do_download_submissions_test(url, most_recent_submissions)

    def test_all_files_include_staff(self):
        url = reverse('project-all-submission-files', kwargs={'pk': self.project.pk})
        url += '?include_staff=true'
        self.do_download_submissions_test(
            url, [self.group1_submission1, self.group1_submission2,
                  self.group2_submission1, self.staff_submission1])

    def test_ultimate_submission_files_include_staff(self):
        url = reverse('project-ultimate-submission-files', kwargs={'pk': self.project.pk})
        url += '?include_staff=true'
        staff_submission2 = obj_build.build_finished_submission(
            submitted_files=self.files[:-1],
            submission_group=self.staff_group)
        most_recent_submissions = [
            self.group1_submission2, self.group2_submission1, staff_submission2]
        self.do_download_submissions_test(url, most_recent_submissions)

    def test_non_admin_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.project.course, 1)
        self.client.force_authenticate(staff)
        response = self.client.get(
            reverse('project-all-submission-files', kwargs={'pk': self.project.pk}))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.get(
            reverse('project-ultimate-submission-files', kwargs={'pk': self.project.pk}))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_error_submissions_not_finished_grading_removed_or_error(self):
        self.client.force_authenticate(self.admin)
        not_finished = obj_build.build_submission(submission_group=self.student_group2)
        for grading_status in ag_models.Submission.GradingStatus.active_statuses:
            not_finished.status = grading_status
            not_finished.save()

            response = self.client.get(
                reverse('project-all-submission-files', kwargs={'pk': self.project.pk}))
            self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

            response = self.client.get(
                reverse('project-ultimate-submission-files', kwargs={'pk': self.project.pk}))
            self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def do_download_submissions_test(self, url,
                                     expected_submissions: Iterator[ag_models.Submission]):
        self.client.force_authenticate(self.admin)

        response = self.client.get(url)
        self.assertEqual(status.HTTP_202_ACCEPTED, response.status_code)

        task = ag_models.DownloadTask.objects.get(pk=response.data['pk'])
        self.assertFalse(task.has_error, msg=task.error_msg)
        self.assertEqual(100, task.progress)

        expected_filenames = []
        for submission in expected_submissions:
            for filename in submission.submitted_filenames:
                expected_filenames.append(
                    '{}_{}/{}-{}/{}'.format(
                        self.project.course.name, self.project.name,
                        '_'.join(sorted(submission.submission_group.member_names)),
                        submission.timestamp.isoformat(), filename))

        with open(task.result_filename, 'rb') as result:
            with zipfile.ZipFile(result) as z:
                self.assertCountEqual(expected_filenames, [info.filename for info in z.infolist()])
                for info in z.infolist():
                    with z.open(info.filename) as f:
                        expected_file = self.files_by_name[os.path.basename(info.filename)]
                        expected_file.open()
                        self.assertEqual(expected_file.read(), f.read())


@mock.patch(
    'autograder.rest_api.views.project_views.project_detail_view._PROGRESS_UPDATE_FREQUENCY',
    new=1)
class DownloadGradesTestCase(test_data.Client, UnitTestBase):
    def setUp(self):
        super().setUp()

        # This submission that belongs to another project shouldn't
        # prevent us from downloading grades for our project.
        obj_build.build_submission(status=ag_models.Submission.GradingStatus.being_graded)

        max_group_size = 3
        self.project = obj_build.make_project(
            visible_to_students=True,
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.best,
            max_group_size=max_group_size
        )
        self.suite1 = obj_build.make_ag_test_suite(self.project)
        self.suite1_case = obj_build.make_ag_test_case(self.suite1)
        self.suite1_cmd = obj_build.make_full_ag_test_command(self.suite1_case)
        self.suite2 = obj_build.make_ag_test_suite(self.project)
        self.suite2_case = obj_build.make_ag_test_case(self.suite2)
        self.suite2_cmd = obj_build.make_full_ag_test_command(self.suite2_case)

        self.student_group1 = obj_build.make_group(project=self.project)
        self.group1_submission1_best = obj_build.build_finished_submission(
            submission_group=self.student_group1)
        obj_build.make_correct_ag_test_command_result(self.suite1_cmd,
                                                      submission=self.group1_submission1_best)
        obj_build.make_correct_ag_test_command_result(self.suite2_cmd,
                                                      submission=self.group1_submission1_best)
        self.group1_submission2 = obj_build.build_finished_submission(
            submission_group=self.student_group1)
        obj_build.make_correct_ag_test_command_result(self.suite1_cmd,
                                                      submission=self.group1_submission2)
        obj_build.make_incorrect_ag_test_command_result(self.suite2_cmd,
                                                        submission=self.group1_submission2)

        self.student_group2 = obj_build.make_group(num_members=max_group_size,
                                                   project=self.project)
        self.group2_only_submission = obj_build.build_finished_submission(
            submission_group=self.student_group2)
        obj_build.make_incorrect_ag_test_command_result(self.suite1_cmd,
                                                        submission=self.group2_only_submission)
        obj_build.make_incorrect_ag_test_command_result(self.suite2_cmd,
                                                        submission=self.group2_only_submission)

        self.staff_group = obj_build.make_group(project=self.project,
                                                members_role=ag_models.UserRole.staff)
        self.staff_submission1 = obj_build.build_finished_submission(
            submission_group=self.staff_group)
        obj_build.make_correct_ag_test_command_result(self.suite1_cmd,
                                                      submission=self.staff_submission1)
        obj_build.make_correct_ag_test_command_result(self.suite2_cmd,
                                                      submission=self.staff_submission1)

        self.no_submissions_group = obj_build.make_group(project=self.project)

        [self.admin] = obj_build.make_admin_users(self.project.course, 1)

    def test_download_all_scores(self):
        url = reverse('project-all-submission-scores', kwargs={'pk': self.project.pk})
        self.do_download_scores_test(
            url, self.project,
            [self.group1_submission1_best, self.group1_submission2, self.group2_only_submission])

    def test_download_all_scores_non_finished_grading_not_included(self):
        obj_build.build_submission(
            submission_group=self.student_group2,
            status=ag_models.Submission.GradingStatus.removed_from_queue)
        obj_build.build_submission(
            submission_group=self.student_group2,
            status=ag_models.Submission.GradingStatus.error)
        url = reverse('project-all-submission-scores', kwargs={'pk': self.project.pk})
        self.assertEqual(2, ag_models.Submission.objects.filter(
            submission_group__project=self.project
        ).exclude(
            status=ag_models.Submission.GradingStatus.finished_grading).count())
        self.do_download_scores_test(
            url, self.project,
            [self.group1_submission1_best, self.group1_submission2, self.group2_only_submission])

    def test_download_ultimate_submission_scores(self):
        url = reverse('project-ultimate-submission-scores', kwargs={'pk': self.project.pk})
        self.do_download_scores_test(
            url, self.project,
            [self.group1_submission1_best, self.group2_only_submission])

    def test_include_staff_all_scores(self):
        url = reverse('project-all-submission-scores', kwargs={'pk': self.project.pk})
        url += '?include_staff=true'
        self.do_download_scores_test(
            url, self.project,
            [self.group1_submission1_best, self.group1_submission2,
             self.group2_only_submission, self.staff_submission1])

    def test_include_staff_ultimate_submission_scores(self):
        url = reverse('project-ultimate-submission-scores', kwargs={'pk': self.project.pk})
        url += '?include_staff=true'
        self.do_download_scores_test(
            url, self.project,
            [self.group1_submission1_best, self.group2_only_submission, self.staff_submission1])

    def test_non_admin_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.project.course, 1)
        self.client.force_authenticate(staff)
        response = self.client.get(
            reverse('project-all-submission-scores', kwargs={'pk': self.project.pk}))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.get(
            reverse('project-ultimate-submission-scores', kwargs={'pk': self.project.pk}))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_error_submissions_not_finished_grading_removed_or_error(self):
        self.client.force_authenticate(self.admin)
        not_finished = obj_build.build_submission(submission_group=self.student_group2)
        for grading_status in ag_models.Submission.GradingStatus.active_statuses:
            not_finished.status = grading_status
            not_finished.save()

            response = self.client.get(
                reverse('project-all-submission-scores', kwargs={'pk': self.project.pk}))
            self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

            response = self.client.get(
                reverse('project-ultimate-submission-scores', kwargs={'pk': self.project.pk}))
            self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def do_download_scores_test(self, url, project: ag_models.Project,
                                expected_submissions: Iterator[ag_models.Submission]):
        self.client.force_authenticate(self.admin)

        response = self.client.get(url)
        self.assertEqual(status.HTTP_202_ACCEPTED, response.status_code)

        expected_headers = ['Username {}'.format(i + 1) for i in range(project.max_group_size)]
        expected_headers.append('Timestamp')
        expected_headers += ['Total', 'Total Possible']
        for suite in project.ag_test_suites.all():
            expected_headers += ['{} Total'.format(suite.name),
                                 '{} Total Possible'.format(suite.name)]
            for case in suite.ag_test_cases.all():
                expected_headers.append('{} - {}'.format(suite.name, case.name))

        expected_result = []
        for submission in expected_submissions:
            values = []
            user_padding_len = project.max_group_size - submission.submission_group.members.count()
            usernames = itertools.chain(sorted(submission.submission_group.member_names),
                                        itertools.repeat('', user_padding_len))
            values += list(usernames)
            values.append(submission.timestamp.isoformat())

            fdbk = submission.get_fdbk(ag_models.FeedbackCategory.max)
            values += [str(fdbk.total_points), str(fdbk.total_points_possible)]
            for suite_result in fdbk.ag_test_suite_results:
                suite_fdbk = suite_result.get_fdbk(ag_models.FeedbackCategory.max)
                values += [str(suite_fdbk.total_points), str(suite_fdbk.total_points_possible)]
                for case_result in suite_fdbk.ag_test_case_results:
                    values.append(
                        str(case_result.get_fdbk(ag_models.FeedbackCategory.max).total_points))

            self.assertEqual(len(expected_headers), len(values))
            expected_result.append(dict(zip(expected_headers, values)))

        task = ag_models.DownloadTask.objects.get(pk=response.data['pk'])
        self.assertEqual(100, task.progress)
        self.assertEqual('', task.error_msg)
        with open(task.result_filename) as f:
            actual_result = list(csv.DictReader(f))
        self.assertCountEqual(expected_result, actual_result)


class DownloadTaskEndpointsTestCase(test_data.Client, UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.build_project()

    def test_list_project_download_tasks(self):
        user1, user2 = obj_build.make_admin_users(self.project.course, 2)

        task1 = ag_models.DownloadTask.objects.validate_and_create(
            project=self.project,
            creator=user1, download_type=ag_models.DownloadType.all_scores)
        task2 = ag_models.DownloadTask.objects.validate_and_create(
            project=self.project,
            creator=user2, download_type=ag_models.DownloadType.final_graded_submission_files)

        url = reverse('project-download-tasks', kwargs={'pk': self.project.pk})
        self.client.force_authenticate(user1)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual([task1.to_dict()], response.data)

    def test_non_admin_list_project_download_tasks_permission_denied(self):
        [user] = obj_build.make_staff_users(self.project.course, 1)

        url = reverse('project-download-tasks', kwargs={'pk': self.project.pk})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_get_download_task_detail(self):
        [user] = obj_build.make_admin_users(self.project.course, 1)

        task = ag_models.DownloadTask.objects.validate_and_create(
            project=self.project,
            creator=user, download_type=ag_models.DownloadType.all_scores)

        url = reverse('download_tasks-detail', kwargs={'pk': task.pk})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(task.to_dict(), response.data)

    def test_non_creator_get_download_task_detail_permission_denied(self):
        [user, other] = obj_build.make_admin_users(self.project.course, 2)

        task = ag_models.DownloadTask.objects.validate_and_create(
            project=self.project,
            creator=user, download_type=ag_models.DownloadType.all_scores)

        url = reverse('download_tasks-detail', kwargs={'pk': task.pk})
        self.client.force_authenticate(other)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_get_download_task_result(self):
        content = b'spaaaam'
        with tempfile.NamedTemporaryFile() as f:
            f.write(content)
            f.seek(0)

            [user] = obj_build.make_admin_users(self.project.course, 1)

            task = ag_models.DownloadTask.objects.validate_and_create(
                project=self.project,
                creator=user, download_type=ag_models.DownloadType.final_graded_submission_scores,
                progress=100,
                result_filename=f.name)

            url = reverse('download_tasks-result', kwargs={'pk': task.pk})
            self.client.force_authenticate(user)
            response = self.client.get(url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertEqual(f.read(), b''.join((chunk for chunk in response.streaming_content)))

    def test_get_download_task_result_in_progress_error(self):
        [user] = obj_build.make_admin_users(self.project.course, 1)

        in_progress_task = ag_models.DownloadTask.objects.validate_and_create(
            project=self.project,
            creator=user, download_type=ag_models.DownloadType.all_scores)

        url = reverse('download_tasks-result', kwargs={'pk': in_progress_task.pk})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(in_progress_task.progress, response.data['in_progress'])

    def test_get_download_task_result_task_errored_error(self):
        [user] = obj_build.make_admin_users(self.project.course, 1)
        errored_task = ag_models.DownloadTask.objects.validate_and_create(
            project=self.project,
            creator=user, download_type=ag_models.DownloadType.all_scores,
            progress=100, error_msg='badz')

        url = reverse('download_tasks-result', kwargs={'pk': errored_task.pk})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(errored_task.error_msg, response.data['task_error'])

    def test_non_creator_get_download_task_result_permission_denied(self):
        [user, other] = obj_build.make_admin_users(self.project.course, 2)

        task = ag_models.DownloadTask.objects.validate_and_create(
            project=self.project,
            creator=user, download_type=ag_models.DownloadType.all_scores,
            progress=100)

        url = reverse('download_tasks-result', kwargs={'pk': task.pk})
        self.client.force_authenticate(other)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
