from django.core.urlresolvers import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build

import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class AGTestCaseOrderTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.case1 = obj_build.make_ag_test_case()
        self.ag_test_suite = self.case1.ag_test_suite
        self.case2 = obj_build.make_ag_test_case(self.case1.ag_test_suite)
        self.course = self.ag_test_suite.project.course
        self.client = APIClient()
        self.url = reverse('ag_test_case_order',
                           kwargs={'ag_test_suite_pk': self.ag_test_suite.pk})

    def test_staff_get_order(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.client.force_authenticate(staff)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual([self.case1.pk, self.case2.pk], response.data)

        new_order = [self.case2.pk, self.case1.pk]
        self.ag_test_suite.set_agtestcase_order(new_order)
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual([self.case2.pk, self.case1.pk], response.data)

    def test_non_staff_get_order_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.client.force_authenticate(enrolled)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_admin_set_order(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.client.force_authenticate(admin)

        reverse_order = self.ag_test_suite.get_agtestcase_order()[::-1]
        response = self.client.put(self.url, reverse_order)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(reverse_order, response.data)

    def test_non_admin_set_order_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.client.force_authenticate(staff)

        original_order = list(self.ag_test_suite.get_agtestcase_order())
        response = self.client.put(self.url, original_order[::-1])

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertSequenceEqual(original_order, self.ag_test_suite.get_agtestcase_order())


class ListAGTestCasesTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.case1 = obj_build.make_ag_test_case()
        self.ag_test_suite = self.case1.ag_test_suite
        self.case2 = obj_build.make_ag_test_case(self.ag_test_suite)
        self.course = self.ag_test_suite.project.course
        self.client = APIClient()
        self.url = reverse('ag_test_cases', kwargs={'ag_test_suite_pk':self.ag_test_suite.pk})

    def test_staff_valid_list_cases(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.client.force_authenticate(staff)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual([self.case1.to_dict(), self.case2.to_dict()], response.data)

    def test_non_staff_list_cases_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.client.force_authenticate(enrolled)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateAGTestCaseTestCase(test_impls.CreateObjectTest, UnitTestBase):
    def setUp(self):
        super().setUp()
        self.ag_test_suite = obj_build.make_ag_test_suite()
        self.course = self.ag_test_suite.project.course
        self.client = APIClient()
        self.url = reverse('ag_test_cases', kwargs={'ag_test_suite_pk':self.ag_test_suite.pk})

    def test_admin_valid_create(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        data = {
            'name': 'adsjkfa;jeifae;fjakjxc,mcaj'
        }
        self.do_create_object_test(
            ag_models.AGTestCase.objects, self.client, admin, self.url, data)

    def test_non_admin_create_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.ag_test_suite.project.course, 1)
        data = {
            'name': 'advnaieroa;'
        }
        self.do_permission_denied_create_test(
            ag_models.AGTestCase.objects, self.client, enrolled, self.url, data)


class GetUpdateDeleteAGTestCaseTestCase(test_impls.GetObjectTest,
                                        test_impls.UpdateObjectTest,
                                        test_impls.DestroyObjectTest,
                                        UnitTestBase):
    def setUp(self):
        super().setUp()
        self.ag_test_case = obj_build.make_ag_test_case()
        self.course = self.ag_test_case.ag_test_suite.project.course
        self.client = APIClient()
        self.url = reverse('ag-test-case-detail', kwargs={'pk': self.ag_test_case.pk})

    def test_staff_valid_get(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_get_object_test(self.client, staff, self.url, self.ag_test_case.to_dict())

    def test_non_staff_get_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.do_permission_denied_get_test(self.client, enrolled, self.url)

    def test_admin_valid_update(self):
        other_suite = obj_build.make_ag_test_suite(project=self.ag_test_case.ag_test_suite.project)
        patch_data = {
            'name': 'ncvai',
            'ag_test_suite': other_suite.pk,
            'normal_fdbk_config': {
                'show_individual_commands': False
            }
        }
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_patch_object_test(self.ag_test_case, self.client, admin, self.url, patch_data)

    def test_admin_update_bad_values(self):
        bad_data = {
            'name': ''
        }
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_patch_object_invalid_args_test(
            self.ag_test_case, self.client, admin, self.url, bad_data)

    def test_non_admin_update_permission_denied(self):
        patch_data = {
            'name': 'adfasdflkj;lkj'
        }
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_patch_object_permission_denied_test(
            self.ag_test_case, self.client, staff, self.url, patch_data)

    def test_admin_valid_delete(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_delete_object_test(self.ag_test_case, self.client, admin, self.url)

    def test_non_admin_delete_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_delete_object_permission_denied_test(
            self.ag_test_case, self.client, staff, self.url)
