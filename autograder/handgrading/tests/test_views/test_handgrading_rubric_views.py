import unittest

from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.handgrading.models as handgrading_models
import autograder.utils.testing.model_obj_builders as obj_build

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls


class RetrieveHandgradingRubricTestCase(UnitTestBase):
    """/api/projects/<project_pk>/handgrading_rubric/"""

    def setUp(self):
        super().setUp()
        data = {
            'points_style': handgrading_models.PointsStyle.start_at_zero_and_add.value,
            'max_points': 20,
            'show_grades_and_rubric_to_students': True,
            'handgraders_can_leave_comments': True,
            'handgraders_can_adjust_points': True,
            'project': obj_build.build_project()
        }

        self.handgrading_rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(**data)
        )

        for _ in range(3):
            handgrading_models.Criterion.objects.validate_and_create(
                short_description="sample short description",
                long_description="sample loooooong description",
                points=0,
                handgrading_rubric=self.handgrading_rubric)

        criterion_order = self.handgrading_rubric.get_criterion_order()[::-1]
        self.handgrading_rubric.set_criterion_order(criterion_order)

        for _ in range(3):
            handgrading_models.Annotation.objects.validate_and_create(
                handgrading_rubric=self.handgrading_rubric)

        annotation_order = self.handgrading_rubric.get_annotation_order()[::-1]
        self.handgrading_rubric.set_annotation_order(annotation_order)

        self.course = self.handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('handgrading_rubric',
                           kwargs={'project_pk': self.handgrading_rubric.project.pk})

    def test_staff_valid_retrieve(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        [admin] = obj_build.make_admin_users(self.course, 1)
        [handgrader] = obj_build.make_users(1)
        self.handgrading_rubric.project.course.handgraders.add(handgrader)

        for user in [admin, staff, handgrader]:
            self.client.force_authenticate(user)
            response = self.client.get(self.url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertSequenceEqual(self.handgrading_rubric.to_dict(), response.data)

    def test_annotation_and_criterion_ordering(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.client.force_authenticate(admin)
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self.handgrading_rubric.to_dict(), response.data)

        response_criteria_order = [criteria["pk"] for criteria in response.data["criteria"]]
        response_annotation_order = [annotation["pk"]
                                     for annotation in response.data["annotations"]]

        self.assertSequenceEqual(response_criteria_order,
                                 self.handgrading_rubric.get_criterion_order())
        self.assertSequenceEqual(response_annotation_order,
                                 self.handgrading_rubric.get_annotation_order())

    def test_non_staff_retrieve_permission_denied(self):
        [enrolled] = obj_build.make_student_users(self.course, 1)
        self.client.force_authenticate(enrolled)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateHandgradingRubricTestCase(test_impls.CreateObjectTest, UnitTestBase):
    """/api/projects/<project_pk>/handgrading_rubric/"""

    def setUp(self):
        super().setUp()
        self.project = obj_build.build_project()
        self.course = self.project.course
        self.client = APIClient()
        self.url = reverse('handgrading_rubric', kwargs={'project_pk': self.project.pk})

        self.data = {
            'points_style': handgrading_models.PointsStyle.start_at_zero_and_add.value,
            'max_points': 20,
            'show_grades_and_rubric_to_students': True,
            'handgraders_can_leave_comments': True,
            'handgraders_can_adjust_points': True,
        }

    def test_admin_valid_create(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        response = self.do_create_object_test(handgrading_models.HandgradingRubric.objects,
                                              self.client, admin, self.url, self.data,
                                              check_data=False)

        loaded = handgrading_models.HandgradingRubric.objects.get(pk=response.data['pk'])
        self.assertDictContentsEqual(loaded.to_dict(), response.data)

        self.assertEqual(self.data["points_style"], loaded.points_style.value)
        self.assertEqual(self.data["max_points"], loaded.max_points)
        self.assertEqual(self.data["show_grades_and_rubric_to_students"],
                         loaded.show_grades_and_rubric_to_students)
        self.assertEqual(self.data["handgraders_can_leave_comments"],
                         loaded.handgraders_can_leave_comments)
        self.assertEqual(self.data["handgraders_can_adjust_points"],
                         loaded.handgraders_can_adjust_points)

    def test_non_admin_create_permission_denied(self):
        [enrolled] = obj_build.make_student_users(self.course, 1)
        [staff] = obj_build.make_staff_users(self.course, 1)
        [handgrader] = obj_build.make_users(1)
        self.project.course.handgraders.add(handgrader)

        for user in [enrolled, staff, handgrader]:
            self.do_permission_denied_create_test(handgrading_models.HandgradingRubric.objects,
                                                  self.client, user, self.url, self.data)


class GetUpdateDeleteHandgradingRubricTestCase(test_impls.GetObjectTest,
                                               test_impls.UpdateObjectTest,
                                               test_impls.DestroyObjectTest,
                                               UnitTestBase):
    """/api/handgrading_rubrics/<pk>"""

    def setUp(self):
        super().setUp()

        data = {
            'points_style': handgrading_models.PointsStyle.start_at_zero_and_add.value,
            'max_points': 20,
            'show_grades_and_rubric_to_students': True,
            'handgraders_can_leave_comments': True,
            'handgraders_can_adjust_points': True,
            'project': obj_build.build_project(),
        }

        self.handgrading_rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(**data)
        )
        self.course = self.handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('handgrading-rubric-detail', kwargs={'pk': self.handgrading_rubric.pk})

    def test_staff_valid_get(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_get_object_test(self.client, staff, self.url, self.handgrading_rubric.to_dict())

    def test_non_staff_get_permission_denied(self):
        [enrolled] = obj_build.make_student_users(self.course, 1)
        self.do_permission_denied_get_test(self.client, enrolled, self.url)

    def test_admin_valid_update(self):
        patch_data = {
            'points_style': 'start_at_max_and_subtract',
            'max_points': 10,
            'show_grades_and_rubric_to_students': False,
            'handgraders_can_leave_comments': False,
            'handgraders_can_adjust_points': False
        }
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_patch_object_test(
            self.handgrading_rubric, self.client, admin, self.url, patch_data)

    def test_admin_update_bad_values(self):
        bad_data = {
            'points_style': 'incorrect_enum_field',
            'max_points': -10,
        }
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_patch_object_invalid_args_test(
            self.handgrading_rubric, self.client, admin, self.url, bad_data)

    def test_non_admin_update_permission_denied(self):
        patch_data = {
            'max_points': 30,
        }
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_patch_object_permission_denied_test(
            self.handgrading_rubric, self.client, staff, self.url, patch_data)

    def test_admin_valid_delete(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_delete_object_test(self.handgrading_rubric, self.client, admin, self.url)

    def test_non_admin_delete_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_delete_object_permission_denied_test(
            self.handgrading_rubric, self.client, staff, self.url)
