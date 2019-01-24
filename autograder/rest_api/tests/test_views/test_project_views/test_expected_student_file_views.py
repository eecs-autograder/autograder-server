import random

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls
import autograder.rest_api.tests.test_views.common_generic_data as test_data
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class ListPatternsTestCase(test_impls.GetObjectTest, UnitTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.project = obj_build.make_project()
        self.url = reverse('expected-student-files', kwargs={'pk': self.project.pk})

    def test_admin_list_patterns(self):
        admin = obj_build.make_admin_user(self.project.course)
        self.do_list_patterns_test(admin, self.project)

    def test_staff_list_patterns(self):
        staff = obj_build.make_staff_user(self.project.course)
        self.do_list_patterns_test(staff, self.project)

    def test_student_list_patterns(self):
        self.project.validate_and_update(visible_to_students=True)

        student = obj_build.make_student_user(self.project.course)
        self.do_list_patterns_test(student, self.project)

    def test_student_list_patterns_project_hidden_permission_denied(self):
        student = obj_build.make_student_user(self.project.course)
        self.do_permission_denied_get_test(self.client, student, self.url)

    def test_guest_list_patterns_any_domain(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        guest = obj_build.make_user()
        self.do_list_patterns_test(guest, self.project)

    def test_guest_list_patterns_right_domain(self):
        self.project.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        guest = obj_build.make_allowed_domain_guest_user(self.project.course)
        self.do_list_patterns_test(guest, self.project)

    def test_guest_wrong_domain_list_patterns_permission_denied(self):
        self.project.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        guest = obj_build.make_user()
        self.do_permission_denied_get_test(self.client, guest, self.url)

    def test_guest_list_patterns_project_hidden_permission_denied(self):
        self.project.validate_and_update(guests_can_submit=True)

        guest = obj_build.make_user()
        self.do_permission_denied_get_test(self.client, guest, self.url)

    def test_guest_list_patterns_project_private_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True)

        guest = obj_build.make_user()
        self.do_permission_denied_get_test(self.client, guest, self.url)

    def do_list_patterns_test(self, user, project):
        serialized_patterns = self.build_patterns(project)
        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertCountEqual(serialized_patterns, response.data)

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


class CreatePatternTestCase(test_data.Client, test_data.Project, UnitTestBase):
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


class RetrieveExpectedPatternTestCase(test_impls.GetObjectTest, UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()
        self.course = self.project.course
        self.client = APIClient()

    def test_admin_get_expected_student_file(self):
        admin = obj_build.make_admin_user(self.course)
        pattern = build_pattern(self.project)
        self.do_get_object_test(self.client, admin,
                                pattern_url(pattern), pattern.to_dict())

    def test_staff_get_expected_student_file(self):
        staff = obj_build.make_staff_user(self.course)
        pattern = build_pattern(self.project)
        self.do_get_object_test(self.client, staff,
                                pattern_url(pattern), pattern.to_dict())

    def test_student_get_expected_student_file(self):
        self.project.validate_and_update(visible_to_students=True)
        student = obj_build.make_student_user(self.course)
        pattern = build_pattern(self.project)
        self.do_get_object_test(self.client, student,
                                pattern_url(pattern), pattern.to_dict())

    def test_student_get_expected_student_file_project_hidden_permission_denied(self):
        student = obj_build.make_student_user(self.course)
        pattern = build_pattern(self.project)
        self.do_permission_denied_get_test(self.client, student, pattern_url(pattern))

    def test_guest_get_expected_student_file_any_domain(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        guest = obj_build.make_user()
        pattern = build_pattern(self.project)
        self.do_get_object_test(self.client, guest, pattern_url(pattern), pattern.to_dict())

    def test_guest_get_expected_student_file_right_domain(self):
        self.project.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        guest = obj_build.make_allowed_domain_guest_user(self.project.course)
        pattern = build_pattern(self.project)
        self.do_get_object_test(self.client, guest, pattern_url(pattern), pattern.to_dict())

    def test_guest_wrong_domain_get_expected_student_file_permission_denied(self):
        self.project.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        guest = obj_build.make_user()
        pattern = build_pattern(self.project)
        self.do_permission_denied_get_test(self.client, guest, pattern_url(pattern))

    def test_guest_list_patterns_project_hidden_permission_denied(self):
        self.project.validate_and_update(guests_can_submit=True)

        guest = obj_build.make_user()
        pattern = build_pattern(self.project)
        self.do_permission_denied_get_test(self.client, guest, pattern_url(pattern))

    def test_guest_list_patterns_project_private_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True)

        guest = obj_build.make_user()
        pattern = build_pattern(self.project)
        self.do_permission_denied_get_test(self.client, guest, pattern_url(pattern))


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
