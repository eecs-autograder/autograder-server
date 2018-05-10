from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.handgrading.models as handgrading_models
import autograder.utils.testing.model_obj_builders as obj_build

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls


class ListCriterionResultsTestCase(UnitTestBase):
    """/api/handgrading_results/<handgrading_result_pk>/criterion_results"""

    def setUp(self):
        super().setUp()
        handgrading_rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
            points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
            max_points=0,
            show_grades_and_rubric_to_students=False,
            handgraders_can_leave_comments=True,
            handgraders_can_adjust_points=True,
            project=obj_build.build_project()
        )

        criterion = handgrading_models.Criterion.objects.validate_and_create(
            points=0,
            handgrading_rubric=handgrading_rubric
        )

        submission = obj_build.build_submission()

        self.handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            group=submission.group,
            handgrading_rubric=handgrading_rubric
        )

        criterion_result_data = {
            "selected": True,
            "criterion": criterion,
            "handgrading_result": self.handgrading_result
        }

        self.criterion_result = handgrading_models.CriterionResult.objects.validate_and_create(
            **criterion_result_data)

        self.course = handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('criterion_results',
                           kwargs={'handgrading_result_pk': self.handgrading_result.pk})

    def test_admin_or_staff_or_handgrader_valid_list_criterion_results(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        [staff] = obj_build.make_staff_users(self.course, 1)
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)

        for user in admin, staff, handgrader:
            self.client.force_authenticate(user)

            response = self.client.get(self.url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertSequenceEqual(self.criterion_result.to_dict(), response.data[0])

    def test_student_list_criterion_results_permission_denied(self):
        [enrolled] = obj_build.make_student_users(self.course, 1)
        self.client.force_authenticate(enrolled)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateCriterionResultTestCase(test_impls.CreateObjectTest, UnitTestBase):
    """/api/handgrading_results/<handgrading_result_pk>/criterion_results"""

    def setUp(self):
        super().setUp()
        handgrading_rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
            points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
            max_points=0,
            show_grades_and_rubric_to_students=False,
            handgraders_can_leave_comments=True,
            handgraders_can_adjust_points=True,
            project=obj_build.build_project()
        )

        self.criterion = handgrading_models.Criterion.objects.validate_and_create(
            points=0,
            handgrading_rubric=handgrading_rubric
        )

        submission = obj_build.build_submission(submitted_filenames=["test.cpp"])

        self.handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            group=submission.group,
            handgrading_rubric=handgrading_rubric
        )

        self.course = handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('criterion_results',
                           kwargs={'handgrading_result_pk': self.handgrading_result.pk})

        self.data = {
            "selected": True,
            "criterion": self.criterion.pk,
        }

    def test_admin_or_handgrader_valid_create(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        [handgrader] = obj_build.make_admin_users(self.course, 1)

        for user in admin, handgrader:
            response = self.do_create_object_test(handgrading_models.CriterionResult.objects,
                                                  self.client, user, self.url, self.data,
                                                  check_data=False)

            loaded = handgrading_models.CriterionResult.objects.get(pk=response.data['pk'])
            self.assertDictContentsEqual(loaded.to_dict(), response.data)

            criterion = handgrading_models.Criterion.objects.get(pk=self.data['criterion'])

            self.assertEqual(self.data["selected"], loaded.selected)
            self.assertEqual(criterion.to_dict(), loaded.criterion.to_dict())

    def test_student_create_permission_denied(self):
        [enrolled] = obj_build.make_student_users(self.course, 1)
        self.do_permission_denied_create_test(handgrading_models.CriterionResult.objects,
                                              self.client, enrolled, self.url, self.data)


class GetUpdateDeleteCriterionResultTestCase(test_impls.GetObjectTest,
                                             test_impls.UpdateObjectTest,
                                             test_impls.DestroyObjectTest,
                                             UnitTestBase):
    """/api/criterion_results/<pk>/"""

    def setUp(self):
        super().setUp()
        handgrading_rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
            points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
            max_points=0,
            show_grades_and_rubric_to_students=False,
            handgraders_can_leave_comments=True,
            handgraders_can_adjust_points=True,
            project=obj_build.build_project()
        )

        criterion = handgrading_models.Criterion.objects.validate_and_create(
            points=0,
            handgrading_rubric=handgrading_rubric
        )

        submission = obj_build.build_submission(submitted_filenames=["test.cpp"])

        self.handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            group=submission.group,
            handgrading_rubric=handgrading_rubric
        )

        criterion_result_data = {
            "selected": True,
            "criterion": criterion,
            "handgrading_result": self.handgrading_result
        }

        self.criterion_result = handgrading_models.CriterionResult.objects.validate_and_create(
            **criterion_result_data)

        self.course = handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('criterion-result-detail', kwargs={'pk': self.criterion_result.pk})

    def test_admin_or_staff_or_handgrader_valid_get(self):
        [admin] = obj_build.make_staff_users(self.course, 1)
        [staff] = obj_build.make_staff_users(self.course, 1)
        [handgrader] = obj_build.make_staff_users(self.course, 1)

        for user in admin, staff, handgrader:
            self.do_get_object_test(self.client, user, self.url, self.criterion_result.to_dict())

    def test_student_get_permission_denied(self):
        [enrolled] = obj_build.make_student_users(self.course, 1)
        self.do_permission_denied_get_test(self.client, enrolled, self.url)

    def test_admin_or_handgradre_valid_update(self):
        patch_data = {"selected": False}
        [admin] = obj_build.make_admin_users(self.course, 1)
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)

        for user in admin, handgrader:
            self.do_patch_object_test(
                self.criterion_result, self.client, user, self.url, patch_data)

    def test_admin_or_handgrader_update_bad_values(self):
        bad_data = {"selected": "not a boolean"}
        [admin] = obj_build.make_admin_users(self.course, 1)
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)

        for user in admin, handgrader:
            self.do_patch_object_invalid_args_test(self.criterion_result, self.client, user,
                                                   self.url, bad_data)

    def test_staff_or_student_update_permission_denied(self):
        patch_data = {"selected": False}
        [staff] = obj_build.make_staff_users(self.course, 1)
        [student] = obj_build.make_student_users(self.course, 1)

        for user in staff, student:
            self.do_patch_object_permission_denied_test(self.criterion_result, self.client, user,
                                                        self.url, patch_data)

    def test_admin_valid_delete(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_delete_object_test(self.criterion_result, self.client, admin, self.url)

    def test_handgrader_valid_delete(self):
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)
        self.do_delete_object_test(self.criterion_result, self.client, handgrader, self.url)

    def test_staff_or_student_delete_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        [student] = obj_build.make_student_users(self.course, 1)

        for user in staff, student:
            self.do_delete_object_permission_denied_test(
                self.criterion_result, self.client, user, self.url)
