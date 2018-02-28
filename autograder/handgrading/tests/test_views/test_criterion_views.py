from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import status
from rest_framework.test import APIClient

import autograder.handgrading.models as handgrading_models
import autograder.utils.testing.model_obj_builders as obj_build

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_test_impls as test_impls
import autograder.core.models as ag_models


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

        # Create HandgradingResult with dummy user and submission
        ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            project=self.handgrading_rubric.project,
            pattern='*', max_num_matches=10)
        submitted_files = [SimpleUploadedFile('file{}'.format(i), b'waaaluigi') for i in range(4)]
        submission = obj_build.build_submission(
            submission_group=obj_build.make_group(project=self.handgrading_rubric.project),
            submitted_files=submitted_files)
        handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            submission_group=submission.submission_group,
            handgrading_rubric=self.handgrading_rubric)

        self.assertEqual(0, handgrading_result.criterion_results.count())

        # Create Criterion, which should create a CriterionResult for above HandgradingResult
        response = self.client.post(self.url, self.data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        handgrading_result.refresh_from_db()
        self.assertEqual(1, handgrading_result.criterion_results.count())

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
