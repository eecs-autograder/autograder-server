from django.urls import reverse
from django.core import exceptions

from rest_framework import status

import autograder.core.models as ag_models

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_generic_data as test_data


class _ProjectsSetUp(test_data.Client, test_data.Project, UnitTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse('project-list-create',
                           kwargs={'pk': self.course.pk})


class CourseListProjectsTestCase(_ProjectsSetUp):
    def setUp(self):
        super().setUp()

    def test_admin_list_projects(self):
        self.do_valid_list_projects_test(self.admin, self.all_projects)

    def test_staff_list_projects(self):
        self.do_valid_list_projects_test(self.staff, self.all_projects)

    def test_enrolled_student_list_projects_visible_only(self):
        # Make sure more than just visible projects exist
        all_projects = self.all_projects
        self.do_valid_list_projects_test(self.enrolled, self.visible_projects)

    def test_other_list_projects_permission_denied(self):
        self.client.force_authenticate(self.nobody)
        response = self.client.get(self.url)
        self.assertEqual(403, response.status_code)

    def do_valid_list_projects_test(self, user, expected_projects):
        expected_data = []
        for project in expected_projects:
            proj_dict = project.to_dict()
            proj_dict.pop('closing_time', None)
            expected_data.append(proj_dict)

        self.client.force_authenticate(user)
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertCountEqual(expected_data, response.data)


class CourseAddProjectTestCase(_ProjectsSetUp):
    def test_course_admin_add_project(self):
        args = {'name': 'spam project',
                'min_group_size': 2,
                'max_group_size': 3}
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, args)

        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        loaded = self.course.projects.get(name=args['name'])
        for arg_name, value in args.items():
            self.assertEqual(value, getattr(loaded, arg_name), msg='arg_name')

    def test_other_add_project_permission_denied(self):
        project_name = 'project123'
        for user in self.staff, self.enrolled, self.nobody:
            self.client.force_authenticate(user)
            response = self.client.post(self.url, {'name': project_name})

            self.assertEqual(403, response.status_code)

            with self.assertRaises(exceptions.ObjectDoesNotExist):
                ag_models.Project.objects.get(name=project_name)
