import os
import tempfile
import zipfile

import io
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


class DownloadSubmissionFilesTestCase(test_data.Client, UnitTestBase):
    def setUp(self):
        super().setUp()
        self.files = [
            SimpleUploadedFile('file1.txt', b'adsfadslkfajsdkfj'),
            SimpleUploadedFile('file2.txt', b'asdqeirueinfaksdnfaadf'),
            SimpleUploadedFile('file3.txt', b'cmxcnajsddhadf')
        ]

        self.files_by_name = dict(zip([file_.name for file_ in self.files], self.files))

        self.project = obj_build.make_project(visible_to_students=True)
        ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            project=self.project, pattern='*', max_num_matches=3)
        self.student_group1 = obj_build.make_group(project=self.project)
        self.group1_submission1 = obj_build.build_submission(submitted_files=self.files[:1],
                                                             submission_group=self.student_group1)
        self.group1_submission2 = obj_build.build_submission(submitted_files=self.files[:2],
                                                             submission_group=self.student_group1)

        self.student_group2 = obj_build.make_group(num_members=3, project=self.project)
        self.group2_submission1 = obj_build.build_submission(submitted_files=self.files[-1:],
                                                             submission_group=self.student_group2)

        self.staff_group = obj_build.make_group(members_role=ag_models.UserRole.staff)
        self.staff_submission1 = obj_build.build_submission(submitted_files=self.files,
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
        self.do_download_submissions_test(
            url, [self.group1_submission1, self.group1_submission2,
                  self.group2_submission1, self.staff_submission1])

    def test_ultimate_submission_files_include_staff(self):
        url = reverse('project-ultimate-submission-files', kwargs={'pk': self.project.pk})
        staff_submission2 = obj_build.build_submission(submitted_files=self.files[:-1],
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

    def do_download_submissions_test(self, url, expected_submissions):
        self.client.force_authenticate(self.admin)

        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        expected_filenames = []
        for submission in expected_submissions:
            for filename in submission.submitted_filenames:
                expected_filenames.append(
                    '{}_{}/{}-{}/{}'.format(
                        self.project.course.name, self.project.name,
                        '_'.join(sorted(submission.submission_group.member_names)),
                        submission.timestamp.isoformat(), filename))

        result = io.BytesIO(b''.join(response.streaming_content))
        with zipfile.ZipFile(result) as z:
            self.assertCountEqual(expected_filenames, [info.filename for info in z.infolist()])
            for info in z.infolist():
                with z.open(info.filename) as f:
                    expected_file = self.files_by_name[os.path.basename(info.filename)]
                    expected_file.open()
                    self.assertEqual(expected_file.read(), f.read())


class DownloadGradesTestCase(test_data.Client, UnitTestBase):
    def test_download_all_scores(self):
        self.fail()

    def test_download_ultimate_submission_scores(self):
        self.fail()

    def test_include_staff(self):
        self.fail()

    def test_non_admin_permission_denied():
        self.fail()
