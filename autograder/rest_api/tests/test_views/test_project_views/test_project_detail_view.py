from rest_framework import status
from django.core.urlresolvers import reverse

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.core.models as ag_models


class _ProjectSetUp(test_data.Client, test_data.Project):
    pass


class RetrieveProjectTestCase(_ProjectSetUp, UnitTestBase):
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


class UpdateProjectTestCase(_ProjectSetUp, UnitTestBase):
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


class NumQueuedSubmissionsTestCase(_ProjectSetUp, UnitTestBase):
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
