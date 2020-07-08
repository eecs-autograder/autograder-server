import tempfile
from typing import Optional
from unittest import mock

from django.core import exceptions
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.handgrading.models as hg_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.rest_api.signals import on_project_created
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
        self.url = reverse('list-create-projects', kwargs={'pk': self.course.pk})

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

    def test_admin_plus_student_sees_all_projects(self) -> None:
        self.maxDiff = None
        student = obj_build.make_student_user(self.course)
        self.course.admins.add(student)
        self.do_valid_list_projects_test(
            student, self.all_projects, show_closing_time=True, show_instructor_files=True)

    def test_staff_plus_student_sees_all_projects(self) -> None:
        self.maxDiff = None
        student = obj_build.make_student_user(self.course)
        self.course.staff.add(student)
        self.do_valid_list_projects_test(student, self.all_projects, show_instructor_files=True)

    def test_handgrader_plus_student_sees_all_projects(self) -> None:
        self.maxDiff = None
        student = obj_build.make_student_user(self.course)
        self.course.handgraders.add(student)
        self.do_valid_list_projects_test(student, self.all_projects)

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
        self.url = reverse('list-create-projects', kwargs={'pk': self.course.pk})

    def test_course_admin_add_project(self):
        post_save.connect(on_project_created, sender=ag_models.Project)
        path = 'autograder.rest_api.signals.register_project_queues'
        with mock.patch(path) as mock_register_queues:
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

            mock_register_queues.apply_async.assert_called_once_with(
                kwargs={'project_pks': [new_project.pk]}, queue=mock.ANY, connection=mock.ANY
            )

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


class DeleteProjectTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()
        self.course = self.project.course
        self.url = reverse('project-detail', kwargs={'pk': self.project.pk})
        self.client = APIClient()
        self.admin = obj_build.make_admin_user(self.course)

    def test_error_project_still_has_ag_test_suites(self) -> None:
        ag_models.AGTestSuite.objects.validate_and_create(project=self.project, name='noreastnor')
        self.client.force_authenticate(self.admin)
        response = self.client.delete(self.url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.project.refresh_from_db()

    def test_error_project_still_has_mutation_test_suites(self) -> None:
        ag_models.MutationTestSuite.objects.validate_and_create(project=self.project, name='oiea')
        self.client.force_authenticate(self.admin)
        response = self.client.delete(self.url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.project.refresh_from_db()

    def test_delete_project(self) -> None:
        self.client.force_authenticate(self.admin)
        response = self.client.delete(self.url)
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

        with self.assertRaises(ObjectDoesNotExist):
            self.project.refresh_from_db()

    def test_non_admin_delete_project_permission_denied(self) -> None:
        self.do_delete_object_permission_denied_test(
            self.project, self.client, obj_build.make_staff_user(self.course), self.url)


class CopyProjectViewTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.project = obj_build.make_project()
        self.admin = obj_build.make_admin_user(self.project.course)

        self.other_course = obj_build.make_course()
        self.other_course.admins.add(self.admin)

    def test_admin_copy_project_to_same_course_with_new_name(self):
        post_save.connect(on_project_created, sender=ag_models.Project)
        path = 'autograder.rest_api.signals.register_project_queues'
        with mock.patch(path) as mock_register_queues:
            self.client.force_authenticate(self.admin)
            new_name = 'New Project'
            response = self.send_copy_request(self.project, self.project.course, new_name)
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)

            # Regression check: closing_time and instructor_files should be present
            # https://github.com/eecs-autograder/autograder-server/issues/390
            self.assertIn('closing_time', response.data)
            self.assertIn('instructor_files', response.data)

            new_project = ag_models.Project.objects.get(pk=response.data['pk'])
            self.assertEqual(new_name, new_project.name)
            self.assertEqual(self.project.course, new_project.course)

            mock_register_queues.apply_async.assert_called_once_with(
                kwargs={'project_pks': [new_project.pk]}, queue=mock.ANY, connection=mock.ANY
            )

    def test_admin_copy_project_to_different_course_they_are_admin_for(self):
        self.client.force_authenticate(self.admin)
        response = self.send_copy_request(self.project, self.other_course)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        new_project = ag_models.Project.objects.get(pk=response.data['pk'])
        self.assertEqual(self.project.name, new_project.name)
        self.assertEqual(self.other_course, new_project.course)

    def test_admin_copy_project_to_different_course_with_different_name(self):
        self.client.force_authenticate(self.admin)
        new_name = 'New Project'
        response = self.send_copy_request(self.project, self.other_course, new_name)
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
            response = self.send_copy_request(self.project, self.other_course)

            mock_copy_project.assert_called_once_with(
                project=self.project, target_course=self.other_course, new_project_name=None)

    def test_non_admin_copy_project_permission_denied(self):
        staff = obj_build.make_staff_user(self.project.course)
        self.client.force_authenticate(staff)
        response = self.send_copy_request(self.project, self.project.course, 'New project')
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_admin_copy_project_to_course_they_arent_admin_for_permission_denied(self):
        self.other_course.admins.remove(self.admin)

        self.client.force_authenticate(self.admin)
        response = self.send_copy_request(self.project, self.other_course)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_error_same_course_same_project_name(self):
        self.client.force_authenticate(self.admin)
        response = self.send_copy_request(self.project, self.project.course)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_error_new_project_name_empty(self):
        self.client.force_authenticate(self.admin)
        response = self.send_copy_request(self.project, self.project.course, '')
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def send_copy_request(
        self, project: ag_models.Project,
        target_course: ag_models.Course,
        new_name: Optional[str]=None
    ):
        url = reverse(
            'copy-project',
            kwargs={'project_pk': project.pk, 'target_course_pk': target_course.pk}
        )
        body = {}
        if new_name is not None:
            body['new_project_name'] = new_name

        return self.client.post(url, body)


class ImportHandgradingRubricTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()

        self.import_to = obj_build.make_project()
        self.course = self.import_to.course
        self.import_from = obj_build.make_project(self.course)
        hg_models.HandgradingRubric.objects.validate_and_create(project=self.import_from)

        self.client = APIClient()
        self.admin = obj_build.make_admin_user(self.course)

    def test_import_from_project_in_same_course(self):
        self.assertFalse(hasattr(self.import_to, 'handgrading_rubric'))
        url = reverse('import-handgrading-rubric',
                      kwargs={'project_pk': self.import_to.pk,
                              'import_from_project_pk': self.import_from.pk})
        self.client.force_authenticate(self.admin)
        response = self.client.post(url)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.import_to.refresh_from_db()
        self.assertEqual(self.import_to.handgrading_rubric.to_dict(), response.data)

        self.import_to.refresh_from_db()

        self.assertTrue(hasattr(self.import_to, 'handgrading_rubric'))

        self.assertNotEqual(self.import_to.handgrading_rubric.pk,
                            self.import_from.handgrading_rubric.pk)

    def test_import_from_project_in_other_course_is_admin_for(self):
        other_project = obj_build.make_project()
        other_project.course.admins.add(self.admin)
        hg_models.HandgradingRubric.objects.validate_and_create(project=other_project)

        url = reverse('import-handgrading-rubric',
                      kwargs={'project_pk': self.import_to.pk,
                              'import_from_project_pk': other_project.pk})
        self.client.force_authenticate(self.admin)
        response = self.client.post(url)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.import_to.refresh_from_db()
        self.assertEqual(self.import_to.handgrading_rubric.to_dict(), response.data)

        self.import_to.refresh_from_db()

        self.assertTrue(hasattr(self.import_to, 'handgrading_rubric'))

        self.assertNotEqual(self.import_to.handgrading_rubric.pk,
                            self.import_from.handgrading_rubric.pk)

    def test_view_calls_import_handgrading_rubric(self):
        mock_import_rubric_path = ('autograder.rest_api.views.project_views'
                                   '.project_views.import_handgrading_rubric')

        def _create_rubric(*args, **kwargs):
            hg_models.HandgradingRubric.objects.validate_and_create(project=self.import_to)

        mock_import_rubric = mock.Mock(side_effect=_create_rubric)
        with mock.patch(mock_import_rubric_path, new=mock_import_rubric):
            url = reverse('import-handgrading-rubric',
                          kwargs={'project_pk': self.import_to.pk,
                                  'import_from_project_pk': self.import_from.pk})
            self.client.force_authenticate(self.admin)

            response = self.client.post(url)
            self.assertEqual(status.HTTP_201_CREATED, response.status_code)

            mock_import_rubric.assert_called_once_with(
                import_to=self.import_to, import_from=self.import_from)

    def test_import_from_project_in_different_course_not_admin_for_permission_denied(self):
        other_project = obj_build.make_project()

        url = reverse('import-handgrading-rubric',
                      kwargs={'project_pk': self.import_to.pk,
                              'import_from_project_pk': other_project.pk})
        self.client.force_authenticate(self.admin)
        self.assertFalse(other_project.course.is_admin(self.admin))
        response = self.client.post(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        self.import_to.refresh_from_db()

        self.assertFalse(hasattr(self.import_to, 'handgrading_rubric'))

    def test_400_import_from_has_no_handgrading_rubric(self):
        self.import_from.handgrading_rubric.delete()

        url = reverse('import-handgrading-rubric',
                      kwargs={'project_pk': self.import_to.pk,
                              'import_from_project_pk': self.import_from.pk})
        self.client.force_authenticate(self.admin)
        response = self.client.post(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(f'The project "{self.import_from.name}" has no handgrading rubric',
                         response.data)

    def test_non_admin_permission_denied(self):
        staff = obj_build.make_staff_user(self.course)
        self.client.force_authenticate(staff)

        url = reverse('import-handgrading-rubric',
                      kwargs={'project_pk': self.import_to.pk,
                              'import_from_project_pk': self.import_from.pk})
        response = self.client.post(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_404_import_from_project_does_not_exist(self):
        url = reverse('import-handgrading-rubric',
                      kwargs={'project_pk': self.import_to.pk,
                              'import_from_project_pk': 9002})
        self.client.force_authenticate(self.admin)
        response = self.client.post(url)
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

        self.import_to.refresh_from_db()

        self.assertFalse(hasattr(self.import_to, 'handgrading_rubric'))


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
            reverse('num-queued-submissions',
                    kwargs={'pk': no_submits.pk}))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(0, response.data)

        response = client.get(
            reverse('num-queued-submissions',
                    kwargs={'pk': with_submits1.pk}))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(1, response.data)

        response = client.get(
            reverse('num-queued-submissions',
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

        url = reverse('download-tasks', kwargs={'pk': self.project.pk})
        self.client.force_authenticate(user1)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertCountEqual([task1.to_dict(), task2.to_dict()], response.data)

    def test_non_admin_list_project_download_tasks_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.project.course, 1)
        [handgrader] = obj_build.make_handgrader_users(self.project.course, 1)

        url = reverse('download-tasks', kwargs={'pk': self.project.pk})
        for user in staff, handgrader:
            self.client.force_authenticate(user)
            response = self.client.get(url)
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_get_download_task_detail(self):
        [user] = obj_build.make_admin_users(self.project.course, 1)

        task = ag_models.DownloadTask.objects.validate_and_create(
            project=self.project,
            creator=user, download_type=ag_models.DownloadType.all_scores)

        url = reverse('download-task-detail', kwargs={'pk': task.pk})
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

            url = reverse('download-task-result', kwargs={'pk': task.pk})
            self.client.force_authenticate(user)
            response = self.client.get(url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertIn('Content-Length', response)
            self.assertEqual(f.read(), b''.join(response.streaming_content))

    def test_invalid_get_in_progress_download_task_result(self):
        [user] = obj_build.make_admin_users(self.project.course, 1)

        in_progress_task = ag_models.DownloadTask.objects.validate_and_create(
            project=self.project,
            creator=user, download_type=ag_models.DownloadType.all_scores)

        url = reverse('download-task-result', kwargs={'pk': in_progress_task.pk})
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

        url = reverse('download-task-result', kwargs={'pk': errored_task.pk})
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

        url = reverse('download-task-result', kwargs={'pk': task.pk})
        self.client.force_authenticate(staff)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
