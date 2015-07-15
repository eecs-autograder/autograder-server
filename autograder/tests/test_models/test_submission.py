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


def _make_dummy_user(username, password):
    user = User.objects.create(username=username)
    user.set_password(password)
    return user


class SubmissionTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = Course.objects.create(name='eecs280')
        self.semester = Semester.objects.create(name='f15', course=self.course)

        self.project = Project.objects.create(
            name='my_project', semester=self.semester, max_group_size=2,
            required_student_files=['spam.cpp', 'eggs.cpp'])

        self.project.add_expected_student_file_pattern('test_*.cpp', 1, 2)

        self.group_members = [
            _make_dummy_user('steve', 'spam'),
            _make_dummy_user('joe', 'eggs')
        ]

        self.submission_group = SubmissionGroup.objects.create_group(
            self.group_members, self.project)

    def test_valid_init(self):
        SimpleFileTuple = namedtuple('SimpleFileTuple', ['name', 'content'])

        submit_file_data = sorted([
            SimpleFileTuple('spam.cpp', b'blah'),
            SimpleFileTuple('eggs.cpp', b'merp'),
            SimpleFileTuple('test_spam.cpp', b'cheeese')
        ])

        submission = Submission.objects.validate_and_create(
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

    def test_exception_on_submission_missing_files(self):
        with self.assertRaises(ValidationError):
            Submission.objects.validate_and_create(
                submission_group=self.submission_group,
                submitted_files=[
                    SimpleUploadedFile('eggs.cpp', b'merp'),
                    SimpleUploadedFile('test_spam.cpp', b'cheeese')])

        with self.assertRaises(ValidationError):
            Submission.objects.validate_and_create(
                submission_group=self.submission_group,
                submitted_files=[
                    SimpleUploadedFile('spam.cpp', b'blah'),
                    SimpleUploadedFile('eggs.cpp', b'merp')])

    def test_exception_on_extra_file_no_ignore(self):
        with self.assertRaises(ValidationError):
            Submission.objects.validate_and_create(
                submission_group=self.submission_group,
                ignore_extra_files=False,
                submitted_files=[
                    SimpleUploadedFile('spam.cpp', b'blah'),
                    SimpleUploadedFile('eggs.cpp', b'merp'),
                    SimpleUploadedFile('test_spam.cpp', b'cheeese'),
                    SimpleUploadedFile('extra.cpp', b'toomuch')])

    def test_no_exception_on_extra_file_with_ignore(self):
        Submission.objects.validate_and_create(
            submission_group=self.submission_group,
            submitted_files=[
                SimpleUploadedFile('spam.cpp', b'blah'),
                SimpleUploadedFile('eggs.cpp', b'merp'),
                SimpleUploadedFile('test_spam.cpp', b'cheeese'),
                SimpleUploadedFile('extra.cpp', b'toomuch')])

    def test_exception_on_submit_same_file_twice(self):
        with self.assertRaises(ValidationError):
            Submission.objects.validate_and_create(
                submission_group=self.submission_group,
                submitted_files=[
                    SimpleUploadedFile('spam.cpp', b'blah'),
                    SimpleUploadedFile('spam.cpp', b'blah')])
