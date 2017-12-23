import csv
import os
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


@mock.patch(
    'autograder.rest_api.tasks.project_downloads._PROGRESS_UPDATE_FREQUENCY',
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
    'autograder.rest_api.tasks.project_downloads._PROGRESS_UPDATE_FREQUENCY',
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

        self.student_suite1_bugs = ['suite1_bug{}'.format(i) for i in range(3)]
        self.student_suite1 = obj_build.make_student_test_suite(
            project=self.project, buggy_impl_names=self.student_suite1_bugs)

        self.student_suite2_bugs = ['suite2_bug{}'.format(i) for i in range(5)]
        self.student_suite2 = obj_build.make_student_test_suite(
            project=self.project, buggy_impl_names=self.student_suite2_bugs)

        self.student_group1 = obj_build.make_group(project=self.project)
        self.group1_submission1_best = obj_build.build_finished_submission(
            submission_group=self.student_group1)
        obj_build.make_correct_ag_test_command_result(self.suite1_cmd,
                                                      submission=self.group1_submission1_best)
        obj_build.make_correct_ag_test_command_result(self.suite2_cmd,
                                                      submission=self.group1_submission1_best)
        ag_models.StudentTestSuiteResult.objects.validate_and_create(
            student_test_suite=self.student_suite1,
            submission=self.group1_submission1_best,
            bugs_exposed=self.student_suite1_bugs)
        ag_models.StudentTestSuiteResult.objects.validate_and_create(
            student_test_suite=self.student_suite2,
            submission=self.group1_submission1_best,
            bugs_exposed=self.student_suite2_bugs)
        self.group1_submission2 = obj_build.build_finished_submission(
            submission_group=self.student_group1)
        obj_build.make_correct_ag_test_command_result(self.suite1_cmd,
                                                      submission=self.group1_submission2)
        obj_build.make_incorrect_ag_test_command_result(self.suite2_cmd,
                                                        submission=self.group1_submission2)
        ag_models.StudentTestSuiteResult.objects.validate_and_create(
            student_test_suite=self.student_suite1,
            submission=self.group1_submission2,
            bugs_exposed=[])
        ag_models.StudentTestSuiteResult.objects.validate_and_create(
            student_test_suite=self.student_suite2,
            submission=self.group1_submission2,
            bugs_exposed=[])

        self.student_group2 = obj_build.make_group(num_members=max_group_size,
                                                   project=self.project)
        self.group2_only_submission = obj_build.build_finished_submission(
            submission_group=self.student_group2)
        obj_build.make_incorrect_ag_test_command_result(self.suite1_cmd,
                                                        submission=self.group2_only_submission)
        obj_build.make_incorrect_ag_test_command_result(self.suite2_cmd,
                                                        submission=self.group2_only_submission)
        ag_models.StudentTestSuiteResult.objects.validate_and_create(
            student_test_suite=self.student_suite1,
            submission=self.group2_only_submission,
            bugs_exposed=self.student_suite1_bugs[:-1])
        ag_models.StudentTestSuiteResult.objects.validate_and_create(
            student_test_suite=self.student_suite2,
            submission=self.group2_only_submission,
            bugs_exposed=self.student_suite2_bugs[:-1])

        self.staff_group = obj_build.make_group(project=self.project,
                                                members_role=ag_models.UserRole.staff)
        self.staff_submission1 = obj_build.build_finished_submission(
            submission_group=self.staff_group)
        obj_build.make_correct_ag_test_command_result(self.suite1_cmd,
                                                      submission=self.staff_submission1)
        obj_build.make_correct_ag_test_command_result(self.suite2_cmd,
                                                      submission=self.staff_submission1)
        ag_models.StudentTestSuiteResult.objects.validate_and_create(
            student_test_suite=self.student_suite1,
            submission=self.staff_submission1,
            bugs_exposed=self.student_suite1_bugs[:-1])
        ag_models.StudentTestSuiteResult.objects.validate_and_create(
            student_test_suite=self.student_suite2,
            submission=self.staff_submission1,
            bugs_exposed=self.student_suite2_bugs)

        self.no_submissions_group = obj_build.make_group(project=self.project)

        [self.admin] = obj_build.make_admin_users(self.project.course, 1)

        self.maxDiff = None

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
        # Intentionally reversing the ag and student test suite ordering as an
        # extra check that we get the ag and student test suite results in the right order.
        project.set_agtestsuite_order(project.get_agtestsuite_order()[::-1])
        project.set_studenttestsuite_order(project.get_studenttestsuite_order()[::-1])

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

        for suite in project.student_test_suites.all():
            expected_headers += ['{} Total'.format(suite.name),
                                 '{} Total Possible'.format(suite.name)]

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

            for suite_result in fdbk.student_test_suite_results:
                suite_fdbk = suite_result.get_fdbk(ag_models.FeedbackCategory.max)
                values += [str(suite_fdbk.total_points), str(suite_fdbk.total_points_possible)]

            self.assertEqual(len(expected_headers), len(values))
            expected_result.append(dict(zip(expected_headers, values)))

        task = ag_models.DownloadTask.objects.get(pk=response.data['pk'])
        self.assertEqual(100, task.progress)
        self.assertEqual('', task.error_msg)
        with open(task.result_filename) as f:
            actual_result = list(csv.DictReader(f))
        self.assertCountEqual(expected_result, actual_result)
