import csv
import datetime
import itertools
import os
import tempfile
import zipfile
from collections import OrderedDict
from typing import Iterator, BinaryIO
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.handgrading.models as hg_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.submission_feedback import (
    update_denormalized_ag_test_results, SubmissionResultFeedback, AGTestPreLoader)
from autograder.core.tests.test_submission_feedback.fdbk_getter_shortcuts import (
    get_submission_fdbk)
from autograder.core.submission_feedback import MutationTestSuitePreLoader
from autograder.utils.testing import UnitTestBase


@mock.patch('autograder.rest_api.tasks.project_downloads._PROGRESS_UPDATE_FREQUENCY', new=1)
class DownloadSubmissionFilesTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.client = APIClient()

        # This submission that belongs to another project shouldn't
        # prevent us from downloading files for our project.
        obj_build.make_submission(status=ag_models.Submission.GradingStatus.being_graded)

        self.files = [
            SimpleUploadedFile('file1.txt', b'adsfadslkfajsdkfj'),
            SimpleUploadedFile('file2.txt', b'asdqeirueinfaksdnfaadf'),
            SimpleUploadedFile('file3.txt', b'cmxcnajsddhadf')
        ]

        self.files_by_name = dict(zip([file_.name for file_ in self.files], self.files))

        max_group_size = 3
        self.project = obj_build.make_project(visible_to_students=True,
                                              max_group_size=max_group_size)
        ag_models.ExpectedStudentFile.objects.validate_and_create(
            project=self.project, pattern='*', max_num_matches=3)
        self.student_group1 = obj_build.make_group(project=self.project)
        self.group1_submission1 = obj_build.make_finished_submission(
            submitted_files=self.files[:1],
            group=self.student_group1)
        self.group1_submission2 = obj_build.make_finished_submission(
            submitted_files=self.files[:2],
            group=self.student_group1)

        self.student_group2 = obj_build.make_group(num_members=max_group_size,
                                                   project=self.project)
        self.group2_submission1 = obj_build.make_finished_submission(
            submitted_files=self.files[-1:],
            group=self.student_group2)

        self.staff_group = obj_build.make_group(project=self.project,
                                                members_role=obj_build.UserRole.staff)
        self.staff_submission1 = obj_build.make_finished_submission(
            submitted_files=self.files,
            group=self.staff_group)

        self.no_submissions_group = obj_build.make_group(project=self.project)

        [self.admin] = obj_build.make_admin_users(self.project.course, 1)

    def test_download_all_files(self):
        url = reverse('all-submission-files-task', kwargs={'pk': self.project.pk})
        self.do_download_submissions_test(
            url, [self.group1_submission1, self.group1_submission2, self.group2_submission1])

    def test_download_ultimate_submission_files(self):
        url = reverse('ultimate-submission-files-task', kwargs={'pk': self.project.pk})
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
        most_recent_submissions = [self.group1_submission2, self.group2_submission1]
        self.do_download_submissions_test(url, most_recent_submissions)

    def test_all_files_include_staff(self):
        url = reverse('all-submission-files-task', kwargs={'pk': self.project.pk})
        url += '?include_staff=true'
        self.do_download_submissions_test(
            url, [self.group1_submission1, self.group1_submission2,
                  self.group2_submission1, self.staff_submission1])

    def test_ultimate_submission_files_include_staff(self):
        url = reverse('ultimate-submission-files-task', kwargs={'pk': self.project.pk})
        url += '?include_staff=true'
        staff_submission2 = obj_build.make_finished_submission(
            submitted_files=self.files[:-1],
            group=self.staff_group)
        most_recent_submissions = [
            self.group1_submission2, self.group2_submission1, staff_submission2]
        self.do_download_submissions_test(url, most_recent_submissions)

    def test_download_all_submission_files_no_submissions(self):
        ag_models.Submission.objects.all().delete()

        url = reverse('all-submission-files-task', kwargs={'pk': self.project.pk})
        self.do_download_submissions_test(url, [])

    def test_download_ultimate_submission_files_no_submissions(self):
        ag_models.Submission.objects.all().delete()

        self.student_group1.delete()
        self.student_group2.delete()
        self.no_submissions_group.delete()

        url = reverse('ultimate-submission-files-task', kwargs={'pk': self.project.pk})
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
        self.do_download_submissions_test(url, [])

    def test_download_ultimate_submission_files_only_one_staff_group_with_submission(self):
        # This is a regression test to prevent a divide by zero error.
        # See https://github.com/eecs-autograder/autograder-server/issues/273
        ag_models.Group.objects.all().delete()
        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.admin)
        obj_build.make_finished_submission(group)

        # Exclude staff
        url = reverse('ultimate-submission-files-task', kwargs={'pk': self.project.pk})
        self.do_download_submissions_test(url, [])

    def test_non_admin_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.project.course, 1)
        self.client.force_authenticate(staff)
        response = self.client.post(
            reverse('all-submission-files-task', kwargs={'pk': self.project.pk}))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.post(
            reverse('ultimate-submission-files-task', kwargs={'pk': self.project.pk}))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_unfinished_and_error_submissions_ignored(self):
        self.client.force_authenticate(self.admin)

        student_group3 = obj_build.make_group(num_members=1, project=self.project)

        received = obj_build.make_submission(group=self.student_group1)
        received.status = ag_models.Submission.GradingStatus.received
        received.save()

        queued = obj_build.make_submission(group=self.student_group2)
        queued.status = ag_models.Submission.GradingStatus.queued
        queued.save()

        being_graded = obj_build.make_submission(group=student_group3)
        being_graded.status = ag_models.Submission.GradingStatus.being_graded
        being_graded.save()

        waiting_for_deferred = obj_build.make_submission(group=self.student_group2)
        waiting_for_deferred.status = ag_models.Submission.GradingStatus.waiting_for_deferred
        waiting_for_deferred.save()

        error = obj_build.make_submission(group=self.student_group2)
        error.status = ag_models.Submission.GradingStatus.error
        error.save()

        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)

        self.do_download_submissions_test(
            reverse('all-submission-files-task', kwargs={'pk': self.project.pk}),
            [self.group1_submission1, self.group1_submission2, self.group2_submission1])

        self.do_download_submissions_test(
            reverse('ultimate-submission-files-task', kwargs={'pk': self.project.pk}),
            [self.group1_submission2, self.group2_submission1])

    def do_download_submissions_test(self, url,
                                     expected_submissions: Iterator[ag_models.Submission]):
        self.client.force_authenticate(self.admin)

        response = self.client.post(url)
        self.assertEqual(status.HTTP_202_ACCEPTED, response.status_code)

        task = ag_models.DownloadTask.objects.get(pk=response.data['pk'])
        self.assertFalse(task.has_error, msg=task.error_msg)
        self.assertEqual(100, task.progress)

        expected_filenames = self._get_expected_filenames(expected_submissions)

        # Check the content directly from the filesystem
        with open(task.result_filename, 'rb') as result:
            self._check_zip_content(result, expected_filenames)

        # Check the content returned by the result endpoint
        result_content_url = reverse('download-task-result', kwargs={'pk': task.pk})
        response = self.client.get(result_content_url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual('application/zip', response['Content-Type'])

        with tempfile.TemporaryFile() as result:
            result.write(b''.join(response.streaming_content))
            self._check_zip_content(result, expected_filenames)

        # Make sure that other admin users can request results for downloads
        # they didn't start
        [other_admin] = obj_build.make_admin_users(self.project.course, 1)
        self.client.force_authenticate(other_admin)
        response = self.client.get(result_content_url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual('application/zip', response['Content-Type'])

        with tempfile.TemporaryFile() as result:
            result.write(b''.join(response.streaming_content))
            self._check_zip_content(result, expected_filenames)

    def _get_expected_filenames(self, expected_submissions):
        expected_filenames = []
        for submission in expected_submissions:
            for filename in submission.submitted_filenames:
                expected_filenames.append(
                    '{}_{}/{}-{}/{}'.format(
                        self.project.course.name, self.project.name,
                        '_'.join(sorted(submission.group.member_names)),
                        submission.timestamp.isoformat(), filename))

        return expected_filenames

    def _check_zip_content(self, result: BinaryIO, expected_filenames):
        result.seek(0)
        with zipfile.ZipFile(result) as z:
            self.assertCountEqual(expected_filenames, [info.filename for info in z.infolist()])
            for info in z.infolist():
                with z.open(info.filename) as f:
                    expected_file = self.files_by_name[os.path.basename(info.filename)]
                    expected_file.open()
                    self.assertEqual(expected_file.read(), f.read())


@mock.patch('autograder.rest_api.tasks.project_downloads._PROGRESS_UPDATE_FREQUENCY', new=1)
class DownloadAllUltimateSubmissionGradesTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None

        self.client = APIClient()

        self.project = obj_build.make_project(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.most_recent,
        )

        self.url = reverse('ultimate-submission-scores-task', kwargs={'pk': self.project.pk})

        self.admin = obj_build.make_admin_user(self.project.course)

        self.ag_test_suite = obj_build.make_ag_test_suite(project=self.project)
        self.ag_test_case = obj_build.make_ag_test_case(ag_test_suite=self.ag_test_suite)
        self.ag_test_cmd = obj_build.make_full_ag_test_command(ag_test_case=self.ag_test_case)

        self.student_group = obj_build.make_group(project=self.project, num_members=2)
        self.student_submission = obj_build.make_finished_submission(self.student_group)
        self.student_result = obj_build.make_incorrect_ag_test_command_result(
            ag_test_command=self.ag_test_cmd, submission=self.student_submission)

        self.student_submission = update_denormalized_ag_test_results(self.student_submission.pk)
        self.student_result_fdbk = SubmissionResultFeedback(
            self.student_submission, ag_models.FeedbackCategory.max,
            AGTestPreLoader(self.project))

        self.assertEqual(0, self.student_result_fdbk.total_points)
        self.assertNotEqual(0, self.student_result_fdbk.total_points_possible)

        self.staff_group = obj_build.make_group(
            project=self.project, members_role=obj_build.UserRole.admin)
        self.staff_submission = obj_build.make_finished_submission(self.staff_group)
        self.staff_result = obj_build.make_correct_ag_test_command_result(
            ag_test_command=self.ag_test_cmd, submission=self.staff_submission)

        self.staff_submission = update_denormalized_ag_test_results(self.staff_submission.pk)
        self.staff_result_fdbk = SubmissionResultFeedback(
            self.staff_submission, ag_models.FeedbackCategory.max,
            AGTestPreLoader(self.project))

        self.assertNotEqual(0, self.staff_result_fdbk.total_points)
        self.assertNotEqual(0, self.staff_result_fdbk.total_points_possible)

        # Make sure we use the right queryset
        other_project = obj_build.make_project(course=self.project.course)
        other_group = obj_build.make_group(project=other_project)
        other_submission = obj_build.make_finished_submission(other_group)

    def test_serialize_ultimate_submission_results_called(self):
        mock_serialize_ultimate_submission_results = mock.Mock(return_value=[])

        with mock.patch('autograder.rest_api.tasks.project_downloads'
                        '.serialize_ultimate_submission_results',
                        new=mock_serialize_ultimate_submission_results):
            self.client.force_authenticate(self.admin)
            self.client.post(self.url)

            mock_serialize_ultimate_submission_results.assert_called_once()

    def test_download_all_ultimate_submission_scores_no_staff(self):
        expected = [
            OrderedDict({
                'Username': self.student_group.member_names[0],
                'Group Members': (
                    f'{self.student_group.member_names[0]},{self.student_group.member_names[1]}'),
                'Timestamp': str(self.student_submission.timestamp),
                'Extension': '',
                'Total Points': str(self.student_result_fdbk.total_points),
                'Total Points Possible': str(self.student_result_fdbk.total_points_possible),
                # These point values are the same as the totals because its the only test case
                f'{self.ag_test_suite.name} Total': str(self.student_result_fdbk.total_points),
                f'{self.ag_test_suite.name} Total Possible': (
                    str(self.student_result_fdbk.total_points_possible)),
                f'{self.ag_test_suite.name} - {self.ag_test_case.name}': (
                    str(self.student_result_fdbk.total_points)),
            }),
            OrderedDict({
                'Username': self.student_group.member_names[1],
                'Group Members': (
                    f'{self.student_group.member_names[0]},{self.student_group.member_names[1]}'),
                'Timestamp': str(self.student_submission.timestamp),
                'Extension': '',
                'Total Points': str(self.student_result_fdbk.total_points),
                'Total Points Possible': str(self.student_result_fdbk.total_points_possible),
                f'{self.ag_test_suite.name} Total': (str(self.student_result_fdbk.total_points)),
                f'{self.ag_test_suite.name} Total Possible': (
                    str(self.student_result_fdbk.total_points_possible)),
                f'{self.ag_test_suite.name} - {self.ag_test_case.name}': (
                    str(self.student_result_fdbk.total_points)),
            })
        ]

        self.do_ultimate_submission_scores_csv_test(self.url, expected)

    def test_group_has_past_extension(self):
        student_extension = timezone.now() - datetime.timedelta(days=1)
        self.student_group.validate_and_update(extended_due_date=student_extension)

        self.student_submission.timestamp = student_extension - datetime.timedelta(days=2)
        self.student_submission.save()

        expected = [
            OrderedDict({
                'Username': self.student_group.member_names[0],
                'Group Members': (
                    f'{self.student_group.member_names[0]},{self.student_group.member_names[1]}'),
                'Timestamp': str(self.student_submission.timestamp),
                'Extension': str(student_extension),
                'Total Points': str(self.student_result_fdbk.total_points),
                'Total Points Possible': str(self.student_result_fdbk.total_points_possible),
                # These point values are the same as the totals because its the only test case
                f'{self.ag_test_suite.name} Total': str(self.student_result_fdbk.total_points),
                f'{self.ag_test_suite.name} Total Possible': (
                    str(self.student_result_fdbk.total_points_possible)),
                f'{self.ag_test_suite.name} - {self.ag_test_case.name}': (
                    str(self.student_result_fdbk.total_points)),
            }),
            OrderedDict({
                'Username': self.student_group.member_names[1],
                'Group Members': (
                    f'{self.student_group.member_names[0]},{self.student_group.member_names[1]}'),
                'Timestamp': str(self.student_submission.timestamp),
                'Extension': str(student_extension),
                'Total Points': str(self.student_result_fdbk.total_points),
                'Total Points Possible': str(self.student_result_fdbk.total_points_possible),
                f'{self.ag_test_suite.name} Total': (str(self.student_result_fdbk.total_points)),
                f'{self.ag_test_suite.name} Total Possible': (
                    str(self.student_result_fdbk.total_points_possible)),
                f'{self.ag_test_suite.name} - {self.ag_test_case.name}': (
                    str(self.student_result_fdbk.total_points)),
            })
        ]

        self.do_ultimate_submission_scores_csv_test(self.url, expected)

    def test_ultimate_submission_for_group_is_none_skip_group(self):
        mock_serialize_ultimate_submission_results = mock.Mock(
            return_value=[
                {
                    'username': 'waluigi',
                    'group': {
                        'member_names': ['waluigi'],
                        'extended_due_date': '',
                    },
                    'ultimate_submission': None
                }
            ]
        )

        with mock.patch('autograder.rest_api.tasks.project_downloads'
                        '.serialize_ultimate_submission_results',
                        new=mock_serialize_ultimate_submission_results):
            self.do_ultimate_submission_scores_csv_test(self.url, [])

    def test_group_has_extension_not_past_ultimate_submission_is_none(self):
        student_extension = timezone.now() + datetime.timedelta(days=2)
        self.student_group.validate_and_update(extended_due_date=student_extension)

        self.do_ultimate_submission_scores_csv_test(self.url, [])

    def test_include_staff(self):
        expected = [
            OrderedDict({
                'Username': self.student_group.member_names[0],
                'Group Members': (
                    f'{self.student_group.member_names[0]},{self.student_group.member_names[1]}'),
                'Timestamp': str(self.student_submission.timestamp),
                'Extension': '',
                'Total Points': str(self.student_result_fdbk.total_points),
                'Total Points Possible': str(self.student_result_fdbk.total_points_possible),
                # These point values are the same as the totals because its the only test case
                f'{self.ag_test_suite.name} Total': str(self.student_result_fdbk.total_points),
                f'{self.ag_test_suite.name} Total Possible': (
                    str(self.student_result_fdbk.total_points_possible)),
                f'{self.ag_test_suite.name} - {self.ag_test_case.name}': (
                    str(self.student_result_fdbk.total_points)),
            }),
            OrderedDict({
                'Username': self.student_group.member_names[1],
                'Group Members': (
                    f'{self.student_group.member_names[0]},{self.student_group.member_names[1]}'),
                'Timestamp': str(self.student_submission.timestamp),
                'Extension': '',
                'Total Points': str(self.student_result_fdbk.total_points),
                'Total Points Possible': str(self.student_result_fdbk.total_points_possible),
                f'{self.ag_test_suite.name} Total': (str(self.student_result_fdbk.total_points)),
                f'{self.ag_test_suite.name} Total Possible': (
                    str(self.student_result_fdbk.total_points_possible)),
                f'{self.ag_test_suite.name} - {self.ag_test_case.name}': (
                    str(self.student_result_fdbk.total_points)),
            })
        ]

        staff_group_row = OrderedDict({
            'Username': self.staff_group.member_names[0],
            'Group Members': f'{self.staff_group.member_names[0]}',
            'Timestamp': str(self.staff_submission.timestamp),
            'Extension': '',
            'Total Points': str(self.staff_result_fdbk.total_points),
            'Total Points Possible': str(self.staff_result_fdbk.total_points_possible),
            f'{self.ag_test_suite.name} Total': (
                str(self.staff_result_fdbk.total_points)),
            f'{self.ag_test_suite.name} Total Possible': (
                str(self.staff_result_fdbk.total_points_possible)),
            f'{self.ag_test_suite.name} - {self.ag_test_case.name}': (
                str(self.staff_result_fdbk.total_points)),
        })

        self.assertEqual(2, self.project.groups.count())
        if self.staff_group == self.project.groups.first():
            expected.insert(0, staff_group_row)
        else:
            expected.append(staff_group_row)

        self.do_ultimate_submission_scores_csv_test(self.url + '?include_staff=true', expected)

    def test_unfinished_and_error_submissions_ignored(self):
        unfinished_statuses = filter(
            lambda val: val != ag_models.Submission.GradingStatus.finished_grading,
            ag_models.Submission.GradingStatus.values
        )
        for status in unfinished_statuses:
            self.student_submission.status = status
            self.student_submission.save()

            self.do_ultimate_submission_scores_csv_test(self.url, [])

    def test_download_ultimate_submission_scores_only_one_staff_group_with_submission(self):
        # This is a regression test to prevent a divide by zero error.
        # See https://github.com/eecs-autograder/autograder-server/issues/273
        ag_models.Group.objects.all().delete()
        group = obj_build.make_group(project=self.project, members_role=obj_build.UserRole.admin)
        obj_build.make_finished_submission(group)

        # Exclude staff
        self.do_ultimate_submission_scores_csv_test(self.url, [])

    def test_download_ultimate_submission_scores_no_submissions(self):
        ag_models.Submission.objects.all().delete()

        url = reverse('ultimate-submission-scores-task', kwargs={'pk': self.project.pk})
        self.do_ultimate_submission_scores_csv_test(self.url, [])

    def test_download_all_ultimate_submission_scores_with_handgrading(self):
        handgrading_rubric = hg_models.HandgradingRubric.objects.validate_and_create(
            project=self.project
        )  # type: hg_models.HandgradingRubric

        criterion = hg_models.Criterion.objects.validate_and_create(
            points=2, handgrading_rubric=handgrading_rubric)

        handgrading_result = hg_models.HandgradingResult.objects.validate_and_create(
            submission=self.student_submission,
            group=self.student_group,
            handgrading_rubric=handgrading_rubric,
            finished_grading=True
        )  # type: hg_models.HandgradingResult

        hg_models.CriterionResult.objects.validate_and_create(
            selected=True,
            criterion=criterion,
            handgrading_result=handgrading_result)

        expected = [
            OrderedDict({
                'Username': self.student_group.member_names[0],
                'Group Members': (
                    f'{self.student_group.member_names[0]},{self.student_group.member_names[1]}'),
                'Timestamp': str(self.student_submission.timestamp),
                'Extension': '',
                'Total Points': str(self.student_result_fdbk.total_points),
                'Total Points Possible': str(self.student_result_fdbk.total_points_possible),
                'Handgrading Total Points': str(
                    self.student_submission.handgrading_result.total_points),
                'Handgrading Total Points Possible': (
                    str(self.student_submission.handgrading_result.total_points_possible)),
                # These point values are the same as the totals because its the only test case
                f'{self.ag_test_suite.name} Total': str(self.student_result_fdbk.total_points),
                f'{self.ag_test_suite.name} Total Possible': (
                    str(self.student_result_fdbk.total_points_possible)),
                f'{self.ag_test_suite.name} - {self.ag_test_case.name}': (
                    str(self.student_result_fdbk.total_points)),
            }),
            OrderedDict({
                'Username': self.student_group.member_names[1],
                'Group Members': (
                    f'{self.student_group.member_names[0]},{self.student_group.member_names[1]}'),
                'Timestamp': str(self.student_submission.timestamp),
                'Extension': '',
                'Total Points': str(self.student_result_fdbk.total_points),
                'Total Points Possible': str(self.student_result_fdbk.total_points_possible),
                'Handgrading Total Points': str(
                    self.student_submission.handgrading_result.total_points),
                'Handgrading Total Points Possible': (
                    str(self.student_submission.handgrading_result.total_points_possible)),
                f'{self.ag_test_suite.name} Total': (str(self.student_result_fdbk.total_points)),
                f'{self.ag_test_suite.name} Total Possible': (
                    str(self.student_result_fdbk.total_points_possible)),
                f'{self.ag_test_suite.name} - {self.ag_test_case.name}': (
                    str(self.student_result_fdbk.total_points)),
            })
        ]

        self.do_ultimate_submission_scores_csv_test(self.url, expected)

    def test_download_all_ultimate_submission_scores_student_without_handgrading_result(self):
        handgrading_rubric = hg_models.HandgradingRubric.objects.validate_and_create(
            project=self.project
        )  # type: hg_models.HandgradingRubric

        criterion = hg_models.Criterion.objects.validate_and_create(
            points=2, handgrading_rubric=handgrading_rubric)

        handgrading_result = hg_models.HandgradingResult.objects.validate_and_create(
            submission=self.staff_submission,
            group=self.staff_group,
            handgrading_rubric=handgrading_rubric,
            finished_grading=True
        )  # type: hg_models.HandgradingResult

        hg_models.CriterionResult.objects.validate_and_create(
            selected=False,
            criterion=criterion,
            handgrading_result=handgrading_result)

        # Since student_group has no handgrading result, handgrading columns should be empty
        expected = [
            OrderedDict({
                'Username': self.student_group.member_names[0],
                'Group Members': (
                    f'{self.student_group.member_names[0]},{self.student_group.member_names[1]}'),
                'Timestamp': str(self.student_submission.timestamp),
                'Extension': '',
                'Total Points': str(self.student_result_fdbk.total_points),
                'Total Points Possible': str(self.student_result_fdbk.total_points_possible),
                'Handgrading Total Points': '',
                'Handgrading Total Points Possible': '',
                # These point values are the same as the totals because its the only test case
                f'{self.ag_test_suite.name} Total': str(self.student_result_fdbk.total_points),
                f'{self.ag_test_suite.name} Total Possible': (
                    str(self.student_result_fdbk.total_points_possible)),
                f'{self.ag_test_suite.name} - {self.ag_test_case.name}': (
                    str(self.student_result_fdbk.total_points)),
            }),
            OrderedDict({
                'Username': self.student_group.member_names[1],
                'Group Members': (
                    f'{self.student_group.member_names[0]},{self.student_group.member_names[1]}'),
                'Timestamp': str(self.student_submission.timestamp),
                'Extension': '',
                'Total Points': str(self.student_result_fdbk.total_points),
                'Total Points Possible': str(self.student_result_fdbk.total_points_possible),
                'Handgrading Total Points': '',
                'Handgrading Total Points Possible': '',
                f'{self.ag_test_suite.name} Total': (str(self.student_result_fdbk.total_points)),
                f'{self.ag_test_suite.name} Total Possible': (
                    str(self.student_result_fdbk.total_points_possible)),
                f'{self.ag_test_suite.name} - {self.ag_test_case.name}': (
                    str(self.student_result_fdbk.total_points)),
            })
        ]

        # Since staff_group has handgrading result, so handgrading columns are filled
        staff_group_row = OrderedDict({
            'Username': self.staff_group.member_names[0],
            'Group Members': f'{self.staff_group.member_names[0]}',
            'Timestamp': str(self.staff_submission.timestamp),
            'Extension': '',
            'Total Points': str(self.staff_result_fdbk.total_points),
            'Total Points Possible': str(self.staff_result_fdbk.total_points_possible),
            'Handgrading Total Points': (
                str(self.staff_submission.handgrading_result.total_points)),
            'Handgrading Total Points Possible': (
                str(self.staff_submission.handgrading_result.total_points_possible)),
            # These point values are the same as the totals because its the only test case
            f'{self.ag_test_suite.name} Total': str(self.staff_result_fdbk.total_points),
            f'{self.ag_test_suite.name} Total Possible': (
                str(self.staff_result_fdbk.total_points_possible)),
            f'{self.ag_test_suite.name} - {self.ag_test_case.name}': (
                str(self.staff_result_fdbk.total_points)),
        })

        if self.staff_group == self.project.groups.first():
            expected.insert(0, staff_group_row)
        else:
            expected.append(staff_group_row)

        self.do_ultimate_submission_scores_csv_test(self.url + '?include_staff=true', expected)

    def test_download_all_ultimate_submission_scores_handgrading_in_progress_not_included(self):
        handgrading_rubric = hg_models.HandgradingRubric.objects.validate_and_create(
            project=self.project
        )  # type: hg_models.HandgradingRubric

        criterion = hg_models.Criterion.objects.validate_and_create(
            points=2, handgrading_rubric=handgrading_rubric)

        handgrading_result = hg_models.HandgradingResult.objects.validate_and_create(
            submission=self.student_submission,
            group=self.student_group,
            handgrading_rubric=handgrading_rubric,
            finished_grading=False
        )  # type: hg_models.HandgradingResult

        hg_models.CriterionResult.objects.validate_and_create(
            selected=True,
            criterion=criterion,
            handgrading_result=handgrading_result)

        expected = [
            OrderedDict({
                'Username': self.student_group.member_names[0],
                'Group Members': (
                    f'{self.student_group.member_names[0]},{self.student_group.member_names[1]}'),
                'Timestamp': str(self.student_submission.timestamp),
                'Extension': '',
                'Total Points': str(self.student_result_fdbk.total_points),
                'Total Points Possible': str(self.student_result_fdbk.total_points_possible),
                'Handgrading Total Points': '',
                'Handgrading Total Points Possible': '',
                # These point values are the same as the totals because its the only test case
                f'{self.ag_test_suite.name} Total': str(self.student_result_fdbk.total_points),
                f'{self.ag_test_suite.name} Total Possible': (
                    str(self.student_result_fdbk.total_points_possible)),
                f'{self.ag_test_suite.name} - {self.ag_test_case.name}': (
                    str(self.student_result_fdbk.total_points)),
            }),
            OrderedDict({
                'Username': self.student_group.member_names[1],
                'Group Members': (
                    f'{self.student_group.member_names[0]},{self.student_group.member_names[1]}'),
                'Timestamp': str(self.student_submission.timestamp),
                'Extension': '',
                'Total Points': str(self.student_result_fdbk.total_points),
                'Total Points Possible': str(self.student_result_fdbk.total_points_possible),
                'Handgrading Total Points': '',
                'Handgrading Total Points Possible': '',
                f'{self.ag_test_suite.name} Total': (str(self.student_result_fdbk.total_points)),
                f'{self.ag_test_suite.name} Total Possible': (
                    str(self.student_result_fdbk.total_points_possible)),
                f'{self.ag_test_suite.name} - {self.ag_test_case.name}': (
                    str(self.student_result_fdbk.total_points)),
            })
        ]

        self.do_ultimate_submission_scores_csv_test(self.url, expected)

    def do_ultimate_submission_scores_csv_test(self, url, expected_rows):
        self.client.force_authenticate(self.admin)

        response = self.client.post(url)
        self.assertEqual(status.HTTP_202_ACCEPTED, response.status_code)

        # Check the content directly from the filesystem
        task = ag_models.DownloadTask.objects.get(pk=response.data['pk'])

        self.assertEqual(100, task.progress)
        self.assertEqual('', task.error_msg)

        with open(task.result_filename) as f:
            actual_result = list(csv.DictReader(f))
        self.assertEqual(expected_rows, actual_result)

        # Check the content returned by the result endpoint
        result_content_url = reverse('download-task-result', kwargs={'pk': task.pk})
        response = self.client.get(result_content_url)
        _check_csv_response(self, response, expected_rows)

        # Make sure that other admin users can request results for downloads
        # they didn't start.
        other_admin = obj_build.make_admin_user(self.project.course)
        self.client.force_authenticate(other_admin)
        response = self.client.get(result_content_url)
        _check_csv_response(self, response, expected_rows)


@mock.patch('autograder.rest_api.tasks.project_downloads._PROGRESS_UPDATE_FREQUENCY', new=1)
class DownloadAllSubmissionGradesTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.client = APIClient()

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

        self.mutation_suite1_bugs = ['suite1_bug{}'.format(i) for i in range(3)]
        self.mutation_suite1 = obj_build.make_mutation_test_suite(
            project=self.project, buggy_impl_names=self.mutation_suite1_bugs)

        self.mutation_suite2_bugs = ['suite2_bug{}'.format(i) for i in range(5)]
        self.mutation_suite2 = obj_build.make_mutation_test_suite(
            project=self.project, buggy_impl_names=self.mutation_suite2_bugs)

        self.student_group1 = obj_build.make_group(project=self.project)
        self.group1_submission1_best = obj_build.make_finished_submission(
            group=self.student_group1)
        obj_build.make_correct_ag_test_command_result(self.suite1_cmd,
                                                      submission=self.group1_submission1_best)
        obj_build.make_correct_ag_test_command_result(self.suite2_cmd,
                                                      submission=self.group1_submission1_best)
        ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_suite1,
            submission=self.group1_submission1_best,
            bugs_exposed=self.mutation_suite1_bugs)
        ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_suite2,
            submission=self.group1_submission1_best,
            bugs_exposed=self.mutation_suite2_bugs)
        self.group1_submission2 = obj_build.make_finished_submission(
            group=self.student_group1)
        obj_build.make_correct_ag_test_command_result(self.suite1_cmd,
                                                      submission=self.group1_submission2)
        obj_build.make_incorrect_ag_test_command_result(self.suite2_cmd,
                                                        submission=self.group1_submission2)
        ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_suite1,
            submission=self.group1_submission2,
            bugs_exposed=[])
        ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_suite2,
            submission=self.group1_submission2,
            bugs_exposed=[])

        self.group1_submission1_best = update_denormalized_ag_test_results(
            self.group1_submission1_best.pk)
        self.group1_submission2 = update_denormalized_ag_test_results(self.group1_submission2.pk)

        self.student_group2 = obj_build.make_group(num_members=max_group_size,
                                                   project=self.project)
        self.group2_only_submission = obj_build.make_finished_submission(
            group=self.student_group2)
        obj_build.make_incorrect_ag_test_command_result(self.suite1_cmd,
                                                        submission=self.group2_only_submission)
        obj_build.make_incorrect_ag_test_command_result(self.suite2_cmd,
                                                        submission=self.group2_only_submission)
        ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_suite1,
            submission=self.group2_only_submission,
            bugs_exposed=self.mutation_suite1_bugs[:-1])
        ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_suite2,
            submission=self.group2_only_submission,
            bugs_exposed=self.mutation_suite2_bugs[:-1])

        self.group2_only_submission = update_denormalized_ag_test_results(
            self.group2_only_submission.pk)

        self.staff_group = obj_build.make_group(project=self.project,
                                                members_role=obj_build.UserRole.staff)
        self.staff_submission1 = obj_build.make_finished_submission(
            group=self.staff_group)
        obj_build.make_correct_ag_test_command_result(self.suite1_cmd,
                                                      submission=self.staff_submission1)
        obj_build.make_correct_ag_test_command_result(self.suite2_cmd,
                                                      submission=self.staff_submission1)
        ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_suite1,
            submission=self.staff_submission1,
            bugs_exposed=self.mutation_suite1_bugs[:-1])
        ag_models.MutationTestSuiteResult.objects.validate_and_create(
            mutation_test_suite=self.mutation_suite2,
            submission=self.staff_submission1,
            bugs_exposed=self.mutation_suite2_bugs)

        self.staff_submission1 = update_denormalized_ag_test_results(self.staff_submission1.pk)

        self.no_submissions_group = obj_build.make_group(project=self.project)

        [self.admin] = obj_build.make_admin_users(self.project.course, 1)

        self.maxDiff = None

    def test_download_all_scores(self):
        url = reverse('all-submission-scores-task', kwargs={'pk': self.project.pk})
        self.do_download_scores_test(
            url, self.project,
            [self.group1_submission1_best, self.group1_submission2, self.group2_only_submission])

    def test_download_all_scores_non_finished_grading_not_included(self):
        obj_build.make_submission(
            group=self.student_group2,
            status=ag_models.Submission.GradingStatus.removed_from_queue)
        obj_build.make_submission(
            group=self.student_group2,
            status=ag_models.Submission.GradingStatus.error)
        url = reverse('all-submission-scores-task', kwargs={'pk': self.project.pk})
        self.assertEqual(2, ag_models.Submission.objects.filter(
            group__project=self.project
        ).exclude(
            status=ag_models.Submission.GradingStatus.finished_grading).count())
        self.do_download_scores_test(
            url, self.project,
            [self.group1_submission1_best, self.group1_submission2, self.group2_only_submission])

    def test_download_all_scores_no_submissions(self):
        ag_models.Submission.objects.all().delete()

        url = reverse('all-submission-scores-task', kwargs={'pk': self.project.pk})
        self.do_download_scores_test(url, self.project, [])

    def test_include_staff_all_scores(self):
        url = reverse('all-submission-scores-task', kwargs={'pk': self.project.pk})
        url += '?include_staff=true'
        self.do_download_scores_test(
            url, self.project,
            [self.group1_submission1_best, self.group1_submission2,
             self.group2_only_submission, self.staff_submission1])

    def test_non_admin_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.project.course, 1)
        self.client.force_authenticate(staff)
        response = self.client.post(
            reverse('all-submission-scores-task', kwargs={'pk': self.project.pk}))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        response = self.client.post(
            reverse('ultimate-submission-scores-task', kwargs={'pk': self.project.pk}))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_unfinished_and_error_submissions_ignored(self):
        self.client.force_authenticate(self.admin)

        student_group3 = obj_build.make_group(num_members=1, project=self.project)

        received = obj_build.make_submission(group=self.student_group1)
        received.status = ag_models.Submission.GradingStatus.received
        received.save()

        queued = obj_build.make_submission(group=self.student_group2)
        queued.status = ag_models.Submission.GradingStatus.queued
        queued.save()

        being_graded = obj_build.make_submission(group=student_group3)
        being_graded.status = ag_models.Submission.GradingStatus.being_graded
        being_graded.save()

        waiting_for_deferred = obj_build.make_submission(group=self.student_group2)
        waiting_for_deferred.status = ag_models.Submission.GradingStatus.waiting_for_deferred
        waiting_for_deferred.save()

        error = obj_build.make_submission(group=self.student_group2)
        error.status = ag_models.Submission.GradingStatus.error
        error.save()

        self.project.validate_and_update(
            ultimate_submission_policy=ag_models.UltimateSubmissionPolicy.most_recent)
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)
        self.do_download_scores_test(
            reverse('all-submission-scores-task', kwargs={'pk': self.project.pk}),
            self.project,
            [self.group1_submission1_best, self.group1_submission2, self.group2_only_submission])

    def do_download_scores_test(self, url, project: ag_models.Project,
                                expected_submissions: Iterator[ag_models.Submission]):
        # Intentionally reversing the ag and mutation test suite ordering as an
        # extra check that we get the ag and mutation test suite results in the right order.
        project.set_agtestsuite_order(project.get_agtestsuite_order()[::-1])
        project.set_mutationtestsuite_order(project.get_mutationtestsuite_order()[::-1])

        self.client.force_authenticate(self.admin)

        response = self.client.post(url)
        self.assertEqual(status.HTTP_202_ACCEPTED, response.status_code)

        # Check the content directly from the filesystem
        task = ag_models.DownloadTask.objects.get(pk=response.data['pk'])

        self.assertEqual(100, task.progress)
        self.assertEqual('', task.error_msg)

        with open(task.result_filename) as f:
            actual_result = list(csv.DictReader(f))
        expected_result = self._get_expected_csv(expected_submissions, project)
        self.assertCountEqual(expected_result, actual_result)

        # Check the content returned by the result endpoint
        result_content_url = reverse('download-task-result', kwargs={'pk': task.pk})
        response = self.client.get(result_content_url)
        _check_csv_response(self, response, expected_result)

        # Make sure that other admin users can request results for downloads
        # they didn't start.
        [other_admin] = obj_build.make_admin_users(project.course, 1)
        self.client.force_authenticate(other_admin)
        response = self.client.get(result_content_url)
        _check_csv_response(self, response, expected_result)

    def _get_expected_csv(self, expected_submissions, project):
        expected_headers = ['Username {}'.format(i + 1) for i in range(project.max_group_size)]
        expected_headers.append('Timestamp')
        expected_headers += ['Total', 'Total Possible']
        for suite in project.ag_test_suites.all():
            expected_headers += ['{} Total'.format(suite.name),
                                 '{} Total Possible'.format(suite.name)]
            for case in suite.ag_test_cases.all():
                expected_headers.append('{} - {}'.format(suite.name, case.name))

        for suite in project.mutation_test_suites.all():
            expected_headers += ['{} Total'.format(suite.name),
                                 '{} Total Possible'.format(suite.name)]

        expected_result = []
        for submission in expected_submissions:
            values = []
            user_padding_len = project.max_group_size - submission.group.members.count()
            usernames = itertools.chain(sorted(submission.group.member_names),
                                        itertools.repeat('', user_padding_len))
            values += list(usernames)
            values.append(submission.timestamp.isoformat())

            fdbk = get_submission_fdbk(submission, ag_models.FeedbackCategory.max)
            values += [str(fdbk.total_points), str(fdbk.total_points_possible)]
            for suite_fdbk in fdbk.ag_test_suite_results:
                values += [str(suite_fdbk.total_points), str(suite_fdbk.total_points_possible)]
                for case_fdbk in suite_fdbk.ag_test_case_results:
                    values.append(str(case_fdbk.total_points))

            for suite_result in fdbk.mutation_test_suite_results:
                suite_fdbk = suite_result.get_fdbk(
                    ag_models.FeedbackCategory.max, MutationTestSuitePreLoader(self.project))
                values += [str(suite_fdbk.total_points), str(suite_fdbk.total_points_possible)]

            self.assertEqual(len(expected_headers), len(values))
            expected_result.append(dict(zip(expected_headers, values)))

        return expected_result


def _check_csv_response(test_fixture: UnitTestBase, response, expected_rows):
    test_fixture.assertEqual(status.HTTP_200_OK, response.status_code)
    test_fixture.assertEqual('text/csv', response['Content-Type'])

    with tempfile.TemporaryFile('w+') as result:
        result.write(''.join((chunk.decode() for chunk in response.streaming_content)))
        result.seek(0)
        test_fixture.assertCountEqual(expected_rows, list(csv.DictReader(result)))
