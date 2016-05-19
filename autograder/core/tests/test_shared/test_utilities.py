import os
import re

from django.test import TestCase
from django.conf import settings
from django.core.exceptions import ValidationError

import autograder.core.models as ag_models
import autograder.core.shared.utilities as ut
import autograder.core.shared.global_constants as gc

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.core.tests.dummy_object_utils as obj_ut


class TestFileSystemNavigationUtils(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.original_dir = os.getcwd()
        os.chdir(settings.MEDIA_ROOT)

    def tearDown(self):
        super().tearDown()

        os.chdir(self.original_dir)

    def test_change_directory(self):
        new_dirname = 'my_dir'
        os.mkdir('my_dir')

        self.assertEqual(os.getcwd(), settings.MEDIA_ROOT)

        with ut.ChangeDirectory(new_dirname):
            self.assertEqual(
                os.path.join(settings.MEDIA_ROOT, new_dirname),
                os.getcwd())

        self.assertEqual(os.getcwd(), settings.MEDIA_ROOT)

    def test_temporary_file(self):
        filename = 'spam_file'
        contents = "alsdkjflasjdfla;sdjf"
        self.assertFalse(os.path.exists(filename))

        with ut.TemporaryFile(filename, contents):
            self.assertTrue(os.path.isfile(filename))
            with open(filename) as f:
                self.assertEqual(f.read(), contents)

        self.assertFalse(os.path.exists(filename))

    def test_temporary_directory(self):
        dirname = 'eggs_dir'
        self.assertFalse(os.path.exists(dirname))

        with ut.TemporaryDirectory(dirname):
            self.assertTrue(os.path.isdir(dirname))

        self.assertFalse(os.path.exists(dirname))


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class CheckValuesAgainstWhitelistTestCase(TestCase):
    def setUp(self):
        self.regex = r'spam.*'

    def test_valid_values(self):
        ut.check_values_against_whitelist(
            ['spam', 'spam1', 'spam2'], self.regex)

        ut.check_values_against_whitelist(
            ['spam', 'spam1', 'spam2'], re.compile(self.regex))

    def test_invalid_values(self):
        with self.assertRaises(ValidationError):
            ut.check_values_against_whitelist(
                ['spam', 'spam1', 'badspam', 'spam2'], self.regex)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class CheckUserProvidedFilenameTest(TestCase):
    def test_valid_filename(self):
        ut.check_user_provided_filename('spAM-eggs_42.cpp')

    def test_exception_on_file_path_given(self):
        with self.assertRaises(ValidationError):
            ut.check_user_provided_filename('../spam.txt')

        with self.assertRaises(ValidationError):
            ut.check_user_provided_filename('..')

    def test_exception_on_filename_with_shell_chars(self):
        with self.assertRaises(ValidationError):
            ut.check_user_provided_filename('; echo "haxorz"; # ')

    def test_exception_on_filename_starts_with_dot(self):
        with self.assertRaises(ValidationError):
            ut.check_user_provided_filename('.spameggs')

    def test_exception_null_filename(self):
        with self.assertRaises(ValidationError):
            ut.check_user_provided_filename(None)
            ut.check_user_provided_filename(None, allow_empty=True)

    def test_exception_empty_filename(self):
        with self.assertRaises(ValidationError):
            ut.check_user_provided_filename('')

    def test_no_exception_empty_filename_allowed(self):
        ut.check_user_provided_filename('', allow_empty=True)


class FileSystemUtilTestCase(TestCase):
    def setUp(self):
        self.group = obj_ut.build_submission_group()
        self.project = self.group.project
        self.course = self.project.course

        self.group_dir_basename = 'group{}'.format(self.group.pk)
        self.course_dirname = 'course{}'.format(self.course.pk)
        self.project_dirname = 'project{}'.format(self.project.pk)

    def test_get_course_root_dir(self):
        expected_relative = "{0}/{1}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname)

        actual_relative = ut.get_course_relative_root_dir(self.course)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = settings.MEDIA_ROOT + expected_relative

        actual_absolute = ut.get_course_root_dir(self.course)
        self.assertEqual(expected_absolute, actual_absolute)

    def test_get_project_root_dir(self):
        expected_relative = "{0}/{1}/{2}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname,
            self.project_dirname)

        actual_relative = ut.get_project_relative_root_dir(self.project)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = settings.MEDIA_ROOT + expected_relative

        actual_absolute = ut.get_project_root_dir(self.project)
        self.assertEqual(expected_absolute, actual_absolute)

    def test_get_project_files_dir(self):
        expected_relative = "{0}/{1}/{2}/{3}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname,
            self.project_dirname, gc.PROJECT_FILES_DIRNAME)

        actual_relative = ut.get_project_files_relative_dir(self.project)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = settings.MEDIA_ROOT + expected_relative

        actual_absolute = ut.get_project_files_dir(self.project)
        self.assertEqual(expected_absolute, actual_absolute)

    def test_get_project_submission_groups_dir(self):
        expected_relative = "{0}/{1}/{2}/{3}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname,
            self.project_dirname,
            gc.PROJECT_SUBMISSIONS_DIRNAME)
        actual_relative = ut.get_project_submission_groups_relative_dir(
            self.project)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = settings.MEDIA_ROOT + expected_relative
        actual_absolute = ut.get_project_submission_groups_dir(
            self.project)
        self.assertEqual(expected_absolute, actual_absolute)

    def test_get_student_submission_group_dir(self):
        expected_relative = "{0}/{1}/{2}/{3}/{4}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname,
            self.project_dirname,
            gc.PROJECT_SUBMISSIONS_DIRNAME,
            self.group_dir_basename)

        actual_relative = ut.get_student_submission_group_relative_dir(
            self.group)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = settings.MEDIA_ROOT + expected_relative
        actual_absolute = ut.get_student_submission_group_dir(self.group)

        self.assertEqual(expected_absolute, actual_absolute)

    def test_get_submission_dir(self):
        submission = ag_models.Submission.objects.validate_and_create(
            submission_group=self.group, submitted_files=[])
        submission_dir_basename = 'submission{}'.format(submission.pk)

        expected_relative = "{0}/{1}/{2}/{3}/{4}/{5}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME,
            self.course_dirname,
            self.project_dirname,
            gc.PROJECT_SUBMISSIONS_DIRNAME,
            self.group_dir_basename, submission_dir_basename)

        actual_relative = ut.get_submission_relative_dir(submission)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = settings.MEDIA_ROOT + expected_relative
        actual_absolute = ut.get_submission_dir(submission)
        self.assertEqual(expected_absolute, actual_absolute)
