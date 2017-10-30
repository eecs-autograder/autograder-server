from unittest import mock
from collections import namedtuple

from django.core import exceptions

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase


class RerunSubmissionsTaskTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.project = obj_build.make_project()
        [self.creator] = obj_build.make_admin_users(self.project.course, 1)

        self.ag_test_suite = obj_build.make_ag_test_suite(self.project)
        self.ag_test_case = obj_build.make_ag_test_case(self.ag_test_suite)
        self.student_test_suite = obj_build.make_student_test_suite(self.project)

        self.submission = obj_build.build_submission(
            submission_group=obj_build.make_group(project=self.project))

    def test_default_create(self):
        rerun_task = ag_models.RerunSubmissionsTask.objects.validate_and_create(
            creator=self.creator,
            project=self.project,
            celery_result_id=75
        )  # type: ag_models.RerunSubmissionsTask

        self.assertEqual(self.project, rerun_task.project)
        self.assertEqual(75, rerun_task.celery_result_id)
        self.assertTrue(rerun_task.rerun_all_submissions)
        self.assertEqual([], rerun_task.submission_pks)
        self.assertTrue(rerun_task.rerun_all_ag_test_suites)
        self.assertEqual({}, rerun_task.ag_test_suite_data)
        self.assertTrue(rerun_task.rerun_all_student_test_suites)
        self.assertEqual([], rerun_task.student_suite_pks)

    def test_valid_create(self):
        rerun_task = ag_models.RerunSubmissionsTask.objects.validate_and_create(
            creator=self.creator,
            project=self.project,
            celery_result_id=42,
            rerun_all_submissions=False,
            submission_pks=[self.submission.pk],
            rerun_all_ag_test_suites=False,
            ag_test_suite_data={self.ag_test_suite.pk: [self.ag_test_case.pk]},
            rerun_all_student_test_suites=False,
            student_suite_pks=[self.student_test_suite.pk]
        )  # type: ag_models.RerunSubmissionsTask

        self.assertEqual(self.project, rerun_task.project)
        self.assertEqual(42, rerun_task.celery_result_id)
        self.assertFalse(rerun_task.rerun_all_submissions)
        self.assertEqual([self.submission.pk], rerun_task.submission_pks)
        self.assertFalse(rerun_task.rerun_all_ag_test_suites)
        self.assertEqual({self.ag_test_suite.pk: [self.ag_test_case.pk]},
                         rerun_task.ag_test_suite_data)
        self.assertFalse(rerun_task.rerun_all_student_test_suites)
        self.assertEqual([self.student_test_suite.pk], rerun_task.student_suite_pks)

    def test_progress_computation(self):
        # Replace celery GroupResult with a callable that returns a fake GroupResult
        # instance. The fake instance has a completed_count method that returns
        # the value we want.
        completed_count = 1
        mock_group_result = namedtuple(
            'MockGroupResult', 'completed_count')(lambda: completed_count)
        with mock.patch('autograder.core.models.rerun_submissions_task.GroupResult',
                        new=lambda task_id: mock_group_result):
            rerun_task = ag_models.RerunSubmissionsTask.objects.validate_and_create(
                creator=self.creator,
                project=self.project,
                celery_result_id=42
            )  # type: ag_models.RerunSubmissionsTask

            self.assertAlmostEqual((completed_count / 2) * 100, rerun_task.progress)

    def test_progress_computation_with_specified_pks(self):
        completed_count = 1
        mock_group_result = namedtuple(
            'MockGroupResult', 'completed_count')(lambda: completed_count)
        with mock.patch('autograder.core.models.rerun_submissions_task.GroupResult',
                        new=lambda task_id: mock_group_result):
            rerun_task = ag_models.RerunSubmissionsTask.objects.validate_and_create(
                creator=self.creator,
                project=self.project,
                celery_result_id=42,
                rerun_all_submissions=False,
                submission_pks=[self.submission.pk],
                rerun_all_ag_test_suites=False,
                ag_test_suite_data={self.ag_test_suite.pk: [self.ag_test_case.pk]},
                rerun_all_student_test_suites=False,
                student_suite_pks=[self.student_test_suite.pk]
            )  # type: ag_models.RerunSubmissionsTask

            self.assertAlmostEqual((completed_count / 2) * 100, rerun_task.progress)

    def test_progress_computation_no_subtasks_div_by_zero_avoided(self):
        completed_count = 1
        mock_group_result = namedtuple(
            'MockGroupResult', 'completed_count')(lambda: completed_count)
        with mock.patch('autograder.core.models.rerun_submissions_task.GroupResult',
                        new=lambda task_id: mock_group_result):
            rerun_task = ag_models.RerunSubmissionsTask.objects.validate_and_create(
                creator=self.creator,
                project=self.project,
                celery_result_id=42,
                rerun_all_submissions=False,
                rerun_all_ag_test_suites=False,
                rerun_all_student_test_suites=False,
            )  # type: ag_models.RerunSubmissionsTask

            self.assertEqual(100, rerun_task.progress)

    def test_error_some_submissions_not_in_project(self):
        other_submission = obj_build.build_submission(submission_group=obj_build.make_group())

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.RerunSubmissionsTask.objects.validate_and_create(
                creator=self.creator,
                project=self.project,
                celery_result_id=92,
                rerun_all_submissions=False,
                submission_pks=[other_submission.pk])

        self.assertIn('submission_pks', cm.exception.message_dict)

    def test_error_some_ag_test_suites_not_in_project(self):
        other_ag_test_suite = obj_build.make_ag_test_suite()

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.RerunSubmissionsTask.objects.validate_and_create(
                creator=self.creator,
                project=self.project,
                celery_result_id=92,
                rerun_all_ag_test_suites=False,
                ag_test_suite_data={other_ag_test_suite.pk: []})

        self.assertIn('ag_test_suite_data', cm.exception.message_dict)

    def test_error_some_ag_test_cases_not_in_ag_test_suite(self):
        other_ag_test_case = obj_build.make_ag_test_case()

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.RerunSubmissionsTask.objects.validate_and_create(
                creator=self.creator,
                project=self.project,
                celery_result_id=92,
                rerun_all_ag_test_suites=False,
                ag_test_suite_data={self.ag_test_suite.pk: [other_ag_test_case.pk]})

        self.assertIn('ag_test_suite_data', cm.exception.message_dict)

    def test_error_some_student_suites_not_in_project(self):
        other_student_suite = obj_build.make_student_test_suite()

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.RerunSubmissionsTask.objects.validate_and_create(
                creator=self.creator,
                project=self.project,
                celery_result_id=92,
                rerun_all_student_test_suites=False,
                student_suite_pks=[other_student_suite.pk])

        self.assertIn('student_suite_pks', cm.exception.message_dict)

    def test_serialization(self):
        expected_fields = [
            'progress',
            'error_msg',
            'creator',
            'created_at',
            'has_error',

            'project',
            'celery_result_id',
            'rerun_all_submissions',
            'submission_pks',
            'rerun_all_ag_test_suites',
            'ag_test_suite_data',
            'rerun_all_student_test_suites',
            'student_suite_pks',
        ]

        rerun_task = ag_models.RerunSubmissionsTask.objects.validate_and_create(
            creator=self.creator,
            project=self.project,
            celery_result_id=92)

        self.assertCountEqual(expected_fields, rerun_task.to_dict().keys())
