from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build

import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls


class ListAGTestSuitesTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.suite1 = obj_build.make_ag_test_suite()
        self.project = self.suite1.project
        self.suite2 = obj_build.make_ag_test_suite(self.project)
        self.client = APIClient()
        self.url = reverse('ag_test_suites', kwargs={'project_pk': self.project.pk})

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


class CreateAGTestSuiteTestCase(test_impls.CreateObjectTest, UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()
        self.client = APIClient()
        self.url = reverse('ag_test_suites', kwargs={'project_pk': self.project.pk})

        self.create_data = {
            'name': 'adslkfjals;dkjfa;lsdkjf'
        }

    def test_admin_valid_create(self):
        [admin] = obj_build.make_admin_users(self.project.course, 1)
        self.do_create_object_test(
            ag_models.AGTestSuite.objects, self.client, admin, self.url, self.create_data)

    def test_non_admin_create_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.project.course, 1)
        self.do_permission_denied_create_test(
            ag_models.AGTestSuite.objects, self.client, staff, self.url, self.create_data)

        [enrolled] = obj_build.make_student_users(self.project.course, 1)
        self.do_permission_denied_create_test(
            ag_models.AGTestSuite.objects, self.client, enrolled, self.url, self.create_data)


class AGTestSuitesOrderTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.suite1 = obj_build.make_ag_test_suite()
        self.project = self.suite1.project
        self.suite2 = obj_build.make_ag_test_suite(self.project)
        self.client = APIClient()
        self.url = reverse('ag_test_suite_order', kwargs={'project_pk': self.project.pk})

    def test_staff_get_order(self):
        [staff] = obj_build.make_staff_users(self.project.course, 1)
        self.client.force_authenticate(staff)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual([self.suite1.pk, self.suite2.pk], response.data)

        new_order = [self.suite2.pk, self.suite1.pk]
        self.project.set_agtestsuite_order(new_order)
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

        reverse_order = self.project.get_agtestsuite_order()[::-1]
        response = self.client.put(self.url, reverse_order)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(reverse_order, self.project.get_agtestsuite_order())

    def test_non_admin_set_order_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.project.course, 1)
        self.client.force_authenticate(staff)

        original_order = list(self.project.get_agtestsuite_order())
        response = self.client.put(self.url, original_order[::-1])

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertSequenceEqual(original_order, self.project.get_agtestsuite_order())


class GetUpdateDeleteAGTestSuiteTestCase(test_impls.GetObjectTest,
                                         test_impls.UpdateObjectTest,
                                         test_impls.DestroyObjectTest,
                                         UnitTestBase):
    def setUp(self):
        super().setUp()
        self.ag_test_suite = obj_build.make_ag_test_suite()
        self.course = self.ag_test_suite.project.course
        self.client = APIClient()
        self.url = reverse('ag-test-suite-detail', kwargs={'pk': self.ag_test_suite.pk})

    def test_staff_valid_get(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_get_object_test(self.client, staff, self.url, self.ag_test_suite.to_dict())

    def test_non_staff_get_permission_denied(self):
        [enrolled] = obj_build.make_student_users(self.course, 1)
        self.do_permission_denied_get_test(self.client, enrolled, self.url)

    def test_admin_valid_update(self):
        patch_data = {
            'name': 'asdf;aliena,cskvnaksd;fasdkjfaklsd',
            'setup_suite_cmd': 'echo "weeeeeeeeee"',
            'ultimate_submission_fdbk_config': {
                'show_setup_stderr': False
            },
            'deferred': True
        }
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_patch_object_test(self.ag_test_suite, self.client, admin, self.url, patch_data)

    def test_admin_update_bad_values(self):
        patch_data = {
            'name': '',
            'ultimate_submission_fdbk_config': {
                'not_a_field': False
            }
        }
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_patch_object_invalid_args_test(
            self.ag_test_suite, self.client, admin, self.url, patch_data)

    def test_non_admin_update_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_patch_object_permission_denied_test(
            self.ag_test_suite, self.client, staff, self.url, {'name': 'hello'})

    def test_admin_valid_delete(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_delete_object_test(self.ag_test_suite, self.client, admin, self.url)

    def test_non_admin_delete_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_delete_object_permission_denied_test(
            self.ag_test_suite, self.client, staff, self.url)
