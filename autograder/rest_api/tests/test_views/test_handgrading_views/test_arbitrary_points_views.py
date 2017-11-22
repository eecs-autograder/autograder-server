from django.core.urlresolvers import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.handgrading.models as handgrading_models
import autograder.utils.testing.model_obj_builders as obj_build

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class ListArbitraryPointsTestCase(UnitTestBase):
    """/api/handgrading_results/<handgrading_result_pk>/arbitrary_points"""

    def setUp(self):
        super().setUp()
        self.handgrdaing_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=obj_build.build_submission(submitted_filenames=["test.cpp"])
        )

        arbitrary_points_data = {
            "location": {
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            "text": "",
            "points": 0,
            "handgrading_result": self.handgrdaing_result
        }

        self.arbitrary_points = handgrading_models.ArbitraryPoints.objects.validate_and_create(
            **arbitrary_points_data)

        self.course = self.handgrading_result.submission.submission_group.project.course
        self.client = APIClient()
        self.url = reverse('arbitrary_points',
                           kwargs={'handgrading_result_pk': self.handgrading_result.pk})

    def test_staff_valid_list_cases(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.client.force_authenticate(staff)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(self.arbitrary_points.to_dict(), response.data)

    def test_non_staff_list_cases_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.client.force_authenticate(enrolled)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateArbitraryPointsTestCase(test_impls.CreateObjectTest, UnitTestBase):
    """/api/handgrading_results/<handgrading_result_pk>/arbitrary_points"""

    def setUp(self):
        super().setUp()
        self.handgrdaing_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=obj_build.build_submission(submitted_filenames=["test.cpp"])
        )

        self.course = self.handgrading_result.submission.submission_group.project.course
        self.client = APIClient()
        self.url = reverse('arbitrary_points',
                           kwargs={'handgrading_result_pk': self.handgrading_result.pk})

    def test_admin_valid_create(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        data = {
            "location": {
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            "text": "",
            "points": 0,
            "handgrading_result": self.handgrdaing_result
        }
        self.do_create_object_test(
            handgrading_models.ArbitraryPoints.objects, self.client, admin, self.url, data)

    def test_non_admin_create_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        data = {
            "location": {
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            "text": "",
            "points": 0,
            "handgrading_result": self.handgrdaing_result
        }
        self.do_permission_denied_create_test(
            handgrading_models.ArbitraryPoints.objects, self.client, enrolled, self.url, data)


class GetUpdateDeleteArbitraryPointsTestCase(test_impls.GetObjectTest,
                                             test_impls.UpdateObjectTest,
                                             test_impls.DestroyObjectTest,
                                             UnitTestBase):
    """/api/arbitrary_points/<pk>/"""

    def setUp(self):
        super().setUp()
        self.handgrdaing_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=obj_build.build_submission(submitted_filenames=["test.cpp"])
        )

        arbitrary_points_data = {
            "location": {
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            "text": "Sample text.",
            "points": 10,
            "handgrading_result": self.handgrdaing_result
        }

        self.arbitrary_points = handgrading_models.ArbitraryPoints.objects.validate_and_create(
            **arbitrary_points_data)

        self.course = self.handgrading_result.submission.submission_group.project.course
        self.client = APIClient()
        self.url = reverse('arbitrary-points-detail',
                           kwargs={'pk': self.arbitrary_points.pk})

    def test_staff_valid_get(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_get_object_test(self.client, staff, self.url, self.arbitrary_points.to_dict())

    def test_non_staff_get_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.do_permission_denied_get_test(self.client, enrolled, self.url)

    def test_admin_valid_update(self):
        patch_data = {
            "text": "Change sample text.",
            "points": 20,
        }
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_patch_object_test(
            self.arbitrary_points, self.client, admin, self.url, patch_data)

    def test_admin_update_bad_values(self):
        bad_data = {
            "points": -20,
        }
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_patch_object_invalid_args_test(
            self.arbitrary_points, self.client, admin, self.url, bad_data)

    def test_non_admin_update_permission_denied(self):
        patch_data = {
            "text": "Change sample text.",
            "points": 30,
        }
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_patch_object_permission_denied_test(
            self.arbitrary_points, self.client, staff, self.url, patch_data)

    def test_admin_valid_delete(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_delete_object_test(self.arbitrary_points, self.client, admin, self.url)

    def test_non_admin_delete_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        self.do_delete_object_permission_denied_test(
            self.arbitrary_points, self.client, staff, self.url)
