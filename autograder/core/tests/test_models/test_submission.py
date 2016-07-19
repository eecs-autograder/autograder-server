import os

from collections import namedtuple

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from autograder.core.models.autograder_test_case import feedback_config

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.core.models as ag_models
import autograder.core.shared.utilities as ut

import autograder.core.tests.dummy_object_utils as obj_ut


class SubmissionTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.submission_group = obj_ut.build_submission_group(num_members=2)
        self.project = self.submission_group.project

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

        for pattern_settings in expected_files:
            ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
                **pattern_settings)

    def test_to_dict_default_fields(self):
        expected = [
            'submission_group',
            'timestamp',
            'submitter',
            'submitted_filenames',
            'discarded_files',
            'missing_files',
            'status',
            'grading_errors',

            'count_towards_daily_limit',
            'is_past_daily_limit',

            'basic_score',
        ]
        self.assertCountEqual(
            expected,
            ag_models.Submission.get_default_to_dict_fields())
        group = obj_ut.build_submission_group()
        submission = ag_models.Submission(submission_group=group)
        self.assertTrue(submission.to_dict())

    def test_editable_fields(self):
        self.assertCountEqual(['count_towards_daily_limit'],
                              ag_models.Submission.get_editable_fields())

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
            submission_group=self.submission_group,
            submitted_files=[
                SimpleUploadedFile(name, content) for
                name, content in files_to_submit],
            submitter=submitter)

        submission.refresh_from_db()

        self.assertEqual(submitter, submission.submitter)
        self.assertEqual(
            submission.status,
            ag_models.Submission.GradingStatus.received)
        self.assertCountEqual(submission.grading_errors, [])
        self.assertCountEqual(submission.missing_files, [])
        self.assertCountEqual(
            (file_.name for file_ in files_to_submit),
            submission.submitted_filenames)

        self.assertTrue(submission.count_towards_daily_limit)
        self.assertFalse(submission.is_past_daily_limit)

        self.assertLess(submission.timestamp - now,
                        timezone.timedelta(seconds=2))

        # Check file contents in the filesystem
        self.assertTrue(os.path.isdir(ut.get_submission_dir(submission)))
        with ut.ChangeDirectory(ut.get_submission_dir(submission)):
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
        count_towards_daily_limit = False

        sub = ag_models.Submission.objects.validate_and_create(
            [], submission_group=self.submission_group, timestamp=timestamp,
            count_towards_daily_limit=count_towards_daily_limit)

        sub.refresh_from_db()

        self.assertEqual(timestamp, sub.timestamp)
        self.assertEqual(count_towards_daily_limit,
                         sub.count_towards_daily_limit)

    def test_submission_missing_required_file(self):
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('test_spam.cpp', b'cheeese')
        ]

        submission = ag_models.Submission.objects.validate_and_create(
            submission_group=self.submission_group,
            submitted_files=files)

        submission.refresh_from_db()

        self.assertEqual(
            submission.status, ag_models.Submission.GradingStatus.received)
        self.assertEqual({'eggs.cpp': 1}, submission.missing_files)

    def test_submission_not_enough_files_matching_pattern(self):
        self.project.expected_student_file_patterns.get(
            max_num_matches=2
        ).validate_and_update(min_num_matches=2, max_num_matches=3)
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
            SimpleUploadedFile('test_spam.cpp', b'yarp')
        ]

        submission = ag_models.Submission.objects.validate_and_create(
            submission_group=self.submission_group,
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

        submission = ag_models.Submission.objects.validate_and_create(
            submission_group=self.submission_group,
            submitted_files=files + extra_files)

        submission.refresh_from_db()

        self.assertEqual(
            submission.status, ag_models.Submission.GradingStatus.received)
        self.assertCountEqual(
            (file_.name for file_ in files),
            submission.get_submitted_file_basenames())

        self.assertCountEqual((file_.name for file_ in extra_files),
                              submission.discarded_files)

    def test_extra_files_discarded(self):
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
            SimpleUploadedFile('test_spam.cpp', b'cheeese'),
        ]
        extra_files = [
            SimpleUploadedFile('extra.cpp', b'merp'),
            SimpleUploadedFile('extra_extra.cpp', b'spam')]

        submission = ag_models.Submission.objects.validate_and_create(
            submission_group=self.submission_group,
            submitted_files=files + extra_files)

        submission.refresh_from_db()

        self.assertEqual(ag_models.Submission.GradingStatus.received,
                         submission.status)
        self.assertCountEqual(submission.get_submitted_file_basenames(),
                              (file_.name for file_ in files))

        self.assertCountEqual(submission.discarded_files,
                              (file_.name for file_ in extra_files))

        with ut.ChangeDirectory(ut.get_submission_dir(submission)):
            for file_ in extra_files:
                self.assertFalse(os.path.exists(file_.name))

    ## NOTE: Django's uploaded file classes automatically strip path
    ## characters from filenames.
    # def test_files_with_illegal_names_discarded(self):
    #     files = [
    #         SimpleUploadedFile('spam.cpp', b'blah'),
    #         SimpleUploadedFile('eggs.cpp', b'merp'),
    #         SimpleUploadedFile('test_spam.cpp', b'cheeese'),
    #     ]
    #     illegal_files = [
    #         SimpleUploadedFile('; echo "haxorz!" #', b'merp'),
    #         SimpleUploadedFile('@$#%@$#^%$badfilename.bad', b'bad')]

    #     files += illegal_files

    #     Submission.objects.validate_and_create(
    #         submission_group=self.submission_group,
    #         submitted_files=files)

    #     loaded_submission = Submission.objects.get(
    #         submission_group=self.submission_group)

    #     self.assertEqual(
    #         Submission.GradingStatus.received, loaded_submission.status)
    #     self.assertCountEqual(
    #         loaded_submission.get_submitted_file_basenames(),
    #         ['spam.cpp', 'eggs.cpp', 'test_spam.cpp'])

    #     self.assertCountEqual(
    #         loaded_submission.discarded_files,
    #         [file_.name for file_ in illegal_files])

    #     with ut.ChangeDirectory(ut.get_submission_dir(loaded_submission)):
    #         for file_ in illegal_files:
    #             self.assertFalse(os.path.exists(file_.name))

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

        submission = ag_models.Submission.objects.validate_and_create(
            submission_group=self.submission_group,
            submitted_files=files + duplicate_files)

        submission.refresh_from_db()

        self.assertEqual(ag_models.Submission.GradingStatus.received,
                         submission.status)
        self.assertCountEqual(submission.get_submitted_file_basenames(),
                              (file_.name for file_ in files))

        self.assertCountEqual(submission.discarded_files,
                              (file_.name for file_ in duplicate_files))

    def test_is_ultimate_submission(self):
        # most recent
        # best
        self.fail()

    def test_is_ultimate_submission_criteria_not_met(self):
        self.fail()


