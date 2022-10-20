import random
from unittest import mock
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.core import exceptions
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
import autograder.handgrading.models as hg_models
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core.models import Submission
from autograder.handgrading.views.handgrading_result_views import HandgradingResultPaginator
from autograder.rest_api.tests.test_views.ag_view_test_base import AGViewTestBase
from autograder.utils.testing import UnitTestBase


class _SetUp(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.group = obj_build.make_group()
        self.student = self.group.members.first()
        self.project = self.group.project
        ag_models.ExpectedStudentFile.objects.validate_and_create(
            pattern='*', max_num_matches=10, project=self.project)

        self.submitted_files = [SimpleUploadedFile('file{}'.format(i),
                                                   'waaaluigi{}'.format(i).encode())
                                for i in range(3)]
        self.submission = obj_build.make_submission(
            group=self.group,
            submitted_files=self.submitted_files,
            status=Submission.GradingStatus.finished_grading)

        self.handgrading_rubric = hg_models.HandgradingRubric.objects.validate_and_create(
            project=self.project
        )  # type: hg_models.HandgradingRubric

        [self.admin] = obj_build.make_admin_users(self.project.course, 1)
        [self.staff] = obj_build.make_staff_users(self.project.course, 1)
        [self.handgrader] = obj_build.make_users(1)
        self.project.course.handgraders.add(self.handgrader)

        self.client = APIClient()
        self.course = self.handgrading_rubric.project.course
        self.url = reverse('handgrading_result', kwargs={'group_pk': self.submission.group.pk})


class RetrieveHandgradingResultTestCase(_SetUp):
    def setUp(self):
        super().setUp()

        self.handgrading_result = hg_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            group=self.submission.group,
            handgrading_rubric=self.handgrading_rubric
        )  # type: hg_models.HandgradingResult

        for _ in range(3):
            hg_models.Comment.objects.validate_and_create(
                text="HI",
                handgrading_result=self.handgrading_result)

        for _ in range(3):
            hg_models.CriterionResult.objects.validate_and_create(
                selected=True,
                criterion=hg_models.Criterion.objects.validate_and_create(
                    points=0,
                    handgrading_rubric=self.handgrading_rubric),
                handgrading_result=self.handgrading_result)

        criterion_order = self.handgrading_rubric.get_criterion_order()[::-1]
        self.handgrading_rubric.set_criterion_order(criterion_order)

    def test_staff_or_handgrader_can_always_retrieve(self):
        self.project.validate_and_update(visible_to_students=False)
        self.assertFalse(self.handgrading_rubric.show_grades_and_rubric_to_students)

        for user in self.handgrader, self.staff:
            self.client.force_authenticate(user)

            response = self.client.get(self.url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertEqual(self.handgrading_result.to_dict(), response.data)

    def test_ordering(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.url)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self.handgrading_result.to_dict(), response.data)

        result_criterion_order = [criterion_result["criterion"]["pk"]
                                  for criterion_result in response.data["criterion_results"]]
        result_comment_order = [comment["pk"] for comment in response.data["comments"]]
        correct_comment_order = sorted(result_comment_order)

        self.assertSequenceEqual(result_criterion_order,
                                 self.handgrading_result.handgrading_rubric.get_criterion_order())
        self.assertSequenceEqual(result_comment_order, correct_comment_order)

    def test_staff_or_handgrader_get_files(self):
        for user in self.handgrader, self.staff:
            self.client.force_authenticate(user)

            for file_ in self.submitted_files:
                response = self.client.get(self.get_file_url(file_.name))
                self.assertEqual(status.HTTP_200_OK, response.status_code)
                self.assertIn('Content-Length', response)
                file_.seek(0)
                self.assertEqual(file_.read(), b''.join(response.streaming_content))

    def test_get_file_x_accel_headers(self) -> None:
        with override_settings(USE_NGINX_X_ACCEL=True):
            self.client.force_authenticate(self.staff)

            file_ = self.submitted_files[0]
            response = self.client.get(self.get_file_url(file_.name))
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertEqual(b'', response.content)
            self.assertEqual('application/octet-stream', response['Content-Type'])
            self.assertEqual('attachment; filename=' + file_.name, response['Content-Disposition'])
            self.assertEqual(
                f'/protected/{core_ut.get_submission_relative_dir(self.submission)}/{file_.name}',
                response['X-Accel-Redirect']
            )

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

        [other_student] = obj_build.make_student_users(self.course, 1)
        self.client.force_authenticate(other_student)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def get_file_url(self, filename):
        return reverse(
            'handgrading-result-file',
            kwargs={'group_pk': self.submission.group.pk}
        ) + '?filename={}'.format(filename)

