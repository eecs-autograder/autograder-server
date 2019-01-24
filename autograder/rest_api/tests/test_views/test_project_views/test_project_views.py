import tempfile
from typing import Optional
from unittest import mock

from django.core import exceptions
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.rest_api.tests.test_views.ag_view_test_base import AGViewTestBase
from autograder.utils import exclude_dict
from autograder.utils.testing import UnitTestBase


class ListProjectsTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()

        self.hidden_project = obj_build.make_project()
        self.course = self.hidden_project.course
        self.visible_project = obj_build.make_project(course=self.course, visible_to_students=True)
        self.all_projects = [self.hidden_project, self.visible_project]

        self.client = APIClient()
        self.url = reverse('projects', kwargs={'pk': self.course.pk})

    def test_admin_list_projects(self):
        admin = obj_build.make_admin_user(self.course)
        self.do_valid_list_projects_test(
            admin, self.all_projects, show_closing_time=True, show_instructor_files=True)

    def test_staff_list_projects(self):
        staff = obj_build.make_staff_user(self.course)
        self.do_valid_list_projects_test(staff, self.all_projects, show_instructor_files=True)

    def test_student_list_projects_visible_only(self):
        student = obj_build.make_student_user(self.course)
        self.do_valid_list_projects_test(student, [self.visible_project])

    def test_handgrader_list_all_projects(self):
        handgrader = obj_build.make_handgrader_user(self.course)
        self.do_valid_list_projects_test(handgrader, self.all_projects)

    def test_other_list_projects_permission_denied(self):
        guest = obj_build.make_user()
        self.do_permission_denied_get_test(self.client, guest, self.url)

    def do_valid_list_projects_test(self, user, expected_projects,
                                    *, show_closing_time: bool=False,
                                    show_instructor_files: bool=False):
        expected_data = []
        for project in expected_projects:
            proj_dict = project.to_dict()
            if not show_closing_time:
                proj_dict.pop('closing_time', None)

            if not show_instructor_files:
                proj_dict.pop('instructor_files', None)

            expected_data.append(proj_dict)

        self.client.force_authenticate(user)
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertCountEqual(expected_data, response.data)


class CreateProjectTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.course = obj_build.make_course()
        self.url = reverse('projects', kwargs={'pk': self.course.pk})

    def test_course_admin_add_project(self):
        admin = obj_build.make_admin_user(self.course)
        args = {'name': 'spam project',
                'min_group_size': 2,
                'max_group_size': 3}
        self.client.force_authenticate(admin)
        response = self.client.post(self.url, args)

        # Regression check: closing_time and instructor_files should be present
        # https://github.com/eecs-autograder/autograder-server/issues/390
        self.assertIn('closing_time', response.data)
        self.assertIn('instructor_files', response.data)

        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        new_project = self.course.projects.get(name=args['name'])
        for arg_name, value in args.items():
            self.assertEqual(value, getattr(new_project, arg_name), msg=arg_name)

    def test_other_add_project_permission_denied(self):
        staff = obj_build.make_staff_user(self.course)
        student = obj_build.make_student_user(self.course)
        handgrader = obj_build.make_handgrader_user(self.course)
        guest = obj_build.make_user()
        project_name = 'project123'
        for user in staff, student, handgrader, guest:
            self.client.force_authenticate(user)
            response = self.client.post(self.url, {'name': project_name})

            self.assertEqual(403, response.status_code)

            with self.assertRaises(exceptions.ObjectDoesNotExist):
                ag_models.Project.objects.get(name=project_name)


class CopyProjectViewTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.client = APIClient()
        self.project = obj_build.make_project()
        self.admin = obj_build.make_admin_user(self.project.course)

        self.other_course = obj_build.make_course()
        self.other_course.admins.add(self.admin)

    def test_admin_copy_project_to_same_course_with_new_name(self):
        self.client.force_authenticate(self.admin)
        new_name = 'New Project'
        response = self.client.post(self.get_url(self.project, self.project.course, new_name))
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        # Regression check: closing_time and instructor_files should be present
        # https://github.com/eecs-autograder/autograder-server/issues/390
        self.assertIn('closing_time', response.data)
        self.assertIn('instructor_files', response.data)

        new_project = ag_models.Project.objects.get(pk=response.data['pk'])
        self.assertEqual(new_name, new_project.name)
        self.assertEqual(self.project.course, new_project.course)

    def test_admin_copy_project_to_different_course_they_are_admin_for(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.get_url(self.project, self.other_course))
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        new_project = ag_models.Project.objects.get(pk=response.data['pk'])
        self.assertEqual(self.project.name, new_project.name)
        self.assertEqual(self.other_course, new_project.course)

    def test_admin_copy_project_to_different_course_with_different_name(self):
        self.client.force_authenticate(self.admin)
        new_name = 'New Project'
        response = self.client.post(self.get_url(self.project, self.other_course, new_name))
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        new_project = ag_models.Project.objects.get(pk=response.data['pk'])
        self.assertEqual(new_name, new_project.name)
        self.assertEqual(self.other_course, new_project.course)

    def test_view_calls_copy_project(self):
        dummy_project = obj_build.make_project(self.other_course)
        mock_copy_project = mock.Mock(return_value=dummy_project)
        with mock.patch('autograder.rest_api.views.project_views.project_views.copy_project',
                        new=mock_copy_project):
            self.client.force_authenticate(self.admin)
            response = self.client.post(self.get_url(self.project, self.other_course))

            mock_copy_project.assert_called_once_with(
                project=self.project, target_course=self.other_course, new_project_name=None)

    def test_non_admin_copy_project_permission_denied(self):
        staff = obj_build.make_staff_user(self.project.course)
        self.client.force_authenticate(staff)
        response = self.client.post(self.get_url(self.project, self.project.course, 'New project'))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_admin_copy_project_to_course_they_arent_admin_for_permission_denied(self):
        self.other_course.admins.remove(self.admin)

        self.client.force_authenticate(self.admin)
        response = self.client.post(self.get_url(self.project, self.other_course))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_error_same_course_same_project_name(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.get_url(self.project, self.project.course))
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_error_new_project_name_empty(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.get_url(self.project, self.project.course, ''))
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def get_url(self, project: ag_models.Project,
                target_course: ag_models.Course, new_name: Optional[str]=None):
        url = reverse('copy-project',
                      kwargs={'project_pk': project.pk, 'target_course_pk': target_course.pk})
        if new_name is not None:
            url += f'?new_project_name={new_name}'

        return url


class RetrieveProjectTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.project = obj_build.make_project()
        self.course = self.project.course
        self.url = reverse('project-detail', kwargs={'pk': self.project.pk})

    def test_admin_get_project(self):
        self.assertFalse(self.project.visible_to_students)
        admin = obj_build.make_admin_user(self.course)
        self.do_get_object_test(self.client, admin, self.url, self.project.to_dict())

    def test_staff_get_project(self):
        self.assertFalse(self.project.visible_to_students)
        staff = obj_build.make_staff_user(self.course)
        # closing_time is only shown to admins.
        self.do_get_object_test(self.client, staff, self.url,
                                exclude_dict(self.project.to_dict(), ['closing_time']))

    def test_handgrader_get_project(self):
        self.assertFalse(self.project.visible_to_students)
        handgrader = obj_build.make_handgrader_user(self.course)
        # closing_time is only shown to admins.
        self.do_get_object_test(
            self.client, handgrader, self.url,
            exclude_dict(self.project.to_dict(), ['closing_time', 'instructor_files']))

    def test_student_get_visible_project(self):
        self.project.validate_and_update(visible_to_students=True)
        student = obj_build.make_student_user(self.course)
        # closing_time is only shown to admins.
        self.do_get_object_test(
            self.client, student, self.url,
            exclude_dict(self.project.to_dict(), ['closing_time', 'instructor_files']))

    def test_student_get_hidden_project_permission_denied(self):
        student = obj_build.make_student_user(self.course)
        self.do_permission_denied_get_test(self.client, student, self.url)

    def test_guest_get_project_any_domain(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        guest = obj_build.make_user()
        self.do_get_object_test(
            self.client, guest, self.url,
            exclude_dict(self.project.to_dict(), ['closing_time', 'instructor_files']))

    def test_guest_get_project_right_domain(self):
        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        guest = obj_build.make_allowed_domain_guest_user(self.course)
        self.do_get_object_test(
            self.client, guest, self.url,
            exclude_dict(self.project.to_dict(), ['closing_time', 'instructor_files']))

    def test_guest_wrong_domain_get_project_permission_denied(self):
        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        guest = obj_build.make_user()
        self.do_permission_denied_get_test(self.client, guest, self.url)

    def test_guest_get_visible_no_guests_allowed_project_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=False)
        guest = obj_build.make_user()
        self.do_permission_denied_get_test(self.client, guest, self.url)

    def test_guest_get_guest_allowed_hidden_project_permission_denied(self):
        self.project.validate_and_update(visible_to_students=False, guests_can_submit=True)
        guest = obj_build.make_user()
        self.do_permission_denied_get_test(self.client, guest, self.url)


class UpdateProjectTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()
        self.course = self.project.course
        self.url = reverse('project-detail', kwargs={'pk': self.project.pk})
        self.client = APIClient()

    def test_admin_edit_project(self):
        request_data = {
            'name': self.project.name + 'waaaaa',
            'min_group_size': 3,
            'max_group_size': 5
        }

        admin = obj_build.make_admin_user(self.course)
        self.do_patch_object_test(self.project, self.client, admin, self.url, request_data)

    def test_edit_project_invalid_settings(self):
        request_data = {
            'min_group_size': 2,
            'max_group_size': 1
        }

        admin = obj_build.make_admin_user(self.course)
        self.do_patch_object_invalid_args_test(
            self.project, self.client, admin, self.url, request_data)

    def test_non_admin_edit_project_permission_denied(self):
        staff = obj_build.make_staff_user(self.course)
        self.do_patch_object_permission_denied_test(
            self.project, self.client, staff, self.url, {'name': 'waaaaaaaaluigi'})


class NumQueuedSubmissionsTestCase(UnitTestBase):
    def test_get_num_queued_submissions(self):
        client = APIClient()

        course = obj_build.make_course()
        admin = obj_build.make_admin_user(course)
        proj_kwargs = {
            'visible_to_students': True,
            'guests_can_submit': True
        }
        no_submits = obj_build.make_project(course, **proj_kwargs)
        with_submits1 = obj_build.make_project(course, **proj_kwargs)
        with_submits2 = obj_build.make_project(course, **proj_kwargs)

        group_with_submits1 = obj_build.make_group(project=with_submits1)
        group_with_submits2 = obj_build.make_group(project=with_submits2)

        g1_statuses = [ag_models.Submission.GradingStatus.queued,
                       ag_models.Submission.GradingStatus.finished_grading,
                       ag_models.Submission.GradingStatus.removed_from_queue,
                       ag_models.Submission.GradingStatus.received,
                       ag_models.Submission.GradingStatus.being_graded,
                       ag_models.Submission.GradingStatus.error]

        for grading_status in g1_statuses:
            obj_build.make_submission(
                status=grading_status,
                group=group_with_submits1)

        for i in range(3):
            obj_build.make_submission(
                status=ag_models.Submission.GradingStatus.queued,
                group=group_with_submits2)

        client.force_authenticate(admin)
        response = client.get(
            reverse('project-num-queued-submissions',
                    kwargs={'pk': no_submits.pk}))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(0, response.data)

        response = client.get(
            reverse('project-num-queued-submissions',
                    kwargs={'pk': with_submits1.pk}))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(1, response.data)

        response = client.get(
            reverse('project-num-queued-submissions',
                    kwargs={'pk': with_submits2.pk}))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(3, response.data)


