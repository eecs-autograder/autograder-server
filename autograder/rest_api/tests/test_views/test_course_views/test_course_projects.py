from django.core.urlresolvers import reverse
from django.core import exceptions

from rest_framework import status

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.rest_api.tests.test_views.common_generic_data as test_data


class _ProjectsSetUp(test_data.Client, test_data.Project):
    def setUp(self):
        super().setUp()
        self.url = reverse('course-projects-list',
                           kwargs={'course_pk': self.course.pk})


class CourseListProjectsTestCase(_ProjectsSetUp, TemporaryFilesystemTestCase):
    def test_admin_or_staff_list_projects(self):
        expected_content = ag_serializers.ProjectSerializer(
            self.all_projects, many=True).data
        for user in self.admin, self.staff:
            self.client.force_authenticate(user)
            response = self.client.get(self.url)

            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertCountEqual(expected_content, response.data)

    def test_enrolled_student_list_projects_visible_only(self):
        expected_content = ag_serializers.ProjectSerializer(
            self.visible_projects, many=True).data

        self.client.force_authenticate(self.enrolled)
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertCountEqual(expected_content, response.data)

    def test_other_list_projects_permission_denied(self):
        self.client.force_authenticate(self.nobody)
        response = self.client.get(self.url)
        self.assertEqual(403, response.status_code)


class CourseAddProjectTestCase(_ProjectsSetUp, TemporaryFilesystemTestCase):
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
