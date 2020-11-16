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


class ListAGTestCasesTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.case1 = obj_build.make_ag_test_case()
        self.ag_test_suite = self.case1.ag_test_suite
        self.case2 = obj_build.make_ag_test_case(self.ag_test_suite)
        self.course = self.ag_test_suite.project.course
        self.client = APIClient()
        self.url = reverse('ag_test_cases', kwargs={'ag_test_suite_pk': self.ag_test_suite.pk})

    def test_staff_valid_list_cases(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.client.force_authenticate(staff)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual([self.case1.to_dict(), self.case2.to_dict()], response.data)

    def test_non_staff_list_cases_permission_denied(self):
        student = obj_build.make_student_user(self.course)
        self.client.force_authenticate(student)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateAGTestCaseTestCase(test_impls.CreateObjectTest, UnitTestBase):
    def setUp(self):
        super().setUp()
        self.ag_test_suite = obj_build.make_ag_test_suite()
        self.course = self.ag_test_suite.project.course
        self.client = APIClient()
        self.url = reverse('ag_test_cases', kwargs={'ag_test_suite_pk': self.ag_test_suite.pk})

    def test_admin_valid_create(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        data = {
            'name': 'adsjkfa;jeifae;fjakjxc,mcaj'
        }
        self.do_create_object_test(
            ag_models.AGTestCase.objects, self.client, admin, self.url, data)

    def test_non_admin_create_permission_denied(self):
        data = {'name': 'advnaieroa'}

        [staff] = obj_build.make_staff_users(self.ag_test_suite.project.course, 1)
        self.do_permission_denied_create_test(
            ag_models.AGTestCase.objects, self.client, staff, self.url, data)

        student = obj_build.make_student_user(self.ag_test_suite.project.course)
        self.do_permission_denied_create_test(
            ag_models.AGTestCase.objects, self.client, student, self.url, data)


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
        student = obj_build.make_student_user(self.course)
        self.client.force_authenticate(student)

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
        student = obj_build.make_student_user(self.course)
        self.do_permission_denied_get_test(self.client, student, self.url)

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


class CachedSubmissionResultInvalidationTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.submission = obj_build.make_finished_submission()
        self.project = self.submission.group.project
        self.ag_test_suite = obj_build.make_ag_test_suite(self.project)
        self.ag_test_case = obj_build.make_ag_test_case(self.ag_test_suite)

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
        url = reverse('ag_test_case_order',
                      kwargs={'ag_test_suite_pk': self.ag_test_suite.pk})
        with self.assert_cache_key_invalidated(self.key):
            response = self.client.put(url, [self.ag_test_case.pk])
            self.assertEqual(status.HTTP_200_OK, response.status_code)

    def test_update_invalidates_cached_submission_result_fdbk(self):
        url = reverse('ag-test-case-detail', kwargs={'pk': self.ag_test_case.pk})
        with self.assert_cache_key_invalidated(self.key):
            response = self.client.patch(url, {'name': 'WAAAA'})
            self.assertEqual(status.HTTP_200_OK, response.status_code)

    def test_delete_invalidates_cached_submission_result_fdbk(self):
        url = reverse('ag-test-case-detail', kwargs={'pk': self.ag_test_case.pk})
        with self.assert_cache_key_invalidated(self.key):
            response = self.client.delete(url)
            self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

    def test_create_does_not_invalidate_cache(self):
        url = reverse('ag_test_cases', kwargs={'ag_test_suite_pk': self.ag_test_suite.pk})
        self.assertIsNotNone(cache.get(self.key))
        response = self.client.post(url, {'name': 'Wee'})
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertIsNotNone(cache.get(self.key))
