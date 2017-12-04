from django.core.urlresolvers import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.handgrading.models as handgrading_models
import autograder.utils.testing.model_obj_builders as obj_build

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class RetrieveHandgradingResultsTestCase(UnitTestBase):
    """/api/submissions/<submission_pk>/handgrading_results/"""

    def setUp(self):
        super().setUp()
        submission = obj_build.build_submission()

        handgrading_rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
                max_points=0,
                show_grades_and_rubric_to_students=False,
                handgraders_can_leave_comments=True,
                handgraders_can_apply_arbitrary_points=True,
                project=submission.submission_group.project
            )
        )

        data = {
            "submission": submission,
            "handgrading_rubric": handgrading_rubric
        }

        self.handgrading_result = (
            handgrading_models.HandgradingResult.objects.validate_and_create(**data)
        )
        self.client = APIClient()
        self.course = handgrading_rubric.project.course
        self.url = reverse('handgrading_results',
                           kwargs={'submission_pk': self.handgrading_result.submission.pk})

    def test_staff_has_access(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.client.force_authenticate(staff)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self.handgrading_result.to_dict(), response.data)

    def test_students_are_denied_acess(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.client.force_authenticate(enrolled)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateHandgradingResultsTestCase(test_impls.CreateObjectTest, UnitTestBase):
    """/api/submissions/<submission_pk>/handgrading_results/"""

    def setUp(self):
        super().setUp()
        submission = obj_build.build_submission()

        handgrading_rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
                max_points=0,
                show_grades_and_rubric_to_students=False,
                handgraders_can_leave_comments=True,
                handgraders_can_apply_arbitrary_points=True,
                project=submission.submission_group.project
            )
        )

        self.data = {
            "submission": submission.pk,
            "handgrading_rubric": handgrading_rubric.pk
        }

        self.course = handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('handgrading_results', kwargs={'submission_pk': submission.pk})

    def test_admin_valid_create(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_create_object_test(
            handgrading_models.HandgradingResult.objects, self.client, admin, self.url, self.data)

    def test_non_admin_create_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.do_permission_denied_create_test(
            handgrading_models.HandgradingResult.objects,
            self.client, enrolled, self.url, self.data)


class GetUpdateDeleteHandgradingResultTestCase(test_impls.GetObjectTest,
                                               test_impls.UpdateObjectTest,
                                               test_impls.DestroyObjectTest,
                                               UnitTestBase):
    """/api/handgrading_results/<pk>"""

    def setUp(self):
        super().setUp()
        project = obj_build.build_project()

        handgrading_rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
                max_points=0,
                show_grades_and_rubric_to_students=False,
                handgraders_can_leave_comments=True,
                handgraders_can_apply_arbitrary_points=True,
                project=project
            )
        )

        data = {
            "submission": obj_build.build_submission(),
            "handgrading_rubric": handgrading_rubric
        }

        self.handgrading_result = (
            handgrading_models.HandgradingResult.objects.validate_and_create(**data)
        )
        self.course = handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('handgrading-result-detail', kwargs={'pk': self.handgrading_result.pk})

    def test_staff_valid_get(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_get_object_test(self.client, staff, self.url, self.handgrading_result.to_dict())

    def test_non_staff_get_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.do_permission_denied_get_test(self.client, enrolled, self.url)

    # TODO: Can Handgrading Result be updated?
    # def test_admin_valid_update(self):
    #     patch_data = {
    #         'submission': '?'
    #     }
    #     [admin] = obj_build.make_admin_users(self.course, 1)
    #     self.do_patch_object_test(self.ag_test_suite, self.client, admin, self.url, patch_data)
    #
    # def test_admin_update_bad_values(self):
    #     patch_data = {
    #         'submission': '?'
    #     }
    #     [admin] = obj_build.make_admin_users(self.course, 1)
    #     self.do_patch_object_invalid_args_test(
    #         self.ag_test_suite, self.client, admin, self.url, patch_data)
    #
    # def test_non_admin_update_permission_denied(self):
    #     [staff] = obj_build.make_staff_users(self.course, 1)
    #     self.do_patch_object_permission_denied_test(
    #         self.ag_test_suite, self.client, staff, self.url, {'name': 'hello'})

    def test_admin_valid_delete(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_delete_object_test(self.handgrading_result, self.client, admin, self.url)

    def test_non_admin_delete_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_delete_object_permission_denied_test(
            self.handgrading_result, self.client, staff, self.url)
