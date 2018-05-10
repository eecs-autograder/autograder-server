import json
import os
from collections import namedtuple

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
import autograder.utils.testing.model_obj_builders as obj_build
from autograder import utils
from autograder.core import constants
from autograder.core.models.submission import get_submissions_with_results_queryset
from autograder.utils.testing import UnitTestBase


class SubmissionTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.group = obj_build.build_group(num_members=2)
        self.project = self.group.project

        expected_files = [
            {
                'project': self.project,
                'pattern': 'spam.cpp'
            },
            {
                'project': self.project,
                'pattern': 'eggs.cpp'
            },
            {
                'project': self.project,
                'pattern': 'test_*.cpp',
                'min_num_matches': 1,
                'max_num_matches': 2
            }
        ]

        for expected_file_dict in expected_files:
            ag_models.ExpectedStudentFile.objects.validate_and_create(
                **expected_file_dict)

    def test_valid_init(self):
        SimpleFileTuple = namedtuple('SimpleFileTuple', ['name', 'content'])

        files_to_submit = sorted([
            SimpleFileTuple('spam.cpp', b'blah'),
            SimpleFileTuple('eggs.cpp', b'merp'),
            SimpleFileTuple('test_spam.cpp', b'cheeese')
        ])

        now = timezone.now()

        submitter = 'steve'
        submission = ag_models.Submission.objects.validate_and_create(
            group=self.group,
            submitted_files=[
                SimpleUploadedFile(name, content) for
                name, content in files_to_submit],
            submitter=submitter)

        submission.refresh_from_db()

        self.assertEqual(submitter, submission.submitter)
        self.assertEqual(
            submission.status,
            ag_models.Submission.GradingStatus.received)
        self.assertEqual(submission.error_msg, '')
        self.assertCountEqual(submission.missing_files, [])
        self.assertCountEqual(
            (file_.name for file_ in files_to_submit),
            submission.submitted_filenames)

        self.assertTrue(submission.count_towards_daily_limit)
        self.assertFalse(submission.is_past_daily_limit)

        self.assertLess(submission.timestamp - now,
                        timezone.timedelta(seconds=2))

        # Check file contents in the filesystem
        self.assertTrue(os.path.isdir(core_ut.get_submission_dir(submission)))
        with utils.ChangeDirectory(core_ut.get_submission_dir(submission)):
            self.assertTrue(os.path.isdir(constants.FILESYSTEM_RESULT_OUTPUT_DIRNAME))
            for name, content in files_to_submit:
                self.assertEqual(name, submission.get_file(name).name)
                self.assertEqual(content, submission.get_file(name).read())

                self.assertTrue(
                    os.path.isfile(os.path.basename(name)))
                with open(name, 'rb') as f:
                    self.assertEqual(content, f.read())

        # Check submitted files using member accessors
        expected = sorted(files_to_submit)
        actual = sorted(submission.submitted_files,
                        key=lambda file_: file_.name)
        for expected_file, loaded_file in zip(expected, actual):
            self.assertEqual(expected_file.name,
                             os.path.basename(loaded_file.name))
            self.assertEqual(expected_file.content,
                             loaded_file.read())

    def test_init_custom_values(self):
        timestamp = timezone.now() + timezone.timedelta(hours=1)

        sub = ag_models.Submission.objects.validate_and_create(
            [], group=self.group, timestamp=timestamp)

        sub.refresh_from_db()

        self.assertEqual(timestamp, sub.timestamp)

    def test_submission_missing_required_file(self):
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('test_spam.cpp', b'cheeese')
        ]

        submission = ag_models.Submission.objects.validate_and_create(
            group=self.group,
            submitted_files=files)

        submission.refresh_from_db()

        self.assertEqual(
            submission.status, ag_models.Submission.GradingStatus.received)
        self.assertEqual({'eggs.cpp': 1}, submission.missing_files)

    def test_submission_not_enough_files_matching_pattern(self):
        self.project.expected_student_files.get(
            max_num_matches=2
        ).validate_and_update(min_num_matches=2, max_num_matches=3)
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
            SimpleUploadedFile('test_spam.cpp', b'yarp')
        ]

        submission = ag_models.Submission.objects.validate_and_create(
            group=self.group,
            submitted_files=files)

        submission.refresh_from_db()

        self.assertEqual(submission.status,
                         ag_models.Submission.GradingStatus.received)
        self.assertEqual({'test_*.cpp': 1}, submission.missing_files)

    def test_extra_files_matching_pattern_discarded(self):
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
            SimpleUploadedFile('test_spam.cpp', b'cheeese'),
            SimpleUploadedFile('test_egg.cpp', b'cheeese'),
        ]
        extra_files = [
            SimpleUploadedFile('test_sausage.cpp', b'cheeese')
        ]

        self._do_files_discarded_test(files, extra_files)

    def test_extra_files_discarded(self):
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
            SimpleUploadedFile('test_spam.cpp', b'cheeese'),
        ]
        extra_files = [
            SimpleUploadedFile('extra.cpp', b'merp'),
            SimpleUploadedFile('extra_extra.cpp', b'spam')]

        submission = self._do_files_discarded_test(files, extra_files)

        with utils.ChangeDirectory(core_ut.get_submission_dir(submission)):
            for file_ in extra_files:
                self.assertFalse(os.path.exists(file_.name))

    def test_duplicate_files_discarded(self):
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
            SimpleUploadedFile('test_spam.cpp', b'cheeese')
        ]
        duplicate_files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
            SimpleUploadedFile('eggs.cpp', b'merp')
        ]

        self._do_files_discarded_test(files, duplicate_files)

    def test_invalid_filenames(self):
        bad_files = [
            SimpleUploadedFile('..', b'blah'),
            SimpleUploadedFile('.', b'merp'),
            SimpleUploadedFile('', b'cheeese')
        ]
        ag_models.ExpectedStudentFile.objects.validate_and_create(
            project=self.project, pattern='*', max_num_matches=10)

        self._do_files_discarded_test([SimpleUploadedFile('test_spam.cpp', b'cheeese')], bad_files)

    def _do_files_discarded_test(self, files, files_to_discard):
        submission = ag_models.Submission.objects.validate_and_create(
            group=self.group,
            submitted_files=files + files_to_discard)

        submission.refresh_from_db()

        self.assertEqual(ag_models.Submission.GradingStatus.received,
                         submission.status)
        self.assertCountEqual(submission.get_submitted_file_basenames(),
                              (file_.name for file_ in files))

        self.assertCountEqual(submission.discarded_files,
                              (file_.name for file_ in files_to_discard))
        return submission

    def test_active_statuses(self):
        statuses = [
            ag_models.Submission.GradingStatus.received,
            ag_models.Submission.GradingStatus.queued,
            ag_models.Submission.GradingStatus.being_graded]
        self.assertCountEqual(
            statuses,
            ag_models.Submission.GradingStatus.active_statuses)

    def test_serializable_fields(self):
        # Note: Do NOT add basic_score to this list, as that will leak
        # information in certain scenarios (such as when a student
        # requests feedback on a submission that is past the daily
        # limit).
        expected = [
            'pk',
            'group',
            'timestamp',
            'submitter',
            'submitted_filenames',
            'discarded_files',
            'missing_files',
            'status',

            'count_towards_daily_limit',
            'is_past_daily_limit',

            'position_in_queue',
        ]
        self.assertCountEqual(
            expected,
            ag_models.Submission.get_serializable_fields())
        group = obj_build.build_group()
        submission = ag_models.Submission(group=group)
        self.assertTrue(submission.to_dict())

    def test_editable_fields(self):
        self.assertCountEqual(['count_towards_daily_limit'],
                              ag_models.Submission.get_editable_fields())


