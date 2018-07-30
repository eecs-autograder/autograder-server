from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls


class ListStudentTestSuitesTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.suite1 = obj_build.make_student_test_suite()
        self.project = self.suite1.project
        self.suite2 = obj_build.make_student_test_suite(self.project)

        self.client = APIClient()
        self.url = reverse('student_test_suites', kwargs={'project_pk': self.project.pk})

    def test_staff_valid_list_suites(self):
        [staff] = obj_build.make_staff_users(self.project.course, 1)
        self.client.force_authenticate(staff)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual([self.suite1.to_dict(), self.suite2.to_dict()], response.data)

    def test_non_staff_list_suites_permission_denied(self):
        [enrolled] = obj_build.make_student_users(self.project.course, 1)
        self.client.force_authenticate(enrolled)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateStudentTestSuiteTestCase(test_impls.CreateObjectTest, UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()
        self.client = APIClient()
        self.url = reverse('student_test_suites', kwargs={'project_pk': self.project.pk})

        self.create_data = {
            'name': 'some suite'
        }

    def test_admin_valid_create(self):
        [admin] = obj_build.make_admin_users(self.project.course, 1)
        self.do_create_object_test(
            ag_models.StudentTestSuite.objects, self.client, admin, self.url, self.create_data)

    def test_non_admin_create_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.project.course, 1)
        self.client.force_authenticate(staff)

        self.do_permission_denied_create_test(
            ag_models.StudentTestSuite.objects, self.client, staff, self.url, self.create_data)

        [enrolled] = obj_build.make_student_users(self.project.course, 1)

        self.client.force_authenticate(enrolled)

        self.do_permission_denied_create_test(
            ag_models.StudentTestSuite.objects, self.client, enrolled, self.url, self.create_data)


class StudentTestSuitesOrderTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.suite1 = obj_build.make_student_test_suite()
        self.project = self.suite1.project
        self.suite2 = obj_build.make_student_test_suite(self.project)

        self.suite_pks = list(self.project.get_studenttestsuite_order())

        self.client = APIClient()
        self.url = reverse('student_test_suite_order', kwargs={'project_pk': self.project.pk})

    def test_staff_get_order(self):
        [staff] = obj_build.make_staff_users(self.project.course, 1)
        self.client.force_authenticate(staff)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(self.suite_pks, response.data)

        new_order = self.suite_pks[::-1]
        self.project.set_studenttestsuite_order(new_order)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(new_order, response.data)

    def test_non_staff_get_order_permission_denied(self):
        [enrolled] = obj_build.make_student_users(self.project.course, 1)
        self.client.force_authenticate(enrolled)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_admin_set_order(self):
        [admin] = obj_build.make_admin_users(self.project.course, 1)
        self.client.force_authenticate(admin)

        reverse_order = self.project.get_studenttestsuite_order()[::-1]
        response = self.client.put(self.url, reverse_order)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(reverse_order, self.project.get_studenttestsuite_order())

    def test_non_admin_set_order_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.project.course, 1)
        self.client.force_authenticate(staff)

        response = self.client.put(self.url, self.suite_pks[::-1])

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertSequenceEqual(self.suite_pks, self.project.get_studenttestsuite_order())


class GetUpdateDeleteStudentTestSuiteTestCase(test_impls.GetObjectTest,
                                              test_impls.UpdateObjectTest,
                                              test_impls.DestroyObjectTest,
                                              UnitTestBase):
    def setUp(self):
        super().setUp()
        self.student_suite = obj_build.make_student_test_suite()
        self.course = self.student_suite.project.course

        self.client = APIClient()
        self.url = reverse('student-test-suite-detail', kwargs={'pk': self.student_suite.pk})

    def test_staff_valid_get(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_get_object_test(self.client, staff, self.url, self.student_suite.to_dict())

    def test_non_staff_get_permission_denied(self):
        [enrolled] = obj_build.make_student_users(self.course, 1)
        self.do_permission_denied_get_test(self.client, enrolled, self.url)

    def test_admin_valid_update(self):
        patch_data = {
            'name': 'a new name',
            'buggy_impl_names': ['bug_spam', 'bug_egg']
        }
        [admin] = obj_build.make_admin_users(self.course, 1)
        response = self.do_patch_object_test(
            self.student_suite, self.client, admin, self.url, patch_data)

        # Make sure the DecimalField is encoded correctly.
        self.assertIsInstance(response.data['points_per_exposed_bug'], str)

    def test_admin_update_bad_values(self):
        patch_data = {
            'name': '',
            'buggy_impl_names': ['bug_spam', '']
        }
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_patch_object_invalid_args_test(
            self.student_suite, self.client, admin, self.url, patch_data)

    def test_non_admin_update_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_patch_object_permission_denied_test(
            self.student_suite, self.client, staff, self.url, {'name': 'lulz'})

    def test_admin_valid_delete(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_delete_object_test(self.student_suite, self.client, admin, self.url)

    def test_non_admin_delete_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_delete_object_permission_denied_test(
            self.student_suite, self.client, staff, self.url)
