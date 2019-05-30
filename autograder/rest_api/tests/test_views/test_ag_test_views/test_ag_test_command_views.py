from django.core.cache import cache
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
from autograder.core.caching import submission_fdbk_cache_key, get_cached_submission_feedback
from autograder.core.submission_feedback import SubmissionResultFeedback, AGTestPreLoader
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build

import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls


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
        [enrolled] = obj_build.make_student_users(self.course, 1)
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

        [enrolled] = obj_build.make_student_users(self.course, 1)
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
        [enrolled] = obj_build.make_student_users(self.course, 1)
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
        [enrolled] = obj_build.make_student_users(self.course, 1)
        self.do_permission_denied_get_test(self.client, enrolled, self.url)

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


class CachedSubmissionResultInvalidationTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.submission = obj_build.make_finished_submission()
        self.project = self.submission.group.project
        self.ag_test_suite = obj_build.make_ag_test_suite(self.project)
        self.ag_test_case = obj_build.make_ag_test_case(self.ag_test_suite)
        self.ag_test_cmd = obj_build.make_full_ag_test_command(self.ag_test_case,
                                                               set_arbitrary_points=False,
                                                               set_arbitrary_expected_vals=False)

        self.key = submission_fdbk_cache_key(
            project_pk=self.project.pk, submission_pk=self.submission.pk)

        get_cached_submission_feedback(
            self.submission,
            SubmissionResultFeedback(self.submission,
                                     ag_models.FeedbackCategory.normal,
                                     AGTestPreLoader(self.project))
        )

        self.client = APIClient()
        self.client.force_authenticate(obj_build.make_admin_user(self.project.course))

    def test_set_order_invalidates_cached_submission_result_fdbk(self):
        url = reverse('ag_test_command_order',
                      kwargs={'ag_test_case_pk': self.ag_test_case.pk})
        with self.assert_cache_key_invalidated(self.key):
            response = self.client.put(url, [self.ag_test_cmd.pk])
            self.assertEqual(status.HTTP_200_OK, response.status_code)

    def test_update_invalidates_cached_submission_result_fdbk(self):
        url = reverse('ag-test-command-detail', kwargs={'pk': self.ag_test_cmd.pk})
        with self.assert_cache_key_invalidated(self.key):
            response = self.client.patch(url, {'name': 'WAAAA'})
            self.assertEqual(status.HTTP_200_OK, response.status_code)

    def test_delete_invalidates_cached_submission_result_fdbk(self):
        url = reverse('ag-test-command-detail', kwargs={'pk': self.ag_test_cmd.pk})
        with self.assert_cache_key_invalidated(self.key):
            response = self.client.delete(url)
            self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

    def test_create_does_not_invalidate_cache(self):
        url = reverse('ag_test_commands', kwargs={'ag_test_case_pk': self.ag_test_case.pk})
        self.assertIsNotNone(cache.get(self.key))
        response = self.client.post(url, {'name': 'Wee', 'cmd': 'cmdy'})
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertIsNotNone(cache.get(self.key))