# Note: Creating and running a download task is tested in
# autograder/rest_api/tests/test_views/test_tasks/test_project_downloads.py
class DownloadTaskEndpointsTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()
        self.client = APIClient()

    def test_list_project_download_tasks(self):
        # All admins should be able to see all download tasks.
        user1, user2 = obj_build.make_admin_users(self.project.course, 2)

        task1 = ag_models.DownloadTask.objects.validate_and_create(
            project=self.project,
            creator=user1, download_type=ag_models.DownloadType.all_scores)
        task2 = ag_models.DownloadTask.objects.validate_and_create(
            project=self.project,
            creator=user2, download_type=ag_models.DownloadType.final_graded_submission_files)

        other_project = obj_build.build_project()
        ag_models.DownloadTask.objects.validate_and_create(
            project=other_project,
            creator=obj_build.make_admin_users(self.project.course, 1)[0],
            download_type=ag_models.DownloadType.all_scores)

        url = reverse('project-download-tasks', kwargs={'pk': self.project.pk})
        self.client.force_authenticate(user1)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertCountEqual([task1.to_dict(), task2.to_dict()], response.data)

    def test_non_admin_list_project_download_tasks_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.project.course, 1)
        [handgrader] = obj_build.make_handgrader_users(self.project.course, 1)

        url = reverse('project-download-tasks', kwargs={'pk': self.project.pk})
        for user in staff, handgrader:
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

    def test_invalid_get_in_progress_download_task_result(self):
        [user] = obj_build.make_admin_users(self.project.course, 1)

        in_progress_task = ag_models.DownloadTask.objects.validate_and_create(
            project=self.project,
            creator=user, download_type=ag_models.DownloadType.all_scores)

        url = reverse('download_tasks-result', kwargs={'pk': in_progress_task.pk})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(in_progress_task.progress, response.data['in_progress'])

    def test_error_get_download_task_result_task_errored(self):
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

    def test_non_admin_get_download_task_result_permission_denied(self):
        [admin] = obj_build.make_admin_users(self.project.course, 1)
        [staff] = obj_build.make_staff_users(self.project.course, 1)

        task = ag_models.DownloadTask.objects.validate_and_create(
            project=self.project,
            creator=admin, download_type=ag_models.DownloadType.all_scores,
            progress=100)

        url = reverse('download_tasks-result', kwargs={'pk': task.pk})
        self.client.force_authenticate(staff)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class EditBonusSubmissionsViewTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.initial_num_bonus_submissions = 10
        self.project = obj_build.make_project(
            num_bonus_submissions=self.initial_num_bonus_submissions)

        self.groups = [obj_build.make_group(project=self.project) for i in range(5)]

        # Make sure bonus submissions are only changed for self.project
        self.other_project = obj_build.make_project(course=self.project.course,
                                                    num_bonus_submissions=3)
        self.other_groups = [obj_build.make_group(project=self.other_project) for i in range(5)]

        self.admin = obj_build.make_admin_user(self.project.course)
        self.url = reverse('edit-bonus-submissions', kwargs={'project_pk': self.project.pk})
        self.client = APIClient()

    def test_add_bonus_submissions(self):
        to_add = 4

        self.client.force_authenticate(self.admin)
        response = self.client.patch(self.url, {'add': to_add})
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

        self._check_bonus_submissions(self.initial_num_bonus_submissions + to_add)

    def test_add_bonus_submissions_one_group_only(self):
        to_add = 1

        new_group = obj_build.make_group(project=self.project)
        url = self.url + f'?group_pk={new_group.pk}'

        self.client.force_authenticate(self.admin)
        response = self.client.patch(url, {'add': to_add})
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

        new_group.refresh_from_db()
        self.assertEqual(self.initial_num_bonus_submissions + to_add,
                         new_group.bonus_submissions_remaining)

        self._check_bonus_submissions(self.initial_num_bonus_submissions)

    def test_subtract_bonus_submissions(self):
        to_subtract = 2

        self.client.force_authenticate(self.admin)
        response = self.client.patch(self.url, {'subtract': to_subtract})
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

        self._check_bonus_submissions(self.initial_num_bonus_submissions - to_subtract)

    def test_subtract_bonus_submissions_one_group_only(self):
        to_subtract = 5

        new_group = obj_build.make_group(project=self.project)
        url = self.url + f'?group_pk={new_group.pk}'

        self.client.force_authenticate(self.admin)
        response = self.client.patch(url, {'subtract': to_subtract})
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

        new_group.refresh_from_db()
        self.assertEqual(self.initial_num_bonus_submissions - to_subtract,
                         new_group.bonus_submissions_remaining)

        self._check_bonus_submissions(self.initial_num_bonus_submissions)

    def test_non_admin_permission_denied(self):
        staff = obj_build.make_staff_user(course=self.project.course)
        self.client.force_authenticate(staff)

        response = self.client.patch(self.url, {'add': 42})
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        response = self.client.patch(self.url, {'subtract': 42})
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        self._check_bonus_submissions(self.initial_num_bonus_submissions)

    def test_too_many_options_chosen_bad_request(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(self.url, {'add': 2, 'subtract': 1})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self._check_bonus_submissions(self.initial_num_bonus_submissions)

    def test_no_options_bad_request(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(self.url, {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self._check_bonus_submissions(self.initial_num_bonus_submissions)

    def _check_bonus_submissions(self, expected_num_bonus_submissions: int):
        for group in self.groups:
            group.refresh_from_db()
            self.assertEqual(expected_num_bonus_submissions, group.bonus_submissions_remaining)

        for group in self.other_groups:
            group.refresh_from_db()

            self.assertEqual(self.other_project.num_bonus_submissions,
                             group.bonus_submissions_remaining)
