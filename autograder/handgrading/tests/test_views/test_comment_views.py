from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.handgrading.models as handgrading_models
import autograder.utils.testing.model_obj_builders as obj_build

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class ListCommentsTestCase(UnitTestBase):
    """/api/handgrading_results/<handgrading_result_pk>/comments"""

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

        submission = obj_build.build_submission(submitted_filenames=["test.cpp"])

        self.handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            submission_group=submission.submission_group,
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

    def test_admin_or_staff_or_handgrader_valid_list_cases(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        [staff] = obj_build.make_staff_users(self.course, 1)
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)

        for user in admin, handgrader, staff:
            self.client.force_authenticate(user)

            response = self.client.get(self.url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertSequenceEqual(self.comment.to_dict(), response.data[0])

    def test_student_list_cases_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
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
                handgraders_can_leave_comments=True,
                handgraders_can_adjust_points=True,
                project=obj_build.build_project()
        )

        submission = obj_build.build_submission(submitted_filenames=["test.cpp"])

        self.handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            submission_group=submission.submission_group,
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

    def test_admin_or_handgrader_valid_create_with_location(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)

        for user in admin, handgrader:
            response = self.do_create_object_test(handgrading_models.Comment.objects, self.client,
                                                  user, self.url, self.data, check_data=False)

            loaded = handgrading_models.Comment.objects.get(pk=response.data['pk'])
            self.assertDictContentsEqual(loaded.to_dict(), response.data)

            self.assertEqual(self.data["text"], loaded.text)
            response_location_dict = loaded.location.to_dict()

            for non_modifiable in ["pk", "last_modified"]:
                response_location_dict.pop(non_modifiable)

            self.assertEqual(self.data["location"], response_location_dict)

    def test_admin_or_handgrader_valid_create_without_location(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)
        data = {"text": "Sample comment text."}

        for user in admin, handgrader:
            self.do_create_object_test(handgrading_models.Comment.objects, self.client, user,
                                       self.url, data)

    def test_enrolled_or_staff_create_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        [staff] = obj_build.make_staff_users(self.course, 1)

        for user in enrolled, staff:
            self.do_permission_denied_create_test(handgrading_models.Comment.objects, self.client,
                                                  user, self.url, self.data)

    def test_handgrader_comments_not_allowed_permission_denied(self):
        self.handgrading_rubric.validate_and_update(handgraders_can_leave_comments=False)
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)
        self.do_permission_denied_create_test(handgrading_models.Comment.objects, self.client,
                                              handgrader, self.url, self.data)


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
                handgraders_can_leave_comments=True,
                handgraders_can_adjust_points=True,
                project=obj_build.build_project()
        )

        submission = obj_build.build_submission(submitted_filenames=["test.cpp"])

        self.handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            submission_group=submission.submission_group,
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

    def test_admin_or_staff_or_handgrader_valid_get(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        [staff] = obj_build.make_staff_users(self.course, 1)
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)

        for user in admin, staff, handgrader:
            self.do_get_object_test(self.client, user, self.url, self.comment.to_dict())

    def test_enrolled_get_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.course, 1)
        self.do_permission_denied_get_test(self.client, enrolled, self.url)

    def test_admin_or_handgrader_valid_update(self):
        patch_data = {"text": "Changing comment text."}
        [admin] = obj_build.make_admin_users(self.course, 1)
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)

        for user in admin, handgrader:
            self.do_patch_object_test(self.comment, self.client, user, self.url, patch_data)

    def test_admin_or_handgrader_update_bad_values(self):
        bad_data = {"location": "Location isn't editable!"}
        [admin] = obj_build.make_admin_users(self.course, 1)
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)

        for user in admin, handgrader:
            self.do_patch_object_invalid_args_test(self.comment, self.client, user, self.url,
                                                   bad_data)

    def test_staff_or_student_update_permission_denied(self):
        patch_data = {"text": "Changing comment text."}
        [staff] = obj_build.make_staff_users(self.course, 1)
        [student] = obj_build.make_enrolled_users(self.course, 1)

        for user in staff, student:
            self.do_patch_object_permission_denied_test(self.comment, self.client, user, self.url,
                                                        patch_data)

    def test_admin_valid_delete(self):
        [admin] = obj_build.make_admin_users(self.course, 1)
        self.do_delete_object_test(self.comment, self.client, admin, self.url)

    def test_handgrader_valid_delete(self):
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)
        self.do_delete_object_test(self.comment, self.client, handgrader, self.url)

    def test_student_or_staff_delete_permission_denied(self):
        [staff] = obj_build.make_staff_users(self.course, 1)
        [student] = obj_build.make_enrolled_users(self.course, 1)

        for user in staff, student:
            self.do_delete_object_permission_denied_test(self.comment, self.client, user, self.url)

    def test_handgrader_update_permission_denied(self):
        patch_data = {"text": "Changing comment text."}
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)
        self.handgrading_rubric.validate_and_update(handgraders_can_leave_comments=False)
        self.do_patch_object_permission_denied_test(self.comment, self.client, handgrader,
                                                    self.url, patch_data)

    def test_handgrader_delete_permission_denied(self):
        [handgrader] = obj_build.make_handgrader_users(self.course, 1)
        self.handgrading_rubric.validate_and_update(handgraders_can_leave_comments=False)
        self.do_delete_object_permission_denied_test(self.comment, self.client, handgrader,
                                                     self.url)