class HideUnappliedHandgradingTestCase(_SetUp):
    def setUp(self):
        super().setUp()

        self.project.validate_and_update(visible_to_students=True)
        self.handgrading_rubric.validate_and_update(
            show_grades_and_rubric_to_students=True
        )
        self.handgrading_rubric.validate_and_update(
            show_only_applied_rubric_to_students=True
        )

        self.handgrading_result = (
            hg_models.HandgradingResult.objects.validate_and_create(
                submission=self.submission,
                group=self.submission.group,
                handgrading_rubric=self.handgrading_rubric,
            )
        )  # type: hg_models.HandgradingResult

        for pt in range(3):
            applied = pt % 2 == 0  # So, 0, 2 are applied, 1 is not

            hg_models.CriterionResult.objects.validate_and_create(
                selected=applied,
                criterion=hg_models.Criterion.objects.validate_and_create(
                    short_description=f"C-POSITIVE-{pt}",
                    points=pt,
                    handgrading_rubric=self.handgrading_rubric,
                ),
                handgrading_result=self.handgrading_result,
            )

            hg_models.CriterionResult.objects.validate_and_create(
                selected=applied,
                criterion=hg_models.Criterion.objects.validate_and_create(
                    short_description=f"C-NEGATIVE-{pt}",
                    points=-pt,
                    handgrading_rubric=self.handgrading_rubric,
                ),
                handgrading_result=self.handgrading_result,
            )

            anno = hg_models.Annotation.objects.validate_and_create(
                deduction=-pt,
                short_description=f"A-NEGATIVE-{pt}",
                handgrading_rubric=self.handgrading_rubric,
            )

            if applied:
                hg_models.AppliedAnnotation.objects.validate_and_create(
                    annotation=anno,
                    handgrading_result=self.handgrading_result,
                    location={
                        "first_line": 0,
                        "last_line": 1,
                        "filename": self.submitted_files[pt].name,
                    },
                )

        criterion_order = self.handgrading_rubric.get_criterion_order()[::-1]
        self.handgrading_rubric.set_criterion_order(criterion_order)

    def test_staff_or_handgrader_can_always_retrieve_all(self):
        self.assertTrue(self.handgrading_rubric.show_grades_and_rubric_to_students)
        self.assertTrue(self.handgrading_rubric.show_only_applied_rubric_to_students)

        for user in self.handgrader, self.staff, self.admin:
            self.client.force_authenticate(user)

            response = self.client.get(self.url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertEqual(self.handgrading_result.to_dict(), response.data)

    def test_student_can_only_retrieve_applied(self):
        self.assertTrue(self.handgrading_rubric.show_grades_and_rubric_to_students)
        self.assertTrue(self.handgrading_rubric.show_only_applied_rubric_to_students)

        self.client.force_authenticate(self.student)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertNotEqual(self.handgrading_result.to_dict(), response.data)

        EXPECTED_CRITERIA = {
            "C-POSITIVE-0",
            "C-POSITIVE-2",
            "C-NEGATIVE-0",
            "C-NEGATIVE-2",
        }
        EXPECTED_ANNOTATIONS = {"A-NEGATIVE-0", "A-NEGATIVE-2"}

        # Check all rubrics in the response
        self.assertEqual(
            EXPECTED_ANNOTATIONS,
            {
                a["short_description"]
                for a in response.data["handgrading_rubric"]["annotations"]
            },
        )
        self.assertEqual(
            EXPECTED_ANNOTATIONS,
            {
                a["annotation"]["short_description"]
                for a in response.data["applied_annotations"]
            },
        )
        self.assertEqual(
            EXPECTED_CRITERIA,
            {
                c["short_description"]
                for c in response.data["handgrading_rubric"]["criteria"]
            },
        )
        self.assertEqual(
            EXPECTED_CRITERIA,
            {
                c["criterion"]["short_description"]
                for c in response.data["criterion_results"]
            },
        )

class HasCorrectSubmissionTestCase(_SetUp):
    def setUp(self):
        super().setUp()

        self.handgrading_result = hg_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            group=self.submission.group,
            handgrading_rubric=self.handgrading_rubric
        )  # type: hg_models.HandgradingResult

        self.url = reverse('handgrading-result-has-correct-submission',
                           kwargs={'group_pk': self.submission.group.pk})

    def test_has_correct_ultimate_submission(self) -> None:
        for user in self.admin, self.staff, self.handgrader:
            self.client.force_authenticate(user)
            response = self.client.get(self.url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertIs(response.data, True)

        self.project.validate_and_update(visible_to_students=True)
        self.handgrading_rubric.validate_and_update(show_grades_and_rubric_to_students=True)
        self.client.force_authenticate(self.student)
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertIs(response.data, True)

    def test_has_incorrect_ultimate_submission(self) -> None:
        other_submission = obj_build.make_submission(self.group)
        self.handgrading_result.submission = other_submission
        self.handgrading_result.save()

        for user in self.admin, self.staff, self.handgrader:
            self.client.force_authenticate(user)
            response = self.client.get(self.url)
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            self.assertIs(response.data, False)

        self.project.validate_and_update(visible_to_students=True)
        self.handgrading_rubric.validate_and_update(show_grades_and_rubric_to_students=True)
        self.client.force_authenticate(self.student)
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertIs(response.data, False)

    def test_handgrading_rubric_does_not_exist(self):
        self.handgrading_rubric.delete()

        self.client.force_authenticate(self.admin)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)


