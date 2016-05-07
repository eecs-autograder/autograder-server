import os

from collections import namedtuple

# from django.contrib.auth.models import User
# from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

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
        ]
        self.assertCountEqual(
            expected,
            ag_models.Submission.get_default_to_dict_fields())
        group = obj_ut.build_submission_group()
        submission = ag_models.Submission(submission_group=group)
        self.assertTrue(submission.to_dict())

    def test_valid_init(self):
        SimpleFileTuple = namedtuple('SimpleFileTuple', ['name', 'content'])

        files_to_submit = sorted([
            SimpleFileTuple('spam.cpp', b'blah'),
            SimpleFileTuple('eggs.cpp', b'merp'),
            SimpleFileTuple('test_spam.cpp', b'cheeese')
        ])

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

        # Check file contents in the filesystem
        self.assertTrue(os.path.isdir(ut.get_submission_dir(submission)))
        with ut.ChangeDirectory(ut.get_submission_dir(submission)):
            for name, content in files_to_submit:
                content = content.decode('utf-8')
                self.assertEqual(name, submission.get_file(name).name)
                self.assertEqual(content, submission.get_file(name).read())

                self.assertTrue(
                    os.path.isfile(os.path.basename(name)))
                with open(name) as f:
                    self.assertEqual(content, f.read())

        # Check submitted files using member accessors
        expected = sorted(files_to_submit)
        actual = sorted(submission.submitted_files,
                        key=lambda file_: file_.name)
        for expected_file, loaded_file in zip(expected, actual):
            self.assertEqual(expected_file.name,
                             os.path.basename(loaded_file.name))
            self.assertEqual(expected_file.content.decode('utf-8'),
                             loaded_file.read())

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

    def test_extra_pattern_matching_files_discarded(self):
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

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class SubmissionQueryFunctionTests(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.project = obj_ut.build_project()

        # self.course = Course.objects.validate_and_create(name='eecs280')
        # self.semester = Semester.objects.validate_and_create(
        #     name='f15', course=self.course)

        # self.project = Project.objects.validate_and_create(
        #     name='my_project', semester=self.semester, max_group_size=5,
        #     allow_submissions_from_non_enrolled_students=True)

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

    # import unittest
    # @unittest.skip('todo')
    # def test_get_most_recent_submissions_same_timestamp(self):
    #     self.fail()

    def test_get_most_recent_submissions_group_has_no_submissions(self):
        group = obj_ut.build_submission_group()
        self.assertCountEqual([], group.submissions.all())
        self.assertCountEqual(
            [], ag_models.Submission.get_most_recent_submissions(self.project))
