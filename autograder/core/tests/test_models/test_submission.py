import os

from collections import namedtuple

# from django.contrib.auth.models import User
# from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from autograder.core.models import (
    Course, Semester, Project, Submission, SubmissionGroup)

import autograder.core.shared.utilities as ut

import autograder.core.tests.dummy_object_utils as obj_ut

# TODO: filesystem test cases


class SubmissionTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = Course.objects.validate_and_create(name='eecs280')
        self.semester = Semester.objects.validate_and_create(
            name='f15', course=self.course)

        self.project = Project.objects.validate_and_create(
            name='my_project', semester=self.semester, max_group_size=2,
            required_student_files=['spam.cpp', 'eggs.cpp'],
            expected_student_file_patterns=[
                Project.FilePatternTuple('test_*.cpp', 1, 2)])

        self.group_members = obj_ut.create_dummy_users(2)
        self.member_names = [member.username for member in self.group_members]
        self.semester.add_enrolled_students(*self.group_members)

        self.submission_group = SubmissionGroup.objects.validate_and_create(
            members=self.member_names, project=self.project)

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
        self.assertEqual(
            loaded_submission.status,
            Submission.GradingStatus.received)
        self.assertEqual(loaded_submission.invalid_reason_or_error, [])
        self.assertCountEqual(
            (file_.name for file_ in submit_file_data),
            loaded_submission.submitted_filenames)

        self.assertTrue(os.path.isdir(ut.get_submission_dir(submission)))
        with ut.ChangeDirectory(ut.get_submission_dir(submission)):
            for name, content in submit_file_data:
                content = content.decode('utf-8')
                self.assertEqual(name, submission.get_file(name).name)
                self.assertEqual(content, submission.get_file(name).read())

                self.assertTrue(
                    os.path.isfile(os.path.basename(name)))
                with open(name) as f:
                    self.assertEqual(content, f.read())

        iterable = enumerate(
            sorted(loaded_submission.submitted_files,
                   key=lambda obj: obj.name))
        for index, value in iterable:
            self.assertEqual(
                submit_file_data[index].name, os.path.basename(value.name))
            self.assertEqual(
                submit_file_data[index].content.decode('utf-8'), value.read())

    def test_invalid_submission_missing_required_file(self):
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('test_spam.cpp', b'cheeese')
        ]
        Submission.objects.validate_and_create(
            submission_group=self.submission_group,
            submitted_files=files)

        loaded_submission = Submission.objects.get(
            submission_group=self.submission_group)

        self.assertEqual(
            loaded_submission.status, Submission.GradingStatus.invalid)
        self.assertTrue(loaded_submission.invalid_reason_or_error)

    def test_invalid_submission_not_enough_of_pattern(self):
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
        ]
        Submission.objects.validate_and_create(
            submission_group=self.submission_group,
            submitted_files=files)

        loaded_submission = Submission.objects.get(
            submission_group=self.submission_group)

        self.assertEqual(
            loaded_submission.status, Submission.GradingStatus.invalid)
        self.assertTrue(loaded_submission.invalid_reason_or_error)

    def test_extra_pattern_matching_files_discarded(self):
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
            SimpleUploadedFile('test_spam.cpp', b'cheeese'),
            SimpleUploadedFile('test_egg.cpp', b'cheeese'),
            SimpleUploadedFile('test_sausage.cpp', b'cheeese')
        ]
        Submission.objects.validate_and_create(
            submission_group=self.submission_group,
            submitted_files=files)

        loaded_submission = Submission.objects.get(
            submission_group=self.submission_group)

        self.assertEqual(
            loaded_submission.status, Submission.GradingStatus.received)
        self.assertSetEqual(
            set(file_.name for file_ in files[:-1]),
            set(loaded_submission.get_submitted_file_basenames()))

        self.assertListEqual(
            [files[-1].name], loaded_submission.discarded_files)

    def test_extra_files_discarded(self):
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
            SimpleUploadedFile('test_spam.cpp', b'cheeese'),
        ]
        extra_files = [
            SimpleUploadedFile('extra.cpp', b'merp'),
            SimpleUploadedFile('extra_extra.cpp', b'spam')]
        files += extra_files

        Submission.objects.validate_and_create(
            submission_group=self.submission_group,
            submitted_files=files)

        loaded_submission = Submission.objects.get(
            submission_group=self.submission_group)

        self.assertEqual(
            Submission.GradingStatus.received, loaded_submission.status)
        self.assertCountEqual(
            loaded_submission.get_submitted_file_basenames(),
            ['spam.cpp', 'eggs.cpp', 'test_spam.cpp'])

        self.assertCountEqual(
            loaded_submission.discarded_files,
            [file_.name for file_ in extra_files])

        with ut.ChangeDirectory(ut.get_submission_dir(loaded_submission)):
            for file_ in extra_files:
                self.assertFalse(os.path.exists(file_.name))

    def test_files_with_illegal_names_discarded(self):
        files = [
            SimpleUploadedFile('spam.cpp', b'blah'),
            SimpleUploadedFile('eggs.cpp', b'merp'),
            SimpleUploadedFile('test_spam.cpp', b'cheeese'),
        ]
        illegal_files = [
            SimpleUploadedFile('; echo "haxorz!" #', b'merp'),
            SimpleUploadedFile('@$#%@$#^%$badfilename.bad', b'bad')]

        files += illegal_files

        Submission.objects.validate_and_create(
            submission_group=self.submission_group,
            submitted_files=files)

        loaded_submission = Submission.objects.get(
            submission_group=self.submission_group)

        self.assertEqual(
            Submission.GradingStatus.received, loaded_submission.status)
        self.assertCountEqual(
            loaded_submission.get_submitted_file_basenames(),
            ['spam.cpp', 'eggs.cpp', 'test_spam.cpp'])

        self.assertCountEqual(
            loaded_submission.discarded_files,
            [file_.name for file_ in illegal_files])

        with ut.ChangeDirectory(ut.get_submission_dir(loaded_submission)):
            for file_ in illegal_files:
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
        files += duplicate_files

        Submission.objects.validate_and_create(
            submission_group=self.submission_group,
            submitted_files=files)

        loaded_submission = Submission.objects.get(
            submission_group=self.submission_group)

        self.assertEqual(
            Submission.GradingStatus.received, loaded_submission.status)
        self.assertCountEqual(
            loaded_submission.get_submitted_file_basenames(),
            ['spam.cpp', 'eggs.cpp', 'test_spam.cpp'])

        self.assertCountEqual(
            loaded_submission.discarded_files,
            [file_.name for file_ in duplicate_files])


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class SubmissionQueryFunctionTests(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = Course.objects.validate_and_create(name='eecs280')
        self.semester = Semester.objects.validate_and_create(
            name='f15', course=self.course)

        self.project = Project.objects.validate_and_create(
            name='my_project', semester=self.semester, max_group_size=5,
            allow_submissions_from_non_enrolled_students=True)

    def test_get_most_recent_submissions_normal(self):
        users = obj_ut.create_dummy_users(10)
        groups = [
            SubmissionGroup.objects.validate_and_create(
                members=[username], project=self.project)
            for username in users
        ]
        expected = []
        for group in groups:
            for i in range(4):
                sub = Submission.objects.validate_and_create(
                    submitted_files=[], submission_group=group)
                if i == 3:
                    expected.append(sub)

        sort_key = lambda obj: obj.pk
        actual = sorted(
            Submission.get_most_recent_submissions(self.project),
            key=sort_key)
        self.assertEqual(sorted(expected, key=sort_key), actual)

    import unittest
    @unittest.skip('todo')
    def test_get_most_recent_submissions_same_timestamp(self):
        self.fail()

    def test_get_most_recent_submissions_group_has_no_submissions(self):
        user = obj_ut.create_dummy_user()
        group = SubmissionGroup.objects.validate_and_create(
            members=[user.username], project=self.project)
        self.assertCountEqual([], group.submissions.all())
        self.assertCountEqual(
            [], Submission.get_most_recent_submissions(self.project))
