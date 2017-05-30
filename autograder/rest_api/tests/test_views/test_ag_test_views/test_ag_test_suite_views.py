from django.core.urlresolvers import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build

import autograder.rest_api.tests.test_views.common_test_impls as test_impls


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
        [enrolled] = obj_build.make_enrolled_users(self.project.course, 1)
        self.client.force_authenticate(enrolled)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateAGTestSuiteTestCase(test_impls.CreateObjectTest, UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()
        self.client = APIClient()
        self.url = reverse('ag_test_suites', kwargs={'project_pk': self.project.pk})

    def test_admin_valid_create(self):
        [admin] = obj_build.make_admin_users(self.project.course, 1)
        data = {
            'name': 'adslkfjals;dkjfa;lsdkjf'
        }
        self.do_create_object_test(
            ag_models.AGTestSuite.objects, self.client, admin, self.url, data)

    def test_non_admin_create_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.project.course, 1)
        data = {
            'name': 'werjaisdlf;j'
        }
        self.do_permission_denied_create_test(
            ag_models.AGTestSuite.objects, self.client, enrolled, self.url, data)


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
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.do_permission_denied_get_test(self.client, enrolled, self.url)

    def test_admin_valid_update(self):
        patch_data = {
            'name': 'asdf;aliena,cskvnaksd;fasdkjfaklsd',
            'setup_suite_cmd': 'echo "weeeeeeeeee"',
            'ultimate_submission_fdbk_config': {
                'show_setup_and_teardown_stderr': False
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