class PositionInQueueTestCase(UnitTestBase):
    def test_position_in_queue_multiple_projects(self):
        """
        Makes sure that position in queue is calculated per-project
        """
        project1 = obj_build.build_project()
        group1_proj1 = obj_build.build_group(
            group_kwargs={'project': project1})
        group2_proj1 = obj_build.build_group(
            group_kwargs={'project': project1})

        project2 = obj_build.build_project()
        group1_proj2 = obj_build.build_group(
            group_kwargs={'project': project2})
        group2_proj2 = obj_build.build_group(
            group_kwargs={'project': project2})

        group1_p1 = obj_build.build_submission(
            group=group1_proj1)
        group1_p1.status = (
            ag_models.Submission.GradingStatus.queued)
        group1_p1.save()
        group1_p1_queue_pos = 1

        group2_p1 = obj_build.build_submission(
            group=group2_proj1)
        group2_p1.status = (
            ag_models.Submission.GradingStatus.queued)
        group2_p1.save()
        group2_p1_queue_pos = 2

        group1_p2 = obj_build.build_submission(
            group=group1_proj2)
        group1_p2.status = (
            ag_models.Submission.GradingStatus.queued)
        group1_p2.save()
        group1_p2_queue_pos = 1

        group2_p2 = obj_build.build_submission(
            group=group2_proj2)
        group2_p2.status = (
            ag_models.Submission.GradingStatus.queued)
        group2_p2.save()
        group2_p2_queue_pos = 2

        self.assertEqual(group1_p1_queue_pos,
                         group1_p1.position_in_queue)
        self.assertEqual(group2_p1_queue_pos,
                         group2_p1.position_in_queue)
        self.assertEqual(group1_p2_queue_pos,
                         group1_p2.position_in_queue)
        self.assertEqual(group2_p2_queue_pos,
                         group2_p2.position_in_queue)

    def test_position_in_queue_for_non_queued_submission(self):
        submission = obj_build.build_submission()

        non_queued_statuses = list(ag_models.Submission.GradingStatus.values)
        non_queued_statuses.remove(ag_models.Submission.GradingStatus.queued)

        for status in non_queued_statuses:
            submission.status = status
            submission.save()
            self.assertEqual(0, submission.position_in_queue)


class SubmissionFeedbackTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None

        self.project = obj_build.make_project()
        self.course = self.project.course

        self.ag_test_suite1 = obj_build.make_ag_test_suite(self.project)
        self.ag_test_case1 = obj_build.make_ag_test_case(self.ag_test_suite1)
        self.ag_test_cmd1 = obj_build.make_full_ag_test_command(
            self.ag_test_case1, set_arbitrary_points=True)

        self.ag_test_suite2 = obj_build.make_ag_test_suite(self.project)
        self.ag_test_case2 = obj_build.make_ag_test_case(self.ag_test_suite2)
        self.ag_test_cmd2 = obj_build.make_full_ag_test_command(
            self.ag_test_case2, set_arbitrary_points=True)

        self.points_per_bug_exposed = 3
        self.num_buggy_impls = 4
        self.student_suite1 = ag_models.StudentTestSuite.objects.validate_and_create(
            name='suite1', project=self.project,
            buggy_impl_names=['bug{}'.format(i) for i in range(self.num_buggy_impls)],
            points_per_exposed_bug=self.points_per_bug_exposed
        )  # type: ag_models.StudentTestSuite
        self.student_suite2 = ag_models.StudentTestSuite.objects.validate_and_create(
            name='suite2', project=self.project,
            buggy_impl_names=['bug{}'.format(i) for i in range(self.num_buggy_impls)],
            points_per_exposed_bug=self.points_per_bug_exposed
        )  # type: ag_models.StudentTestSuite

        self.group = obj_build.make_group(1, project=self.project)
        self.submission = obj_build.build_submission(group=self.group)

        self.ag_suite_result1 = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=self.ag_test_suite1, submission=self.submission
        )  # type: ag_models.AGTestSuiteResult
        self.ag_case_result1 = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_suite_result=self.ag_suite_result1, ag_test_case=self.ag_test_case1
        )  # type: ag_models.AGTestCaseResult
        self.ag_cmd_result1 = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd1, self.ag_case_result1)

        self.ag_suite_result2 = ag_models.AGTestSuiteResult.objects.validate_and_create(
            ag_test_suite=self.ag_test_suite2, submission=self.submission
        )  # type: ag_models.AGTestSuiteResult
        self.ag_case_result2 = ag_models.AGTestCaseResult.objects.validate_and_create(
            ag_test_suite_result=self.ag_suite_result2, ag_test_case=self.ag_test_case2
        )  # type: ag_models.AGTestCaseResult
        self.ag_cmd_result2 = obj_build.make_correct_ag_test_command_result(
            self.ag_test_cmd2, self.ag_case_result2)

        self.num_student_tests = 6
        self.student_tests = ['test{}'.format(i) for i in range(self.num_student_tests)]
        self.student_suite_result1 = ag_models.StudentTestSuiteResult.objects.validate_and_create(
            student_test_suite=self.student_suite1,
            submission=self.submission,
            student_tests=self.student_tests,
            bugs_exposed=self.student_suite1.buggy_impl_names
        )  # type: ag_models.StudentTestSuiteResult
        self.student_suite_result2 = ag_models.StudentTestSuiteResult.objects.validate_and_create(
            student_test_suite=self.student_suite2,
            submission=self.submission,
            student_tests=self.student_tests,
            bugs_exposed=self.student_suite2.buggy_impl_names
        )  # type: ag_models.StudentTestSuiteResult

        self.total_points_per_ag_suite = self.ag_suite_result1.get_fdbk(
            ag_models.FeedbackCategory.max).total_points

        self.total_points_per_student_suite = self.num_buggy_impls * self.points_per_bug_exposed

        self.total_points = (self.total_points_per_ag_suite * 2
                             + self.total_points_per_student_suite * 2)
        self.total_points_possible = self.total_points

        self.assertEqual(
            self.total_points_per_ag_suite,
            self.ag_suite_result2.get_fdbk(ag_models.FeedbackCategory.max).total_points)

        self.assertEqual(
            self.total_points_per_student_suite,
            self.student_suite_result1.get_fdbk(ag_models.FeedbackCategory.max).total_points)

        print(self.total_points)
        self.assertNotEqual(0, self.total_points_per_ag_suite)
        self.assertNotEqual(0, self.total_points_per_student_suite)
        self.assertNotEqual(0, self.total_points)

    def test_max_fdbk(self):
        fdbk = self.submission.get_fdbk(ag_models.FeedbackCategory.max)
        self.assertEqual(self.total_points, fdbk.total_points)
        self.assertEqual(self.total_points, fdbk.total_points_possible)

        self.assertSequenceEqual([self.ag_suite_result1, self.ag_suite_result2],
                                 fdbk.ag_test_suite_results)

        self.assertSequenceEqual([self.student_suite_result1, self.student_suite_result2],
                                 fdbk.student_test_suite_results)

    def test_ag_suite_result_ordering(self):
        for i in range(2):
            self.project.set_agtestsuite_order([self.ag_test_suite2.pk, self.ag_test_suite1.pk])
            fdbk = self.submission.get_fdbk(ag_models.FeedbackCategory.max)
            self.assertSequenceEqual([self.ag_suite_result2, self.ag_suite_result1],
                                     fdbk.ag_test_suite_results)

            self.project.set_agtestsuite_order([self.ag_test_suite1.pk, self.ag_test_suite2.pk])
            fdbk = self.submission.get_fdbk(ag_models.FeedbackCategory.max)
            self.assertSequenceEqual([self.ag_suite_result1, self.ag_suite_result2],
                                     fdbk.ag_test_suite_results)

    def test_student_suite_result_ordering(self):
        for i in range(2):
            self.project.set_studenttestsuite_order(
                [self.student_suite2.pk, self.student_suite1.pk])
            fdbk = self.submission.get_fdbk(ag_models.FeedbackCategory.max)
            self.assertSequenceEqual([self.student_suite_result2, self.student_suite_result1],
                                     fdbk.student_test_suite_results)

            self.project.set_studenttestsuite_order(
                [self.student_suite1.pk, self.student_suite2.pk])
            fdbk = self.submission.get_fdbk(ag_models.FeedbackCategory.max)
            self.assertSequenceEqual([self.student_suite_result1, self.student_suite_result2],
                                     fdbk.student_test_suite_results)

    def test_max_fdbk_some_incorrect(self):
        # Make something incorrect, re-check total points and total points
        # possible.
        self.ag_cmd_result1.return_code_correct = False
        self.ag_cmd_result1.stdout_correct = False
        self.ag_cmd_result1.stderr_correct = False
        self.ag_cmd_result1.save()

        self.student_suite_result1.bugs_exposed = []
        self.student_suite_result1.save()

        fdbk = self.submission.get_fdbk(ag_models.FeedbackCategory.max)

        self.assertEqual(self.total_points_per_ag_suite + self.total_points_per_student_suite,
                         fdbk.total_points)
        self.assertEqual(self.total_points_possible, fdbk.total_points_possible)

        # Make sure that adjusting max_points for a student test suite propagates
        max_points = self.points_per_bug_exposed
        self.student_suite2.validate_and_update(max_points=max_points)

        fdbk = self.submission.get_fdbk(ag_models.FeedbackCategory.max)
        self.assertEqual(self.total_points_per_ag_suite + max_points,
                         fdbk.total_points)
        self.assertEqual(
            self.total_points_per_ag_suite * 2 + self.total_points_per_student_suite + max_points,
            fdbk.total_points_possible)

    def test_normal_fdbk(self):
        self.ag_test_cmd1.normal_fdbk_config.validate_and_update(
            visible=False,
            return_code_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            stdout_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            stderr_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            show_points=True)
        self.ag_test_cmd2.normal_fdbk_config.validate_and_update(
            stdout_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            stderr_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            show_points=True)

        self.student_suite1.normal_fdbk_config.validate_and_update(
            bugs_exposed_fdbk_level=ag_models.BugsExposedFeedbackLevel.num_bugs_exposed,
            show_points=True)

        expected_points = (
            self.total_points_per_ag_suite - self.ag_test_cmd2.points_for_correct_return_code
            + self.total_points_per_student_suite)

        fdbk = self.submission.get_fdbk(ag_models.FeedbackCategory.normal)
        self.assertEqual(expected_points, fdbk.total_points)
        self.assertEqual(expected_points, fdbk.total_points_possible)

        self.assertSequenceEqual([self.ag_suite_result1, self.ag_suite_result2],
                                 fdbk.ag_test_suite_results)
        actual_cmd_results = fdbk.to_dict()[
            'ag_test_suite_results'][0]['ag_test_case_results'][0]['ag_test_command_results']
        self.assertSequenceEqual([], actual_cmd_results)

        self.assertSequenceEqual([self.student_suite_result1, self.student_suite_result2],
                                 fdbk.student_test_suite_results)

    def test_past_limit_fdbk(self):
        self.ag_test_cmd2.past_limit_submission_fdbk_config.validate_and_update(
            visible=False,
            return_code_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            stdout_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            stderr_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            show_points=True)
        self.ag_test_cmd1.past_limit_submission_fdbk_config.validate_and_update(
            return_code_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            stderr_fdbk_level=ag_models.ValueFeedbackLevel.correct_or_incorrect,
            show_points=True
        )

        self.student_suite2.past_limit_submission_fdbk_config.validate_and_update(
            bugs_exposed_fdbk_level=ag_models.BugsExposedFeedbackLevel.num_bugs_exposed,
            show_points=True)

        expected_points = (
            self.total_points_per_ag_suite - self.ag_test_cmd1.points_for_correct_stdout)
        fdbk = self.submission.get_fdbk(ag_models.FeedbackCategory.past_limit_submission)
        self.assertEqual(expected_points, fdbk.total_points)
        self.assertEqual(expected_points, fdbk.total_points_possible)

        self.assertSequenceEqual([self.ag_suite_result1, self.ag_suite_result2],
                                 fdbk.ag_test_suite_results)
        actual_cmd_results = fdbk.to_dict()[
            'ag_test_suite_results'][1]['ag_test_case_results'][0]['ag_test_command_results']
        self.assertSequenceEqual([], actual_cmd_results)

        self.assertSequenceEqual([], fdbk.student_test_suite_results)

    def test_ultimate_fdbk(self):
        self.ag_test_cmd1.ultimate_submission_fdbk_config.validate_and_update(visible=False)
        self.student_suite1.ultimate_submission_fdbk_config.validate_and_update(visible=False)
        fdbk = self.submission.get_fdbk(ag_models.FeedbackCategory.ultimate_submission)
        self.assertEqual(self.total_points_per_ag_suite + self.total_points_per_student_suite,
                         fdbk.total_points)
        self.assertEqual(self.total_points_per_ag_suite + self.total_points_per_student_suite,
                         fdbk.total_points_possible)

        self.assertSequenceEqual([self.ag_suite_result1, self.ag_suite_result2],
                                 fdbk.ag_test_suite_results)
        actual_cmd_results = fdbk.to_dict()[
            'ag_test_suite_results'][0]['ag_test_case_results'][0]['ag_test_command_results']
        self.assertSequenceEqual([], actual_cmd_results)

        self.assertSequenceEqual([self.student_suite_result2], fdbk.student_test_suite_results)

    def test_individual_suite_result_order(self):
        self.project.set_agtestsuite_order([self.ag_test_suite2.pk, self.ag_test_suite1.pk])
        self.project.set_studenttestsuite_order([self.student_suite2.pk, self.student_suite1.pk])

        self.submission = get_submissions_with_results_queryset(
            ag_models.FeedbackCategory.max).get(pk=self.submission.pk)
        fdbk = self.submission.get_fdbk(ag_models.FeedbackCategory.max)

        self.assertSequenceEqual([self.ag_suite_result2, self.ag_suite_result1],
                                 fdbk.ag_test_suite_results)
        self.assertSequenceEqual(
            [self.ag_suite_result2.get_fdbk(ag_models.FeedbackCategory.max).to_dict(),
             self.ag_suite_result1.get_fdbk(ag_models.FeedbackCategory.max).to_dict()],
            fdbk.to_dict()['ag_test_suite_results'])

        self.assertSequenceEqual([self.student_suite_result2, self.student_suite_result1],
                                 fdbk.student_test_suite_results)
        self.assertSequenceEqual(
            [self.student_suite_result2.get_fdbk(ag_models.FeedbackCategory.max).to_dict(),
             self.student_suite_result1.get_fdbk(ag_models.FeedbackCategory.max).to_dict()],
            fdbk.to_dict()['student_test_suite_results'])

    def test_some_ag_and_student_test_suites_not_visible(self):
        self.ag_test_suite2.ultimate_submission_fdbk_config.validate_and_update(visible=False)
        self.student_suite2.ultimate_submission_fdbk_config.validate_and_update(visible=False)

        fdbk = self.submission.get_fdbk(ag_models.FeedbackCategory.ultimate_submission)
        self.assertEqual(self.total_points_per_ag_suite + self.total_points_per_student_suite,
                         fdbk.total_points)
        self.assertEqual(self.total_points_per_ag_suite + self.total_points_per_student_suite,
                         fdbk.total_points_possible)

        self.assertSequenceEqual([self.ag_suite_result1], fdbk.ag_test_suite_results)
        self.assertSequenceEqual(
            [self.ag_suite_result1.get_fdbk(
                ag_models.FeedbackCategory.ultimate_submission).to_dict()],
            fdbk.to_dict()['ag_test_suite_results'])

        self.assertSequenceEqual([self.student_suite_result1], fdbk.student_test_suite_results)
        self.assertSequenceEqual(
            [self.student_suite_result1.get_fdbk(
                ag_models.FeedbackCategory.ultimate_submission).to_dict()],
            fdbk.to_dict()['student_test_suite_results'])

    def test_fdbk_to_dict(self):
        expected = {
            'pk': self.submission.pk,
            'total_points': self.total_points,
            'total_points_possible': self.total_points,
            'ag_test_suite_results': [
                self.ag_suite_result1.get_fdbk(ag_models.FeedbackCategory.max).to_dict(),
                self.ag_suite_result2.get_fdbk(ag_models.FeedbackCategory.max).to_dict()
            ],
            'student_test_suite_results': [
                self.student_suite_result1.get_fdbk(ag_models.FeedbackCategory.max).to_dict(),
                self.student_suite_result2.get_fdbk(ag_models.FeedbackCategory.max).to_dict(),
            ]
        }

        actual = self.submission.get_fdbk(ag_models.FeedbackCategory.max).to_dict()
        print(json.dumps(actual, indent=4, sort_keys=True))
        self.assertEqual(expected, actual)
