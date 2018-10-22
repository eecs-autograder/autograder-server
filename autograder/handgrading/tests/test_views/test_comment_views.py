from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.handgrading.models as handgrading_models
import autograder.utils.testing.model_obj_builders as obj_build

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls


class ListCommentsTestCase(UnitTestBase):
    """/api/handgrading_results/<handgrading_result_pk>/comments"""

    def setUp(self):
        super().setUp()
        handgrading_rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
            points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
            max_points=0,
            show_grades_and_rubric_to_students=False,
            handgraders_can_leave_comments=False,
            handgraders_can_adjust_points=True,
            project=obj_build.build_project()
        )

        submission = obj_build.make_submission(submitted_filenames=["test.cpp"])

        self.handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            group=submission.group,
            handgrading_rubric=handgrading_rubric
        )

        comment_data = {
            "location": {
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            "text": "Sample comment text.",
            "handgrading_result": self.handgrading_result
        }

        self.comment = handgrading_models.Comment.objects.validate_and_create(**comment_data)
        self.course = handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('comments',
                           kwargs={'handgrading_result_pk': self.handgrading_result.pk})

    def test_admin_or_staff_or_handgrader_valid_list_comments(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        [staff] = obj_build.make_staff_users(self.course, 1)
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)

        for user in admin, handgrader, staff:
            self.client.force_authenticate(user)

            response = self.client.get(self.url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertSequenceEqual(self.comment.to_dict(), response.data[0])

    def test_student_list_comments_permission_denied(self):
        [enrolled] = obj_build.make_student_users(self.course, 1)
        self.client.force_authenticate(enrolled)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateCommentTestCase(test_impls.CreateObjectTest, UnitTestBase):
    """/api/handgrading_results/<handgrading_result_pk>/comments"""

    def setUp(self):
        super().setUp()
        self.handgrading_rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
            points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
            max_points=0,
            show_grades_and_rubric_to_students=False,
            handgraders_can_leave_comments=False,
            handgraders_can_adjust_points=True,
            project=obj_build.build_project()
        )

        submission = obj_build.make_submission(submitted_filenames=["test.cpp"])

        self.handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            group=submission.group,
            handgrading_rubric=self.handgrading_rubric
        )

        self.course = self.handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('comments',
                           kwargs={'handgrading_result_pk': self.handgrading_result.pk})

        self.data = {
            "location": {
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            "text": "Sample comment text.",
        }

    def test_admin_or_staff_valid_create_with_location(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        [staff] = obj_build.make_staff_users(self.course, 1)

        for user in admin, staff:
            response = self.do_create_object_test(handgrading_models.Comment.objects, self.client,
                                                  user, self.url, self.data, check_data=False)
            self._check_valid_comment_with_location_created(response)

    def test_handgrader_valid_create_with_location(self):
        self.handgrading_rubric.validate_and_update(handgraders_can_leave_comments=True)
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)
        response = self.do_create_object_test(handgrading_models.Comment.objects, self.client,
                                              handgrader, self.url, self.data, check_data=False)
        self._check_valid_comment_with_location_created(response)

    def test_admin_or_staff_valid_create_without_location(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        [staff] = obj_build.make_staff_users(self.course, 1)
        data = {"text": "Sample comment text."}

        for user in admin, staff:
            self.do_create_object_test(handgrading_models.Comment.objects, self.client, user,
                                       self.url, data)

    def test_handgrader_valid_create_can_leave_comments_without_location(self):
        self.handgrading_rubric.validate_and_update(handgraders_can_leave_comments=True)
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)
        data = {"text": "Sample comment text."}

        self.do_create_object_test(handgrading_models.Comment.objects, self.client, handgrader,
                                   self.url, data)

    def test_enrolled_create_permission_denied(self):
        [enrolled] = obj_build.make_student_users(self.course, 1)
        self.do_permission_denied_create_test(handgrading_models.Comment.objects, self.client,
                                              enrolled, self.url, self.data)

    def test_handgrader_comments_not_allowed_permission_denied(self):
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)
        self.do_permission_denied_create_test(handgrading_models.Comment.objects, self.client,
                                              handgrader, self.url, self.data)

    def _check_valid_comment_with_location_created(self, response):
        loaded = handgrading_models.Comment.objects.get(pk=response.data['pk'])
        self.assert_dict_contents_equal(loaded.to_dict(), response.data)

        self.assertEqual(self.data["text"], loaded.text)
        response_location_dict = loaded.location.to_dict()

        for non_modifiable in ["pk", "last_modified"]:
            response_location_dict.pop(non_modifiable)

        self.assertEqual(self.data["location"], response_location_dict)