class TotalPointsTestCase(TemporaryFilesystemTestCase):
    def test_basic_score(self):
        cache.clear()

        # Increase this number when benchmarking
        num_tests = 10
        min_fdbk = feedback_config.FeedbackConfig.objects.validate_and_create()
        submissions, tests = obj_ut.build_submissions_with_results(
            test_fdbk=min_fdbk, num_tests=num_tests)
        submission = submissions[0]

        self.assertEqual(0, submission.basic_score)

        for test in tests:
            test.validate_and_update(
                feedback_configuration=(
                    feedback_config.FeedbackConfig.create_with_max_fdbk()))

        expected_points = (
            obj_ut.build_compiled_ag_test.points_with_all_used * num_tests)
        actual_points = sum((result.basic_score
                             for result in submission.results.all()))
        self.assertEqual(expected_points, actual_points)

        # # Benchmarks
        # for i in range(10):
        #     cache.clear()
        #     with ut.Timer('Aggregated {} tests '
        #                   'from empty cache.'.format(num_tests)):
        #         actual_points = submission.basic_score

        # for i in range(10):
        #     cache.delete(submission.basic_score_cache_key)
        #     with ut.Timer('Aggregated {} tests from '
        #                   'cached results only.'.format(num_tests)):
        #         actual_points = submission.basic_score

        # for i in range(10):
        #     with ut.Timer('Aggregated {} tests '
        #                   'from full cache.'.format(num_tests)):
        #         actual_points = submission.basic_score

        self.assertEqual(expected_points, submission.basic_score)

    def test_cache_invalidation(self):
        num_tests = 2
        submissions, tests = obj_ut.build_submissions_with_results(
            num_submissions=2, num_tests=num_tests)
        test_case = tests[0]

        expected_points = (
            obj_ut.build_compiled_ag_test.points_with_all_used * num_tests)
        for submission in submissions:
            self.assertEqual(expected_points, submission.basic_score)

        test_case.points_for_correct_return_code += 1
        test_case.save()

        expected_points += 1
        for submission in submissions:
            self.assertEqual(expected_points, submission.basic_score)

        test_case.feedback_configuration.validate_and_update(
            points_fdbk=feedback_config.PointsFdbkLevel.hide)

        expected_points -= (
            obj_ut.build_compiled_ag_test.points_with_all_used + 1)
        for submission in submissions:
            self.assertEqual(expected_points, submission.basic_score)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class SubmissionQueryFunctionTests(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.project = obj_ut.build_project()

    def test_get_most_recent_submissions_normal(self):
        groups = [
            obj_ut.build_submission_group(
                group_kwargs={'project': self.project})
            for i in range(10)
        ]

        expected_final_subs = []
        for group in groups:
            num_submissions = 4
            for i in range(num_submissions):
                sub = ag_models.Submission.objects.validate_and_create(
                    submitted_files=[], submission_group=group)
                if i == num_submissions - 1:
                    expected_final_subs.append(sub)

        self.assertCountEqual(
            expected_final_subs,
            ag_models.Submission.get_most_recent_submissions(self.project))

    def test_get_most_recent_submissions_group_has_no_submissions(self):
        group = obj_ut.build_submission_group()
        self.assertCountEqual([], group.submissions.all())
        self.assertCountEqual(
            [], ag_models.Submission.get_most_recent_submissions(self.project))
