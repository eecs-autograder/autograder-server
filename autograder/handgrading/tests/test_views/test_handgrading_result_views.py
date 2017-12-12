from django.core.urlresolvers import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.handgrading.models as handgrading_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.models import Submission
from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class RetrieveHandgradingResultsTestCase(UnitTestBase):
    """/api/submission_groups/<group_pk>/handgrading_result/"""

    def setUp(self):
        super().setUp()
        self.submission = obj_build.build_submission(
            status=Submission.GradingStatus.finished_grading)

        self.handgrading_rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
                max_points=0,
                show_grades_and_rubric_to_students=False,
                handgraders_can_leave_comments=True,
                handgraders_can_apply_arbitrary_points=True,
                project=self.submission.submission_group.project
            )
        )

        self.data = {
            "submission": self.submission,
            "submission_group": self.submission.submission_group,
            "handgrading_rubric": self.handgrading_rubric
        }

        self.client = APIClient()
        self.course = self.handgrading_rubric.project.course
        self.url = reverse('handgrading_result',
                           kwargs={'group_pk': self.submission.submission_group.pk})

    def test_staff_has_access(self):
        handgrading_result = (
            handgrading_models.HandgradingResult.objects.validate_and_create(**self.data)
        )
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.client.force_authenticate(staff)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(handgrading_result.to_dict(), response.data)

    def test_students_are_denied_acess(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.client.force_authenticate(enrolled)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_create_if_does_not_exist(self):
        expected_fields = {
            'pk',
            'last_modified',

            'submission',
            'handgrading_rubric',
            'submission_group',

            'applied_annotations',
            'arbitrary_points',
            'comments',
            'criterion_results',
        }
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.client.force_authenticate(staff)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(expected_fields, response.data.keys())


class CreateHandgradingResultsTestCase(test_impls.CreateObjectTest, UnitTestBase):
    """/api/submission_groups/<group_pk>/handgrading_result/"""

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
            "submission": submission,
            "handgrading_rubric": handgrading_rubric
        }

        self.course = handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('handgrading_result', kwargs={
            'group_pk': submission.submission_group.pk})

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

        submission = obj_build.build_submission(
            status=Submission.GradingStatus.finished_grading)

        data = {
            "submission": submission,
            "submission_group": submission.submission_group,
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

    def test_admin_valid_delete(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_delete_object_test(self.handgrading_result, self.client, admin, self.url)

    def test_non_admin_delete_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_delete_object_permission_denied_test(
            self.handgrading_result, self.client, staff, self.url)
