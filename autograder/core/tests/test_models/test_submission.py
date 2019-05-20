import os
from collections import namedtuple

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
import autograder.utils.testing.model_obj_builders as obj_build
from autograder import utils
from autograder.core import constants
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
        submission: ag_models.Submission = ag_models.Submission.objects.validate_and_create(
            group=self.group,
            submitted_files=[SimpleUploadedFile(name, content)
                             for name, content in files_to_submit],
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

        self.assertTrue(submission.count_towards_total_limit)

        self.assertFalse(submission.is_bonus_submission)

        self.assertEqual([], submission.does_not_count_for)

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
            'is_bonus_submission',

            'count_towards_total_limit',

            'does_not_count_for',

            'position_in_queue',

            'last_modified'
        ]
        self.assertCountEqual(
            expected,
            ag_models.Submission.get_serializable_fields())
        group = obj_build.build_group()
        submission = ag_models.Submission(group=group)
        self.assertTrue(submission.to_dict())

    def test_editable_fields(self):
        self.assertCountEqual(['count_towards_daily_limit', 'count_towards_total_limit'],
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

        group1_p1 = obj_build.make_submission(
            group=group1_proj1)
        group1_p1.status = (
            ag_models.Submission.GradingStatus.queued)
        group1_p1.save()
        group1_p1_queue_pos = 1

        group2_p1 = obj_build.make_submission(
            group=group2_proj1)
        group2_p1.status = (
            ag_models.Submission.GradingStatus.queued)
        group2_p1.save()
        group2_p1_queue_pos = 2

        group1_p2 = obj_build.make_submission(
            group=group1_proj2)
        group1_p2.status = (
            ag_models.Submission.GradingStatus.queued)
        group1_p2.save()
        group1_p2_queue_pos = 1

        group2_p2 = obj_build.make_submission(
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
        submission = obj_build.make_submission()

        non_queued_statuses = list(ag_models.Submission.GradingStatus.values)
        non_queued_statuses.remove(ag_models.Submission.GradingStatus.queued)

        for status in non_queued_statuses:
            submission.status = status
            submission.save()
            self.assertEqual(0, submission.position_in_queue)
