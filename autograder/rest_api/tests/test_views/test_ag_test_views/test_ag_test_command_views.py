from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build

import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class ListAGTestCommandsTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.cmd1 = obj_build.make_full_ag_test_command()
        self.ag_test_case = self.cmd1.ag_test_case
        self.cmd2 = obj_build.make_full_ag_test_command(self.ag_test_case)
        self.course = self.ag_test_case.ag_test_suite.project.course
        self.client = APIClient()
        self.url = reverse('ag_test_commands', kwargs={'ag_test_case_pk': self.ag_test_case.pk})

    def test_staff_valid_list_cmds(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.client.force_authenticate(staff)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual([self.cmd1.to_dict(), self.cmd2.to_dict()], response.data)

    def test_non_staff_list_cmds_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.client.force_authenticate(enrolled)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateAGTestCommandsTestCase(test_impls.CreateObjectTest, UnitTestBase):
    def setUp(self):
        super().setUp()
        self.ag_test_case = obj_build.make_ag_test_case()
        self.course = self.ag_test_case.ag_test_suite.project.course
        self.client = APIClient()
        self.url = reverse('ag_test_commands', kwargs={'ag_test_case_pk': self.ag_test_case.pk})

    def test_admin_valid_create(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        data = {
            'name': 'qpweiourasdjf',
            'cmd': 'echo "haldo"',
        }
        self.do_create_object_test(
            ag_models.AGTestCommand.objects, self.client, admin, self.url, data)

    def test_non_admin_create_permission_denied(self):
        data = {
            'name': 'xcm,vnm,xczv',
            'cmd': 'echo "wow"',
        }

        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_permission_denied_create_test(
            ag_models.AGTestCommand.objects, self.client, staff, self.url, data)

        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.do_permission_denied_create_test(
            ag_models.AGTestCommand.objects, self.client, enrolled, self.url, data)


class AGTestCommandOrderTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.cmd1 = obj_build.make_full_ag_test_command()
        self.ag_test_case = self.cmd1.ag_test_case
        self.cmd2 = obj_build.make_full_ag_test_command(self.ag_test_case)
        self.course = self.ag_test_case.ag_test_suite.project.course
        self.client = APIClient()
        self.url = reverse('ag_test_command_order',
                           kwargs={'ag_test_case_pk': self.ag_test_case.pk})

    def test_staff_get_order(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.client.force_authenticate(staff)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual([self.cmd1.pk, self.cmd2.pk], response.data)

        new_order = [self.cmd2.pk, self.cmd1.pk]
        self.ag_test_case.set_agtestcommand_order(new_order)
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(new_order, response.data)

    def test_non_staff_get_order_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.client.force_authenticate(enrolled)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_admin_set_order(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.client.force_authenticate(admin)

        reverse_order = self.ag_test_case.get_agtestcommand_order()[::-1]
        response = self.client.put(self.url, reverse_order)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(reverse_order, response.data)

    def test_non_admin_set_order_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.client.force_authenticate(staff)

        original_order = list(self.ag_test_case.get_agtestcommand_order())
        response = self.client.put(self.url, original_order[::-1])

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertSequenceEqual(original_order, self.ag_test_case.get_agtestcommand_order())


class GetUpdateDeleteAGTestCommandTestCase(test_impls.GetObjectTest,
                                           test_impls.UpdateObjectTest,
                                           test_impls.DestroyObjectTest,
                                           UnitTestBase):
    def setUp(self):
        super().setUp()
        self.ag_test_cmd = obj_build.make_full_ag_test_command()
        self.course = self.ag_test_cmd.ag_test_case.ag_test_suite.project.course
        self.client = APIClient()
        self.url = reverse('ag-test-command-detail', kwargs={'pk': self.ag_test_cmd.pk})

    def test_staff_valid_get(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_get_object_test(self.client, staff, self.url, self.ag_test_cmd.to_dict())

    def test_non_staff_get_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.do_permission_denied_get_test(self.client, enrolled,self.url)

    def test_admin_valid_update(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        patch_data = {
            'name': 'mcnaieoa;dk',
            'normal_fdbk_config': {
                'return_code_fdbk_level': ag_models.ValueFeedbackLevel.expected_and_actual.value
            }
        }
        self.do_patch_object_test(self.ag_test_cmd, self.client, admin, self.url, patch_data)

    def test_admin_update_bad_values(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        bad_patch_data = {
            'normal_fdbk_config': {
                'return_code_fdbk_level': 'not_a_value'
            }
        }
        self.do_patch_object_invalid_args_test(
            self.ag_test_cmd, self.client, admin, self.url, bad_patch_data)

    def test_non_admin_update_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        patch_data = {
            'name': 'mcnaieoa;dk',
        }
        self.do_patch_object_permission_denied_test(
            self.ag_test_cmd, self.client, staff, self.url, patch_data)

    def test_admin_valid_delete(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_delete_object_test(self.ag_test_cmd, self.client, admin, self.url)

    def test_non_admin_delete_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_delete_object_permission_denied_test(
            self.ag_test_cmd, self.client, staff, self.url)
