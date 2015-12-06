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

    def test_valid_init_with_defaults(self):
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
        self.assertFalse(loaded_submission.show_all_test_cases)
        self.assertEqual(loaded_submission.timestamp, submission.timestamp)
        self.assertIsNone(loaded_submission.test_case_feedback_config_override)
        self.assertIsNone(
            loaded_submission.student_test_suite_feedback_config_override)
        self.assertEqual(
            loaded_submission.status,
            Submission.GradingStatus.received)
        self.assertEqual(loaded_submission.invalid_reason_or_error, [])

        self.assertTrue(os.path.isdir(ut.get_submission_dir(submission)))
        with ut.ChangeDirectory(ut.get_submission_dir(submission)):
            for name, content in submit_file_data:
                self.assertTrue(
                    os.path.isfile(os.path.basename(name)))
                with open(name) as f:
                    self.assertEqual(content.decode('utf-8'), f.read())

        iterable = enumerate(
            sorted(loaded_submission.submitted_files,
                   key=lambda obj: obj.name))
        for index, value in iterable:
            self.assertEqual(
                submit_file_data[index].name, os.path.basename(value.name))
            self.assertEqual(submit_file_data[index].content, value.read())

    import unittest
    @unittest.skip('TODO')
    def test_valid_init_with_non_defaults(self):
        self.fail()
        # submit_file_data = sorted([
        #     SimpleUploadedFile('spam.cpp', b'blah'),
        #     SimpleUploadedFile('eggs.cpp', b'merp'),
        #     SimpleUploadedFile('test_spam.cpp', b'cheeese')
        # ])

        # submission = Submission.objects.validate_and_create(
        #     submission_group=self.submission_group,
        #     submitted_files=[
        #         SimpleUploadedFile(name, content) for
        #         name, content in submit_file_data],

        #     )

        # loaded_submission = Submission.objects.get(
        #     submission_group=self.submission_group)

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
            SimpleUploadedFile('; echo "haxorz!" # ', b'merp'),
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
        usernames = ["recent_submission_user{}".format(i) for i in range(10)]
        groups = [
            SubmissionGroup.objects.validate_and_create(
                members=[username], project=self.project)
            for username in usernames
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

    def test_get_most_recent_submissions_group_has_no_submissions(self):
        group = SubmissionGroup.objects.validate_and_create(
            members=['steve'], project=self.project)
        self.assertSequenceEqual([], group.submissions.all())
        self.assertSequenceEqual(
            [], Submission.get_most_recent_submissions(self.project))
