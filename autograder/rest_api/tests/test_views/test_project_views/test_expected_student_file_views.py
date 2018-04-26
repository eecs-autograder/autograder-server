import itertools
import random

from django.urls import reverse
from rest_framework import status

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls
import autograder.rest_api.tests.test_views.common_generic_data as test_data
from autograder.utils.testing import UnitTestBase


class _PatternSetUp(test_data.Client, test_data.Project):
    pass


class ListPatternsTestCase(_PatternSetUp, UnitTestBase):
    def test_admin_list_patterns(self):
        for project in self.all_projects:
            self.do_list_patterns_test(self.admin, project)

    def test_staff_list_patterns(self):
        for project in self.all_projects:
            self.do_list_patterns_test(self.staff, project)

    def test_enrolled_list_patterns(self):
        for project in self.visible_projects:
            self.do_list_patterns_test(self.enrolled, project)

        for project in self.hidden_projects:
            self.do_permission_denied_test(self.enrolled, project)

    def test_other_list_patterns(self):
        self.do_list_patterns_test(self.nobody, self.visible_public_project)

        for project in [self.visible_private_project] + self.hidden_projects:
            self.do_permission_denied_test(self.nobody, project)

    def do_list_patterns_test(self, user, project):
        serialized_patterns = self.build_patterns(project)
        self.client.force_authenticate(user)
        response = self.client.get(self.get_patterns_url(project))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertCountEqual(serialized_patterns, response.data)

    def do_permission_denied_test(self, user, project):
        self.build_patterns(project)
        self.client.force_authenticate(user)
        response = self.client.get(self.get_patterns_url(project))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def build_patterns(self, project):
        num_patterns = 4
        if not project.expected_student_files.count():
            for i in range(num_patterns):
                min_matches = random.randint(0, 3)
                max_matches = min_matches + 2
                ag_models.ExpectedStudentFile.objects.validate_and_create(
                    project=project,
                    pattern=project.name + '_pattern_' + str(i),
                    min_num_matches=min_matches,
                    max_num_matches=max_matches)

        serialized_patterns = (
            ag_serializers.ExpectedStudentFileSerializer(
                project.expected_student_files.all(), many=True)
        ).data
        self.assertEqual(num_patterns, len(serialized_patterns))
        return serialized_patterns


class CreatePatternTestCase(_PatternSetUp, UnitTestBase):
    def test_admin_create_pattern(self):
        self.assertEqual(
            0, self.project.expected_student_files.count())

        args = {
            'pattern': 'spam.cpp',
            'min_num_matches': 1,
            'max_num_matches': 4
        }

        self.client.force_authenticate(self.admin)
        response = self.client.post(self.get_patterns_url(self.project), args)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(
            1, self.project.expected_student_files.count())
        created_pattern = self.project.expected_student_files.first()
        for arg_name, value in args.items():
            self.assertEqual(value, getattr(created_pattern, arg_name),
                             msg=arg_name)

    def test_admin_create_pattern_invalid_settings(self):
        self.assertEqual(
            0, self.project.expected_student_files.count())

        args = {
            'pattern': 'spam.cpp',
            'min_num_matches': 3,
            'max_num_matches': 1
        }

        self.client.force_authenticate(self.admin)
        response = self.client.post(self.get_patterns_url(self.project), args)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            0, self.project.expected_student_files.count())

    def test_non_admin_create_pattern_permission_denied(self):
        args = {
            'pattern': 'spam.cpp',
            'min_num_matches': 1,
            'max_num_matches': 4
        }

        for user in self.staff, self.enrolled, self.nobody:
            self.client.force_authenticate(user)
            response = self.client.post(
                self.get_patterns_url(self.visible_public_project), args)
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual(
            0, self.project.expected_student_files.count())


base_pattern_kwargs = {
    'pattern': 'spaaaaaam',
    'min_num_matches': 1,
    'max_num_matches': 4
}


def build_pattern(project):
    return ag_models.ExpectedStudentFile.objects.validate_and_create(
        project=project, **base_pattern_kwargs)


def pattern_url(pattern_obj):
    return reverse('expected-student-file-detail', kwargs={'pk': pattern_obj.pk})


class RetrieveExpectedPatternTestCase(test_data.Client,
                                      test_data.Project,
                                      test_impls.GetObjectTest,
                                      UnitTestBase):
    def test_admin_get_pattern(self):
        for project in self.all_projects:
            pattern = build_pattern(project)
            self.do_get_object_test(self.client, self.admin,
                                    pattern_url(pattern), pattern.to_dict())

    def test_staff_get_pattern(self):
        for project in self.all_projects:
            pattern = build_pattern(project)
            self.do_get_object_test(self.client, self.staff,
                                    pattern_url(pattern), pattern.to_dict())

    def test_enrolled_get_pattern(self):
        for project in self.visible_projects:
            pattern = build_pattern(project)
            self.do_get_object_test(self.client, self.enrolled,
                                    pattern_url(pattern), pattern.to_dict())

        for project in self.hidden_projects:
            pattern = build_pattern(project)
            self.do_permission_denied_get_test(self.client, self.enrolled,
                                               pattern_url(pattern))

    def test_other_get_pattern(self):
        visible_pattern = build_pattern(self.visible_public_project)
        self.do_get_object_test(self.client, self.nobody,
                                pattern_url(visible_pattern),
                                visible_pattern.to_dict())

        for project in itertools.chain([self.visible_private_project],
                                       self.hidden_projects):
            hidden_pattern = build_pattern(project)
            self.do_permission_denied_get_test(self.client, self.nobody,
                                               pattern_url(hidden_pattern))


class UpdateExpectedPatternTestCase(test_data.Client,
                                    test_data.Project,
                                    test_impls.UpdateObjectTest,
                                    UnitTestBase):
    @property
    def valid_args(self):
        return {
            'pattern': 'waaaaa',
            'max_num_matches': base_pattern_kwargs['max_num_matches'] + 2
        }

    def test_admin_patch_pattern(self):
        for project in self.all_projects:
            pattern = build_pattern(project)
            self.do_patch_object_test(pattern, self.client, self.admin,
                                      pattern_url(pattern), self.valid_args)

    def test_admin_update_pattern_invalid_args(self):
        args = {
            'min_num_matches': 3,
            'max_num_matches': 1
        }
        pattern = build_pattern(self.visible_public_project)
        self.do_patch_object_invalid_args_test(
            pattern, self.client, self.admin, pattern_url(pattern), args)

    def test_other_update_pattern_permission_denied(self):
        args = {
            'pattern': 'kjahdfkjhasdf'
        }
        pattern = build_pattern(self.visible_public_project)
        url = pattern_url(pattern)
        for user in self.staff, self.enrolled, self.nobody:
            self.do_patch_object_permission_denied_test(
                pattern, self.client, user, url, args)


class DeleteExpectedPatternTestCase(test_data.Client,
                                    test_data.Project,
                                    test_impls.DestroyObjectTest,
                                    UnitTestBase):
    def test_admin_delete_pattern(self):
        for project in self.all_projects:
            pattern = build_pattern(project)
            self.do_delete_object_test(
                pattern, self.client, self.admin, pattern_url(pattern))

    def test_other_delete_pattern_permission_denied(self):
        pattern = build_pattern(self.visible_public_project)
        url = pattern_url(pattern)
        for user in self.staff, self.enrolled, self.nobody:
            self.do_delete_object_permission_denied_test(
                pattern, self.client, user, url)
