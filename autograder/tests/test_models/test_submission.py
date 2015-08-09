import os

from collections import namedtuple

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from autograder.models import (
    Course, Semester, Project, Submission, SubmissionGroup)

import autograder.shared.utilities as ut

import autograder.tests.dummy_object_utils as obj_ut


class SubmissionTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = Course.objects.create(name='eecs280')
        self.semester = Semester.objects.create(name='f15', course=self.course)

        self.project = Project.objects.create(
            name='my_project', semester=self.semester, max_group_size=2,
            required_student_files=['spam.cpp', 'eggs.cpp'],
            expected_student_file_patterns=[
                Project.FilePatternTuple('test_*.cpp', 1, 2)])

        self.group_members = obj_ut.create_dummy_users(2)
        self.semester.add_enrolled_students(*self.group_members)

        self.submission_group = SubmissionGroup.objects.create_group(
            self.group_members, self.project)

    def test_valid_init(self):
        SimpleFileTuple = namedtuple('SimpleFileTuple', ['name', 'content'])

        submit_file_data = sorted([
            SimpleFileTuple('spam.cpp', b'blah'),
            SimpleFileTuple('eggs.cpp', b'merp'),
            SimpleFileTuple('test_spam.cpp', b'cheeese')
        ])

        submission = Submission.objects.create_submission(
            submission_group=self.submission_group,
            submitted_files=[
                SimpleUploadedFile(name, content) for
                name, content in submit_file_data])

        loaded_submission = Submission.objects.get(
            submission_group=self.submission_group)

        self.assertEqual(loaded_submission, submission)
        self.assertEqual(
            loaded_submission.submission_group, self.submission_group)
        self.assertEqual(loaded_submission.timestamp, submission.timestamp)
        self.assertIsNone(loaded_submission.test_case_feedback_config_override)
        self.assertEqual(
            loaded_submission.status,
            Submission.GradingStatus.received)
        self.assertEqual(loaded_submission.invalid_reason, [])

        self.assertTrue(os.path.isdir(ut.get_submission_dir(submission)))
        with ut.ChangeDirectory(ut.get_submission_dir(submission)):
            for name, content in submit_file_data:
                self.assertTrue(
                    os.path.isfile(os.path.basename(name)))
                with open(name) as f:
                    self.assertEqual(content.decode('utf-8'), f.read())

        iterable = enumerate(
            sorted(loaded_submission.get_submitted_files(),
                   key=lambda obj: obj.name))
        for index, value in iterable:
            self.assertEqual(
                submit_file_data[index].name, os.path.basename(value.name))
            self.assertEqual(submit_file_data[index].content, value.read())

    def test_invalid_submission_missing_required_file(self):
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('test_spam.cpp', b'cheeese')
        ]
        Submission.objects.create_submission(
            submission_group=self.submission_group,
            submitted_files=files)

        loaded_submission = Submission.objects.get(
            submission_group=self.submission_group)

        self.assertEqual(
            loaded_submission.status, Submission.GradingStatus.invalid)
        self.assertTrue(loaded_submission.invalid_reason)

    def test_invalid_submission_not_enough_of_pattern(self):
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
        ]
        Submission.objects.create_submission(
            submission_group=self.submission_group,
            submitted_files=files)

        loaded_submission = Submission.objects.get(
            submission_group=self.submission_group)

        self.assertEqual(
            loaded_submission.status, Submission.GradingStatus.invalid)
        self.assertTrue(loaded_submission.invalid_reason)

    def test_invalid_submission_too_much_of_pattern(self):
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
            SimpleUploadedFile('test_spam.cpp', b'cheeese'),
            SimpleUploadedFile('test_egg.cpp', b'cheeese'),
            SimpleUploadedFile('test_sausage.cpp', b'cheeese')
        ]
        Submission.objects.create_submission(
            submission_group=self.submission_group,
            submitted_files=files)

        loaded_submission = Submission.objects.get(
            submission_group=self.submission_group)

        self.assertEqual(
            loaded_submission.status, Submission.GradingStatus.invalid)
        self.assertTrue(loaded_submission.invalid_reason)

    def test_extra_file_discarded(self):
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
            SimpleUploadedFile('test_spam.cpp', b'cheeese'),
        ]
        extra_file = SimpleUploadedFile('extra.cpp', b'merp')
        files.append(extra_file)

        Submission.objects.create_submission(
            submission_group=self.submission_group,
            submitted_files=files)

        loaded_submission = Submission.objects.get(
            submission_group=self.submission_group)

        self.assertEqual(
            Submission.GradingStatus.received, loaded_submission.status)
        self.assertEqual(
            sorted(loaded_submission.get_submitted_file_basenames()),
            sorted(['spam.cpp', 'eggs.cpp', 'test_spam.cpp']))

        with ut.ChangeDirectory(ut.get_submission_dir(loaded_submission)):
            self.assertFalse(os.path.exists(extra_file.name))

    def test_file_with_illegal_name_discarded(self):
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
            SimpleUploadedFile('test_spam.cpp', b'cheeese'),
        ]
        illegal_file = SimpleUploadedFile('; echo "haxorz!" # ', b'merp')
        files.append(illegal_file)

        Submission.objects.create_submission(
            submission_group=self.submission_group,
            submitted_files=files)

        loaded_submission = Submission.objects.get(
            submission_group=self.submission_group)

        self.assertEqual(
            Submission.GradingStatus.received, loaded_submission.status)
        self.assertEqual(
            sorted(loaded_submission.get_submitted_file_basenames()),
            sorted(['spam.cpp', 'eggs.cpp', 'test_spam.cpp']))

        with ut.ChangeDirectory(ut.get_submission_dir(loaded_submission)):
            self.assertFalse(os.path.exists(illegal_file.name))

    def test_duplicate_files_discarded(self):
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
            SimpleUploadedFile('test_spam.cpp', b'cheeese')
        ]
        Submission.objects.create_submission(
            submission_group=self.submission_group,
            submitted_files=files)

        loaded_submission = Submission.objects.get(
            submission_group=self.submission_group)

        self.assertEqual(
            Submission.GradingStatus.received, loaded_submission.status)
        self.assertEqual(
            sorted(loaded_submission.get_submitted_file_basenames()),
            sorted(['spam.cpp', 'eggs.cpp', 'test_spam.cpp']))
