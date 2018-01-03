from django.core import exceptions
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.handgrading.models as handgrading_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.models import Submission
from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class _SetUp(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.group = obj_build.make_group()
        self.student = self.group.members.first()
        self.project = self.group.project
        ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            pattern='*', max_num_matches=10, project=self.project)

        self.submitted_files = [SimpleUploadedFile('file{}'.format(i),
                                                   'waaaluigi{}'.format(i).encode())
                                for i in range(3)]
        self.submission = obj_build.build_submission(
            submission_group=self.group,
            submitted_files=self.submitted_files,
            status=Submission.GradingStatus.finished_grading)

        self.handgrading_rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
            project=self.project
        )  # type: handgrading_models.HandgradingRubric

        [self.admin] = obj_build.make_admin_users(self.project.course, 1)
        [self.staff] = obj_build.make_staff_users(self.project.course, 1)
        [self.handgrader] = obj_build.make_users(1)
        self.project.course.handgraders.add(self.handgrader)

        self.client = APIClient()
        self.course = self.handgrading_rubric.project.course
        self.url = reverse('handgrading_result',
                           kwargs={'group_pk': self.submission.submission_group.pk})


class RetrieveHandgradingResultTestCase(_SetUp):
    """/api/submission_groups/<group_pk>/handgrading_result/"""

    def setUp(self):
        super().setUp()

        self.handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.handgrading_rubric
        )  # type: handgrading_models.HandgradingResult

    def test_staff_or_handgrader_can_always_retrieve(self):
        self.project.validate_and_update(visible_to_students=False)
        self.assertFalse(self.handgrading_rubric.show_grades_and_rubric_to_students)

        for user in self.handgrader, self.staff:
            self.client.force_authenticate(user)

            response = self.client.get(self.url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertEqual(self.handgrading_result.to_dict(), response.data)

    def test_staff_or_handgrader_get_files(self):
        for user in self.handgrader, self.staff:
            self.client.force_authenticate(user)

            for file_ in self.submitted_files:
                response = self.client.get(self.get_file_url(file_.name))
                self.assertEqual(status.HTTP_200_OK, response.status_code)
                file_.seek(0)
                self.assertEqual(file_.read(),
                                 b''.join((chunk for chunk in response.streaming_content)))

    def test_get_file_not_found(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get(self.get_file_url('not_a_file'))
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_handgrading_result_does_not_exist(self):
        self.handgrading_result.delete()

        self.client.force_authenticate(self.admin)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_handgrading_rubric_does_not_exist(self):
        self.handgrading_rubric.delete()

        self.client.force_authenticate(self.admin)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_student_get_handgrading_result_scores_released(self):
        self.project.validate_and_update(visible_to_students=True)
        self.handgrading_rubric.validate_and_update(show_grades_and_rubric_to_students=True)
        self.client.force_authenticate(self.student)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self.handgrading_result.to_dict(), response.data)

    def test_student_get_handgrading_result_scores_not_released_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True)
        self.handgrading_rubric.validate_and_update(show_grades_and_rubric_to_students=False)
        self.client.force_authenticate(self.student)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_student_get_handgrading_result_project_hidden_permission_denied(self):
        self.handgrading_rubric.validate_and_update(show_grades_and_rubric_to_students=True)
        self.project.validate_and_update(visible_to_students=False)
        self.client.force_authenticate(self.student)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_student_not_in_group_get_handgrading_result_permission_denied(self):
        self.handgrading_rubric.validate_and_update(show_grades_and_rubric_to_students=True)
        self.project.validate_and_update(visible_to_students=True)

        [other_student] = obj_build.make_enrolled_users(self.course, 1)
        self.client.force_authenticate(other_student)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def get_file_url(self, filename):
        return self.url + '?filename={}'.format(filename)


class CreateHandgradingResultTestCase(test_impls.CreateObjectTest, _SetUp):
    """/api/submission_groups/<group_pk>/handgrading_result/"""

    def setUp(self):
        super().setUp()

        self.criteria = [
            handgrading_models.Criterion.objects.validate_and_create(
                handgrading_rubric=self.handgrading_rubric)
            for i in range(3)
        ]

    def test_admin_or_grader_post_creates_if_does_not_exist_and_gets_if_does_exist(self):
        for user in self.admin, self.handgrader:
            with self.assertRaises(exceptions.ObjectDoesNotExist):
                print(self.group.handgrading_result)

            self.client.force_authenticate(user)
            response = self.client.post(self.url, {})

            self.assertEqual(status.HTTP_201_CREATED, response.status_code)

            self.group = ag_models.SubmissionGroup.objects.get(pk=self.group.pk)
            handgrading_result = self.group.handgrading_result
            self.assertEqual(handgrading_result.to_dict(), response.data)

            response = self.client.post(self.url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertEqual(handgrading_result.to_dict(), response.data)

            handgrading_result.refresh_from_db()
            self.assertEqual(len(self.criteria), handgrading_result.criterion_results.count())
            for criterion_result in handgrading_result.criterion_results.all():
                self.assertIn(criterion_result.criterion, self.criteria)

            handgrading_result.delete()
            self.group = ag_models.SubmissionGroup.objects.get(pk=self.group.pk)

    def test_no_handgrading_rubric(self):
        self.handgrading_rubric.delete()

        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('handgrading_rubric', response.data)
        self.assertEqual(0, handgrading_models.HandgradingResult.objects.count())

    def test_group_has_no_submissions(self):
        self.submission.delete()

        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('num_submissions', response.data)
        self.assertEqual(0, handgrading_models.HandgradingResult.objects.count())

    def test_non_admin_create_permission_denied(self):
        self.do_permission_denied_create_test(
            handgrading_models.HandgradingResult.objects,
            self.client, self.student, self.url, {})


class UpdateHandgradingResultPointsAdjustmentTestCase(test_impls.UpdateObjectTest, _SetUp):
    def setUp(self):
        super().setUp()

        self.handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.handgrading_rubric
        )  # type: handgrading_models.HandgradingResult

        self.assertFalse(self.handgrading_result.finished_grading)
        self.assertEqual(0, self.handgrading_result.points_adjustment)

    def test_admin_always_can_update(self):
        request_data = {'finished_grading': True, 'points_adjustment': -3}
        self.do_patch_object_test(
            self.handgrading_result, self.client, self.admin, self.url, request_data)

    def test_handgrader_always_update_finished_grading(self):
        request_data = {'finished_grading': True}
        self.do_patch_object_test(
            self.handgrading_result, self.client, self.handgrader, self.url, request_data)

    def test_handgrader_update_points_adjustment_allowed(self):
        self.handgrading_rubric.validate_and_update(handgraders_can_adjust_points=True)
        request_data = {'points_adjustment': -3}
        self.do_patch_object_test(
            self.handgrading_result, self.client, self.handgrader, self.url, request_data)

    def test_handgrader_update_points_adjustment_not_allowed_permission_denied(self):
        self.handgrading_rubric.validate_and_update(handgraders_can_adjust_points=False)
        request_data = {'points_adjustment': -3}
        self.do_patch_object_permission_denied_test(
            self.handgrading_result, self.client, self.handgrader, self.url, request_data)

    def test_other_update_points_adjustment_permission_denied(self):
        self.handgrading_rubric.validate_and_update(handgraders_can_adjust_points=True)
        request_data = {'points_adjustment': -3}
        self.do_patch_object_permission_denied_test(
            self.handgrading_result, self.client, self.student, self.url, request_data)
