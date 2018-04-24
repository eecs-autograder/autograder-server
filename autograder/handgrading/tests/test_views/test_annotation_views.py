from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.handgrading.models as handgrading_models
import autograder.utils.testing.model_obj_builders as obj_build

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls


class ListAnnotationsTestCase(UnitTestBase):
    """/api/handgrading_rubric/<handgrading_rubric_pk>/annotations"""

    def setUp(self):
        super().setUp()
        handgrading_rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
                max_points=0,
                show_grades_and_rubric_to_students=False,
                handgraders_can_leave_comments=True,
                handgraders_can_adjust_points=True,
                project=obj_build.build_project())
        )

        self.annotation = handgrading_models.Annotation.objects.validate_and_create(
            short_description="Short description text.",
            long_description="Looooong description text.",
            deduction=-3,
            handgrading_rubric=handgrading_rubric)

        self.course = handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('annotations',
                           kwargs={'handgrading_rubric_pk': handgrading_rubric.pk})

    def test_staff_valid_list_cases(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.client.force_authenticate(staff)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(self.annotation.to_dict(), response.data[0])

    def test_non_staff_list_cases_permission_denied(self):
        [enrolled] = obj_build.make_student_users(self.course, 1)
        self.client.force_authenticate(enrolled)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateAnnotationTestCase(test_impls.CreateObjectTest, UnitTestBase):
    """/api/handgrading_rubric/<handgrading_rubric_pk>/annotations"""

    def setUp(self):
        super().setUp()
        self.handgrading_rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
                max_points=0,
                show_grades_and_rubric_to_students=False,
                handgraders_can_leave_comments=True,
                handgraders_can_adjust_points=True,
                project=obj_build.build_project())
        )

        self.course = self.handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('annotations',
                           kwargs={'handgrading_rubric_pk': self.handgrading_rubric.pk})

        self.data = {
            "short_description": "Sample short description.",
            "long_description": "Sample loooooooong description.",
            "deduction": -3,
        }

    def test_admin_valid_create(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_create_object_test(
            handgrading_models.Annotation.objects, self.client, admin, self.url, self.data)

    def test_non_admin_create_permission_denied(self):
        [enrolled] = obj_build.make_student_users(self.course, 1)
        self.do_permission_denied_create_test(
            handgrading_models.Annotation.objects, self.client, enrolled, self.url, self.data)


class GetUpdateDeleteAnnotationTestCase(test_impls.GetObjectTest,
                                        test_impls.UpdateObjectTest,
                                        test_impls.DestroyObjectTest,
                                        UnitTestBase):
    """/api/annotations/<pk>/"""

    def setUp(self):
        super().setUp()
        handgrading_rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
                points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
                max_points=0,
                show_grades_and_rubric_to_students=False,
                handgraders_can_leave_comments=True,
                handgraders_can_adjust_points=True,
                project=obj_build.build_project())

        self.annotation = handgrading_models.Annotation.objects.validate_and_create(
            short_description="Short description text.",
            long_description="Looooong description text.",
            deduction=-3,
            handgrading_rubric=handgrading_rubric)

        self.course = handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('annotation-detail', kwargs={'pk': self.annotation.pk})

    def test_staff_valid_get(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_get_object_test(self.client, staff, self.url, self.annotation.to_dict())

    def test_non_staff_get_permission_denied(self):
        [enrolled] = obj_build.make_student_users(self.course, 1)
        self.do_permission_denied_get_test(self.client, enrolled, self.url)

    def test_admin_valid_update(self):
        patch_data = {
            "short_description": "Changing short description.",
            "long_description": "Changing loooooooong description.",
            "deduction": -5,
        }
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_patch_object_test(
            self.annotation, self.client, admin, self.url, patch_data)

    def test_admin_update_bad_values(self):
        bad_data = {
            "deduction": 42,
        }
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_patch_object_invalid_args_test(
            self.annotation, self.client, admin, self.url, bad_data)

    def test_non_admin_update_permission_denied(self):
        patch_data = {
            "short_description": "Changing short description.",
            "long_description": "Changing loooooooong description.",
            "deduction": -5,
        }
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_patch_object_permission_denied_test(
            self.annotation, self.client, staff, self.url, patch_data)

    def test_admin_valid_delete(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_delete_object_test(self.annotation, self.client, admin, self.url)

    def test_non_admin_delete_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_delete_object_permission_denied_test(
            self.annotation, self.client, staff, self.url)


class AnnotationOrderTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.handgrading_rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
                max_points=0,
                show_grades_and_rubric_to_students=False,
                handgraders_can_leave_comments=True,
                handgraders_can_adjust_points=True,
                project=obj_build.build_project())
        )

        self.annotation1 = handgrading_models.Annotation.objects.validate_and_create(
            short_description="Short description text.",
            long_description="Looooong description text.",
            deduction=-3,
            handgrading_rubric=self.handgrading_rubric)

        self.annotation2 = handgrading_models.Annotation.objects.validate_and_create(
            short_description="Short description text #2.",
            long_description="Looooong description text #2.",
            deduction=-6,
            handgrading_rubric=self.handgrading_rubric)

        self.course = self.handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('annotation_order',
                           kwargs={'handgrading_rubric_pk': self.handgrading_rubric.pk})

    def test_staff_get_order(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        [admin] = obj_build.make_admin_users(self.course, 1)

        for user in staff, admin:
            self.client.force_authenticate(user)

            new_order = [self.annotation1.pk, self.annotation2.pk]
            self.handgrading_rubric.set_annotation_order(new_order)
            response = self.client.get(self.url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertSequenceEqual([self.annotation1.pk, self.annotation2.pk], response.data)

            new_order = [self.annotation2.pk, self.annotation1.pk]
            self.handgrading_rubric.set_annotation_order(new_order)
            response = self.client.get(self.url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertSequenceEqual(new_order, response.data)

    def test_non_staff_get_order_permission_denied(self):
        [enrolled] = obj_build.make_student_users(self.course, 1)
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)

        for user in enrolled, handgrader:
            self.client.force_authenticate(user)

            response = self.client.get(self.url)
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_admin_set_order(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.client.force_authenticate(admin)

        reverse_order = self.handgrading_rubric.get_annotation_order()[::-1]
        response = self.client.put(self.url, reverse_order)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(reverse_order, self.handgrading_rubric.get_annotation_order())

    def test_non_admin_set_order_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        [enrolled] = obj_build.make_student_users(self.course, 1)
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)

        for user in staff, enrolled, handgrader:
            self.client.force_authenticate(user)

            original_order = list(self.handgrading_rubric.get_annotation_order())
            response = self.client.put(self.url, original_order[::-1])

            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
            self.assertSequenceEqual(original_order, self.handgrading_rubric.get_annotation_order())