class CreateHandgradingResultTestCase(_SetUp):
    def setUp(self):
        super().setUp()

        self.criteria = [
            hg_models.Criterion.objects.validate_and_create(
                handgrading_rubric=self.handgrading_rubric)
            for i in range(3)
        ]

    def test_admin_or_staff_or_grader_post_creates_if_does_not_exist_and_gets_if_does_exist(self):
        for user in self.admin, self.staff, self.handgrader:
            with self.assertRaises(exceptions.ObjectDoesNotExist):
                print(self.group.handgrading_result)

            self.client.force_authenticate(user)
            response = self.client.post(self.url, {})

            self.assertEqual(status.HTTP_201_CREATED, response.status_code)

            self.group = ag_models.Group.objects.get(pk=self.group.pk)
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
            self.group = ag_models.Group.objects.get(pk=self.group.pk)

    def test_ultimate_submission_to_grade_does_not_consider_submission_not_counting_for_user(self):
        """
        The field Submission.does_not_count_for is not considered when
        determining which submission to handgrade.
        """
        with self.assertRaises(exceptions.ObjectDoesNotExist):
            print(self.group.handgrading_result)

        mock_get_ultimate_submission = mock.Mock(return_value=self.submission)

        with mock.patch(
                'autograder.handgrading.views.handgrading_result_views.get_ultimate_submission',
                new=mock_get_ultimate_submission):
            self.client.force_authenticate(self.admin)
            response = self.client.post(self.url, {})

            mock_get_ultimate_submission.assert_called_once_with(self.group)

    def test_no_handgrading_rubric(self):
        self.handgrading_rubric.delete()

        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('handgrading_rubric', response.data)
        self.assertEqual(0, hg_models.HandgradingResult.objects.count())

    def test_group_has_no_submissions(self):
        self.submission.delete()

        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, {})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('num_submissions', response.data)
        self.assertEqual(0, hg_models.HandgradingResult.objects.count())

    def test_non_admin_create_permission_denied(self):
        self.do_permission_denied_create_test(
            hg_models.HandgradingResult.objects,
            self.client, self.student, self.url, {})


