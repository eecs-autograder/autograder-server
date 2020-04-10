import random

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.rest_api.tests.test_views.ag_view_test_base import AGViewTestBase
from autograder.utils.testing import UnitTestBase


class ListPatternsTestCase(AGViewTestBase):
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
        serialized_patterns = [
            obj_build.make_expected_student_file(
                self.project,
                min_num_matches=random.randint(0, 2),
                max_num_matches=random.randint(3, 6)
            ).to_dict()
            for i in range(4)
        ]
        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertCountEqual(serialized_patterns, response.data)


class CreatePatternTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.project = obj_build.make_project()
        self.course = self.project.course
        self.admin = obj_build.make_admin_user(self.course)

    def test_admin_create_pattern(self):
        self.assertEqual(0, self.project.expected_student_files.count())

        args = {
            'pattern': 'spam.cpp',
            'min_num_matches': 1,
            'max_num_matches': 4
        }

        self.client.force_authenticate(self.admin)
        response = self.client.post(self.get_patterns_url(self.project), args)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, self.project.expected_student_files.count())
        created_pattern = self.project.expected_student_files.first()
        for arg_name, value in args.items():
            self.assertEqual(value, getattr(created_pattern, arg_name), msg=arg_name)

    def test_admin_create_pattern_invalid_settings(self):
        self.assertEqual(0, self.project.expected_student_files.count())

        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.get_patterns_url(self.project),
            {
                'pattern': 'spam.cpp',
                'min_num_matches': 3,
                'max_num_matches': 1
            }
        )
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(0, self.project.expected_student_files.count())

    def test_non_admin_create_pattern_permission_denied(self):
        staff = obj_build.make_staff_user(self.course)
        student = obj_build.make_student_user(self.course)
        handgrader = obj_build.make_handgrader_user(self.course)
        guest = obj_build.make_user()

        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        for user in staff, student, handgrader, guest:
            self.client.force_authenticate(user)
            response = self.client.post(
                self.get_patterns_url(self.project),
                {
                    'pattern': 'spam.cpp',
                    'min_num_matches': 1,
                    'max_num_matches': 4
                }
            )
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual(
            0, self.project.expected_student_files.count())

    def get_patterns_url(self, project):
        return reverse('expected-student-files', kwargs={'pk': project.pk})


def pattern_url(pattern_obj):
    return reverse('expected-student-file-detail', kwargs={'pk': pattern_obj.pk})


class RetrieveExpectedPatternTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()
        self.course = self.project.course
        self.client = APIClient()

    def test_admin_get_expected_student_file(self):
        admin = obj_build.make_admin_user(self.course)
        pattern = obj_build.make_expected_student_file(self.project)
        self.do_get_object_test(self.client, admin,
                                pattern_url(pattern), pattern.to_dict())

    def test_staff_get_expected_student_file(self):
        staff = obj_build.make_staff_user(self.course)
        pattern = obj_build.make_expected_student_file(self.project)
        self.do_get_object_test(self.client, staff,
                                pattern_url(pattern), pattern.to_dict())

    def test_student_get_expected_student_file(self):
        self.project.validate_and_update(visible_to_students=True)
        student = obj_build.make_student_user(self.course)
        pattern = obj_build.make_expected_student_file(self.project)
        self.do_get_object_test(self.client, student,
                                pattern_url(pattern), pattern.to_dict())

    def test_student_get_expected_student_file_project_hidden_permission_denied(self):
        student = obj_build.make_student_user(self.course)
        pattern = obj_build.make_expected_student_file(self.project)
        self.do_permission_denied_get_test(self.client, student, pattern_url(pattern))

    def test_guest_get_expected_student_file_any_domain(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        guest = obj_build.make_user()
        pattern = obj_build.make_expected_student_file(self.project)
        self.do_get_object_test(self.client, guest, pattern_url(pattern), pattern.to_dict())

    def test_guest_get_expected_student_file_right_domain(self):
        self.project.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        guest = obj_build.make_allowed_domain_guest_user(self.project.course)
        pattern = obj_build.make_expected_student_file(self.project)
        self.do_get_object_test(self.client, guest, pattern_url(pattern), pattern.to_dict())

    def test_guest_wrong_domain_get_expected_student_file_permission_denied(self):
        self.project.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        guest = obj_build.make_user()
        pattern = obj_build.make_expected_student_file(self.project)
        self.do_permission_denied_get_test(self.client, guest, pattern_url(pattern))

    def test_guest_list_patterns_project_hidden_permission_denied(self):
        self.project.validate_and_update(guests_can_submit=True)

        guest = obj_build.make_user()
        pattern = obj_build.make_expected_student_file(self.project)
        self.do_permission_denied_get_test(self.client, guest, pattern_url(pattern))

    def test_guest_list_patterns_project_private_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True)

        guest = obj_build.make_user()
        pattern = obj_build.make_expected_student_file(self.project)
        self.do_permission_denied_get_test(self.client, guest, pattern_url(pattern))


class UpdateExpectedPatternTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()
        self.course = self.project.course
        self.admin = obj_build.make_admin_user(self.course)
        self.client = APIClient()

    def test_admin_patch_pattern(self):
        pattern = obj_build.make_expected_student_file(self.project)
        self.do_patch_object_test(
            pattern, self.client, self.admin, pattern_url(pattern),
            {'pattern': 'some very new pattern', 'min_num_matches': 5, 'max_num_matches': 8})

    def test_admin_update_pattern_invalid_args(self):
        pattern = obj_build.make_expected_student_file(self.project)
        self.do_patch_object_invalid_args_test(
            pattern, self.client, self.admin, pattern_url(pattern),
            {'min_num_matches': 3, 'max_num_matches': 1})

    def test_non_admin_update_pattern_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        pattern = obj_build.make_expected_student_file(self.project)

        staff = obj_build.make_staff_user(self.course)
        student = obj_build.make_student_user(self.course)
        handgrader = obj_build.make_handgrader_user(self.course)
        guest = obj_build.make_user()

        for user in staff, student, handgrader, guest:
            self.do_patch_object_permission_denied_test(
                pattern, self.client, user, pattern_url(pattern), {'pattern': 'kjahdfkjhasdf'})


class DeleteExpectedPatternTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()
        self.course = self.project.course
        self.admin = obj_build.make_admin_user(self.course)
        self.client = APIClient()

    def test_admin_delete_pattern(self):
        pattern = obj_build.make_expected_student_file(self.project)
        self.do_delete_object_test(pattern, self.client, self.admin, pattern_url(pattern))

    def test_other_delete_pattern_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        pattern = obj_build.make_expected_student_file(self.project)

        staff = obj_build.make_staff_user(self.course)
        student = obj_build.make_student_user(self.course)
        handgrader = obj_build.make_handgrader_user(self.course)
        guest = obj_build.make_user()

        for user in staff, student, handgrader, guest:
            self.do_delete_object_permission_denied_test(
                pattern, self.client, user, pattern_url(pattern))
