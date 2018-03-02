from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.handgrading.models as handgrading_models
import autograder.utils.testing.model_obj_builders as obj_build

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class ListCriteriaTestCase(UnitTestBase):
    """/api/handgrading_rubric/<handgrading_rubric_pk>/criteria"""

    def setUp(self):
        super().setUp()
        handgrading_rubric_inputs = {
            "points_style": handgrading_models.PointsStyle.start_at_max_and_subtract,
            "max_points": 0,
            "show_grades_and_rubric_to_students": False,
            "handgraders_can_leave_comments": True,
            "handgraders_can_adjust_points": True,
            "project": obj_build.build_project()
        }

        self.handgrading_rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                **handgrading_rubric_inputs)
        )

        self.default_criterion = {
            "short_description": "Sample short description.",
            "long_description": "Sample loooooooong description.",
            "points": 20,
            "handgrading_rubric": self.handgrading_rubric
        }

        self.criterion = handgrading_models.Criterion.objects.validate_and_create(
            **self.default_criterion)

        self.course = self.handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('criteria',
                           kwargs={'handgrading_rubric_pk': self.handgrading_rubric.pk})

    def test_staff_valid_list_cases(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.client.force_authenticate(staff)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(self.criterion.to_dict(), response.data[0])

    def test_non_staff_list_cases_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.client.force_authenticate(enrolled)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateCriterionTestCase(test_impls.CreateObjectTest, UnitTestBase):
    """/api/handgrading_rubric/<handgrading_rubric_pk>/criteria"""

    def setUp(self):
        super().setUp()
        self.handgrading_rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
                points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
                max_points=0,
                show_grades_and_rubric_to_students=False,
                handgraders_can_leave_comments=True,
                handgraders_can_adjust_points=True,
                project=obj_build.build_project())

        self.course = self.handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('criteria',
                           kwargs={'handgrading_rubric_pk': self.handgrading_rubric.pk})

        self.data = {
            "short_description": "Sample short description.",
            "long_description": "Sample loooooooong description.",
            "points": 20,
        }

    def test_admin_valid_create(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_create_object_test(
            handgrading_models.Criterion.objects, self.client, admin, self.url, self.data)

    def test_non_admin_create_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.do_permission_denied_create_test(
            handgrading_models.Criterion.objects, self.client, enrolled, self.url, self.data)

    def test_create_criterion_results_on_create(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.client.force_authenticate(admin)

        # Create HandgradingResult
        submission = obj_build.build_submission(
            submission_group=obj_build.make_group(project=self.handgrading_rubric.project))
        handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            submission_group=submission.submission_group,
            handgrading_rubric=self.handgrading_rubric)

        # Create dummy submissions and groups with no submissions. These should not be affected
        dummy_submission = obj_build.build_submission(
            submission_group=obj_build.make_group(project=self.handgrading_rubric.project))
        dummy_submission = obj_build.build_submission(
            submission_group=obj_build.make_group(project=self.handgrading_rubric.project))
        group_with_no_submission = obj_build.make_group(project=self.handgrading_rubric.project)
        group_with_no_submission = obj_build.make_group(project=self.handgrading_rubric.project)

        self.assertEqual(0, handgrading_result.criterion_results.count())
        self.assertEqual(1, handgrading_models.HandgradingResult.objects.count())

        # Create dummy project with its own groups and HandgradingResults.
        #   These should not be affected
        dummy_project = obj_build.make_project(course=self.handgrading_rubric.project.course)
        dummy_handgrading_rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
                points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
                max_points=0,
                show_grades_and_rubric_to_students=False,
                handgraders_can_leave_comments=True,
                handgraders_can_adjust_points=True,
                project=dummy_project)
        dummy_submission = obj_build.build_submission(
            submission_group=obj_build.make_group(project=self.handgrading_rubric.project))
        dummy_handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=dummy_submission,
            submission_group=dummy_submission.submission_group,
            handgrading_rubric=dummy_handgrading_rubric)

        self.assertEqual(0, handgrading_models.CriterionResult.objects.count())
        self.assertEqual(2, handgrading_models.HandgradingResult.objects.count())

        # Create Criterion, which should create a CriterionResult for above HandgradingResult
        response = self.client.post(self.url, self.data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        handgrading_result.refresh_from_db()
        self.assertEqual(1, handgrading_result.criterion_results.count())
        self.assertEqual(1, handgrading_models.CriterionResult.objects.count())

        criterion_results = handgrading_result.to_dict()["criterion_results"]
        self.assertFalse(criterion_results[0]["selected"])
        self.assertEqual(criterion_results[0]["criterion"], response.data)


class GetUpdateDeleteCriterionTestCase(test_impls.GetObjectTest,
                                       test_impls.UpdateObjectTest,
                                       test_impls.DestroyObjectTest,
                                       UnitTestBase):
    """/api/criteria/<pk>/"""

    def setUp(self):
        super().setUp()

        handgrading_rubric_inputs = {
            "points_style": handgrading_models.PointsStyle.start_at_max_and_subtract,
            "max_points": 0,
            "show_grades_and_rubric_to_students": False,
            "handgraders_can_leave_comments": True,
            "handgraders_can_adjust_points": True,
            "project": obj_build.build_project()
        }

        self.handgrading_rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                **handgrading_rubric_inputs)
        )

        criterion_data = {
            "short_description": "Sample short description.",
            "long_description": "Sample loooooooong description.",
            "points": 20,
            "handgrading_rubric": self.handgrading_rubric
        }

        self.criterion = handgrading_models.Criterion.objects.validate_and_create(**criterion_data)
        self.course = self.handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('criterion-detail', kwargs={'pk': self.criterion.pk})

    def test_staff_valid_get(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_get_object_test(self.client, staff, self.url, self.criterion.to_dict())

    def test_non_staff_get_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.do_permission_denied_get_test(self.client, enrolled, self.url)

    def test_admin_valid_update(self):
        patch_data = {
            "short_description": "Changing short description.",
            "long_description": "Changing loooooooong description.",
            "points": 40,
        }
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_patch_object_test(
            self.criterion, self.client, admin, self.url, patch_data)

    def test_admin_update_bad_values(self):
        bad_data = {
            "points": "something_wrong",
            "long_description": 12,
            "short_description": 12,
        }
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_patch_object_invalid_args_test(
            self.criterion, self.client, admin, self.url, bad_data)

    def test_non_admin_update_permission_denied(self):
        patch_data = {
            "short_description": "Changing short description.",
            "long_description": "Changing loooooooong description.",
            "points": 40,
        }
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_patch_object_permission_denied_test(
            self.criterion, self.client, staff, self.url, patch_data)

    def test_admin_valid_delete(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_delete_object_test(self.criterion, self.client, admin, self.url)

    def test_non_admin_delete_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_delete_object_permission_denied_test(
            self.criterion, self.client, staff, self.url)


class CriterionOrderTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        handgrading_rubric_inputs = {
            "points_style": handgrading_models.PointsStyle.start_at_max_and_subtract,
            "max_points": 0,
            "show_grades_and_rubric_to_students": False,
            "handgraders_can_leave_comments": True,
            "handgraders_can_adjust_points": True,
            "project": obj_build.build_project()
        }

        self.handgrading_rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                **handgrading_rubric_inputs)
        )

        criterion_data = {
            "short_description": "Sample short description.",
            "long_description": "Sample loooooooong description.",
            "points": 20,
            "handgrading_rubric": self.handgrading_rubric
        }

        self.criterion1 = handgrading_models.Criterion.objects.validate_and_create(
            **criterion_data)
        self.criterion2 = handgrading_models.Criterion.objects.validate_and_create(
            **criterion_data)

        self.course = self.handgrading_rubric.project.course

        self.client = APIClient()
        self.url = reverse('criterion_order',
                           kwargs={'handgrading_rubric_pk': self.handgrading_rubric.pk})

    def test_staff_get_order(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        [admin] = obj_build.make_admin_users(self.course, 1)
        for user in staff, admin:
            self.client.force_authenticate(user)

            new_order = [self.criterion1.pk, self.criterion2.pk]
            self.handgrading_rubric.set_criterion_order(new_order)
            response = self.client.get(self.url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertSequenceEqual([self.criterion1.pk, self.criterion2.pk], response.data)

            new_order = [self.criterion2.pk, self.criterion1.pk]
            self.handgrading_rubric.set_criterion_order(new_order)
            response = self.client.get(self.url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertSequenceEqual(new_order, response.data)

    def test_non_staff_get_order_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)

        for user in enrolled, handgrader:
            self.client.force_authenticate(user)

            response = self.client.get(self.url)
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_admin_set_order(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.client.force_authenticate(admin)

        reverse_order = self.handgrading_rubric.get_criterion_order()[::-1]
        response = self.client.put(self.url, reverse_order)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(reverse_order, self.handgrading_rubric.get_criterion_order())

    def test_non_admin_set_order_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)

        for user in staff, enrolled, handgrader:
            self.client.force_authenticate(user)

            original_order = list(self.handgrading_rubric.get_criterion_order())
            response = self.client.put(self.url, original_order[::-1])

            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
            self.assertSequenceEqual(original_order, self.handgrading_rubric.get_criterion_order())