class UpdateHandgradingResultPointsAdjustmentTestCase(test_impls.UpdateObjectTest, _SetUp):
    def setUp(self):
        super().setUp()

        self.handgrading_result = hg_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            group=self.submission.group,
            handgrading_rubric=self.handgrading_rubric
        )  # type: hg_models.HandgradingResult

        self.assertFalse(self.handgrading_result.finished_grading)
        self.assertEqual(0, self.handgrading_result.points_adjustment)

    def test_admin_and_staff_always_can_update(self):
        request_data = {'finished_grading': True, 'points_adjustment': -3}
        for user in self.admin, self.staff:
            self.do_patch_object_test(
                self.handgrading_result, self.client, user, self.url, request_data)

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
        self.do_patch_object_permission_denied_test(self.handgrading_result, self.client,
                                                    self.handgrader, self.url, request_data)

    def test_other_update_points_adjustment_permission_denied(self):
        self.handgrading_rubric.validate_and_update(handgraders_can_adjust_points=True)
        request_data = {'points_adjustment': -3}
        self.do_patch_object_permission_denied_test(
            self.handgrading_result, self.client, self.student, self.url, request_data)


class DeleteHandgradingResultTestCase(_SetUp):
    def setUp(self):
        super().setUp()

        self.handgrading_result = hg_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            group=self.submission.group,
            handgrading_rubric=self.handgrading_rubric
        )  # type: hg_models.HandgradingResult

    def test_admin_delete_result(self) -> None:
        self.do_delete_object_test(self.handgrading_result, self.client, self.admin, self.url)

    def test_staff_delete_result(self) -> None:
        self.do_delete_object_test(self.handgrading_result, self.client, self.staff, self.url)

    def test_handgrader_delete_result(self) -> None:
        self.do_delete_object_test(self.handgrading_result, self.client, self.handgrader, self.url)

    def test_student_delete_result_permission_denied(self) -> None:
        self.project.validate_and_update(visible_to_students=True)
        self.handgrading_rubric.validate_and_update(show_grades_and_rubric_to_students=True)

        self.do_delete_object_permission_denied_test(
            self.handgrading_result, self.client, self.student, self.url)


class ListHandgradingResultsViewTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.maxDiff = None

        self.client = APIClient()
        self.course = obj_build.make_course()
        self.project = obj_build.make_project(course=self.course)
        self.assertEqual(ag_models.UltimateSubmissionPolicy.most_recent,
                         self.project.ultimate_submission_policy)

        self.rubric = hg_models.HandgradingRubric.objects.validate_and_create(
            project=self.project,
            points_style=hg_models.PointsStyle.start_at_max_and_subtract,
            max_points=43)

        [self.staff] = obj_build.make_staff_users(self.course, 1)
        [self.handgrader] = obj_build.make_handgrader_users(self.course, 1)

    def test_staff_get_handgrading_results_no_results(self):
        self.do_handgrading_results_test(self.staff, num_results=0)

    def test_get_handgrading_results_exclude_staff(self):
        staff_group = obj_build.make_group(members_role=obj_build.UserRole.staff,
                                           project=self.project)
        admin_group = obj_build.make_group(members_role=obj_build.UserRole.admin,
                                           project=self.project)

        staff_submission = obj_build.make_finished_submission(group=staff_group)
        admin_submission = obj_build.make_finished_submission(group=admin_group)

        staff_hg_result = hg_models.HandgradingResult.objects.validate_and_create(
            submission=staff_submission, group=staff_group, handgrading_rubric=self.rubric)
        admin_hg_result = hg_models.HandgradingResult.objects.validate_and_create(
            submission=admin_submission, group=admin_group, handgrading_rubric=self.rubric)

        self.client.force_authenticate(self.staff)
        url = reverse('handgrading_results', kwargs={'pk': self.project.pk})
        url += '?' + urlencode({'include_staff': 'false'})
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual([], response.data['results'])

        student_group = obj_build.make_group(members_role=obj_build.UserRole.student,
                                             project=self.project)
        student_submission = obj_build.make_finished_submission(group=student_group)
        student_hg_result = hg_models.HandgradingResult.objects.validate_and_create(
            submission=student_submission, group=student_group, handgrading_rubric=self.rubric)

        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(1, len(response.data['results']))
        self.assertEqual(student_group.member_names, response.data['results'][0]['member_names'])

    def test_handgrader_get_handgrading_results_no_results(self):
        self.do_handgrading_results_test(self.handgrader, num_results=0)

    def test_staff_get_handgrading_results_default_page_size(self):
        self.do_handgrading_results_test(self.staff, num_results=2)

    def test_handgrader_get_handgrading_results_default_page_size(self):
        self.do_handgrading_results_test(self.handgrader, num_results=2)

    def test_staff_get_paginated_handgrading_results_custom_page_size(self):
        self.do_handgrading_results_test(self.staff, num_results=3, page_size=1)

    def test_handgrader_get_paginated_handgrading_results_custom_page_size(self):
        self.do_handgrading_results_test(self.handgrader, num_results=3, page_size=1)

    def test_staff_get_paginated_handgrading_results_specific_page(self):
        self.do_handgrading_results_test(self.staff, num_results=4, page_size=3, page_num=2)

    def test_handgrader_get_paginated_handgrading_results_specific_page(self):
        self.do_handgrading_results_test(self.handgrader, num_results=4, page_size=3, page_num=2)

    def test_get_paginated_results_some_groups_have_no_result(self):
        self.do_handgrading_results_test(self.handgrader, num_results=2, num_groups=4)

    def test_non_staff_non_handgrader_get_handgrading_results_permission_denied(self):
        [student] = obj_build.make_student_users(self.course, 1)
        self.client.force_authenticate(student)
        response = self.client.get(reverse('handgrading_results', kwargs={'pk': self.project.pk}))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def do_handgrading_results_test(self, user: User, *,
                                    num_results: int, num_groups: int = None,
                                    page_size: int = None, page_num: int = None):
        if num_groups is None:
            num_groups = num_results
        else:
            assert num_groups >= num_results

        groups = [obj_build.make_group(3, project=self.project) for _ in range(num_groups)]
        expected_data = []
        for i in range(num_results):
            group = groups[i]
            s = obj_build.make_finished_submission(group=group)
            score = random.randint(0, self.rubric.max_points + 3)
            hg_result = hg_models.HandgradingResult.objects.validate_and_create(
                submission=s, group=group, handgrading_rubric=self.rubric,
                points_adjustment=score,
                finished_grading=bool(random.getrandbits(1)))

            # Groups that have a handgrading result
            data = hg_result.group.to_dict()
            data['handgrading_result'] = {
                'total_points': hg_result.total_points,
                'total_points_possible': hg_result.total_points_possible,
                'finished_grading': hg_result.finished_grading
            }
            data['member_names'].sort()
            expected_data.append(data)

        # Groups that don't have a handgrading result
        for i in range(num_results, num_groups):
            data = groups[i].to_dict()
            data['member_names'].sort()
            data['handgrading_result'] = None
            expected_data.append(data)

        expected_data.sort(key=lambda group: group['member_names'][0])

        self.client.force_authenticate(user)
        url = reverse('handgrading_results', kwargs={'pk': self.project.pk})
        query_params = {}
        if page_num is not None:
            query_params['page'] = page_num
        else:
            page_num = 1

        if page_size is not None:
            query_params['page_size'] = page_size
        else:
            page_size = HandgradingResultPaginator.page_size

        expected_data = expected_data[page_num - 1 * page_size:page_num * page_size]

        if query_params:
            url += '?' + urlencode(query_params)
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual(expected_data, response.data['results'])