class GetUpdateDeleteCommentTestCase(test_impls.GetObjectTest,
                                     test_impls.UpdateObjectTest,
                                     test_impls.DestroyObjectTest,
                                     UnitTestBase):
    """/api/comments/<pk>/"""

    def setUp(self):
        super().setUp()
        self.handgrading_rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
            points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
            max_points=0,
            show_grades_and_rubric_to_students=False,
            handgraders_can_leave_comments=False,
            handgraders_can_adjust_points=True,
            project=obj_build.build_project()
        )

        submission = obj_build.make_submission(submitted_filenames=["test.cpp"])

        self.handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            group=submission.group,
            handgrading_rubric=self.handgrading_rubric
        )

        comment_data = {
            "location": {
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            "text": "Sample comment text.",
            "handgrading_result": self.handgrading_result
        }

        self.comment = handgrading_models.Comment.objects.validate_and_create(**comment_data)
        self.comment2 = handgrading_models.Comment.objects.validate_and_create(**comment_data)
        self.course = self.handgrading_rubric.project.course
        self.client = APIClient()
        self.url = reverse('comment-detail', kwargs={'pk': self.comment.pk})

        [self.admin] = obj_build.make_admin_users(self.course, 1)
        [self.staff] = obj_build.make_staff_users(self.course, 1)
        [self.handgrader] = obj_build.make_handgrader_users(self.course, 1)
        [self.student] = obj_build.make_student_users(self.course, 1)

    def test_admin_or_staff_or_handgrader_valid_get(self):
        for user in self.admin, self.staff, self.handgrader:
            self.do_get_object_test(self.client, user, self.url, self.comment.to_dict())

    def test_student_get_permission_denied(self):
        self.do_permission_denied_get_test(self.client, self.student, self.url)

    def test_admin_or_staff_or_handgrader_valid_update(self):
        patch_data = {"text": "Changing comment text."}

        for user in self.admin, self.staff:
            self.do_patch_object_test(self.comment, self.client, user, self.url, patch_data)

    def test_handgrader_valid_update_when_can_leave_comment(self):
        patch_data = {"text": "Changing comment text."}
        self.handgrading_rubric.validate_and_update(handgraders_can_leave_comments=True)

        self.do_patch_object_test(self.comment, self.client, self.handgrader, self.url, patch_data)

    def test_admin_or_staff_update_bad_values(self):
        bad_data = {"location": "Location isn't editable!"}

        for user in self.admin, self.staff:
            self.do_patch_object_invalid_args_test(self.comment, self.client, user, self.url,
                                                   bad_data)

    def test_handgrader_update_bad_values_when_can_leave_comment(self):
        bad_data = {"location": "Location isn't editable!"}
        self.handgrading_rubric.validate_and_update(handgraders_can_leave_comments=True)

        self.do_patch_object_invalid_args_test(self.comment, self.client, self.handgrader,
                                               self.url, bad_data)

    def test_student_update_permission_denied(self):
        patch_data = {"text": "Changing comment text."}
        self.do_patch_object_permission_denied_test(self.comment, self.client, self.student,
                                                    self.url, patch_data)

    def test_admin_valid_delete(self):
        self.do_delete_object_test(self.comment, self.client, self.admin, self.url)

    def test_staff_valid_delete(self):
        self.do_delete_object_test(self.comment, self.client, self.staff, self.url)

    def test_handgrader_valid_delete(self):
        self.handgrading_rubric.validate_and_update(handgraders_can_leave_comments=True)
        self.do_delete_object_test(self.comment, self.client, self.handgrader, self.url)

    def test_student_delete_permission_denied(self):
        self.do_delete_object_permission_denied_test(self.comment, self.client, self.student,
                                                     self.url)

    def test_handgrader_update_permission_denied(self):
        patch_data = {"text": "Changing comment text."}
        self.do_patch_object_permission_denied_test(self.comment, self.client, self.handgrader,
                                                    self.url, patch_data)

    def test_handgrader_delete_permission_denied(self):
        self.do_delete_object_permission_denied_test(self.comment, self.client, self.handgrader,
                                                     self.url)
