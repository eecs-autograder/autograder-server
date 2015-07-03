import os
import re
import collections

from django.test import TestCase
from django.conf import settings

from .temporary_filesystem_test_case import TemporaryFilesystemTestCase

import autograder.shared.utilities as ut
import autograder.shared.global_constants as gc


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
        with self.assertRaises(ValueError):
            ut.check_values_against_whitelist(
                ['spam', 'spam1', 'badspam', 'spam2'], self.regex)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class CheckUserProvidedFilenameTest(TestCase):
    def test_valid_filename(self):
        ut.check_user_provided_filename('spAM-eggs_42.cpp')

    def test_exception_on_file_path_given(self):
        with self.assertRaises(ValueError):
            ut.check_user_provided_filename('../spam.txt')

        with self.assertRaises(ValueError):
            ut.check_user_provided_filename('..')

    def test_exception_on_filename_with_shell_chars(self):
        with self.assertRaises(ValueError):
            ut.check_user_provided_filename('; echo "haxorz"; # ')

    def test_exception_on_filename_starts_with_dot(self):
        with self.assertRaises(ValueError):
            ut.check_user_provided_filename('.spameggs')


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

MockCourse = collections.namedtuple('MockCourse', ['name'])
MockSemester = collections.namedtuple('MockSemester', ['name', 'course'])
MockProject = collections.namedtuple('MockProject', ['name', 'semester'])


class FileSystemUtilTestCase(TestCase):
    def setUp(self):
        self.COURSE_NAME = 'eecs280'
        self.SEMESTER_NAME = 'fall2015'
        self.PROJECT_NAME = 'p1'
        self.course = MockCourse(name='eecs280')
        self.semester = MockSemester(name='fall2015', course=self.course)
        self.project = MockProject(name='p1', semester=self.semester)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def test_get_course_root_dir(self):
        expected_relative = "{0}/{1}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME, self.COURSE_NAME)

        actual_relative = ut.get_course_relative_root_dir(self.course)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = settings.MEDIA_ROOT + expected_relative

        actual_absolute = ut.get_course_root_dir(self.course)
        self.assertEqual(expected_absolute, actual_absolute)

    # -------------------------------------------------------------------------

    def test_get_semester_root_dir(self):
        expected_relative = "{0}/{1}/{2}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME, self.COURSE_NAME,
            self.SEMESTER_NAME)

        actual_relative = ut.get_semester_relative_root_dir(self.semester)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = settings.MEDIA_ROOT + expected_relative

        actual_absolute = ut.get_semester_root_dir(self.semester)
        self.assertEqual(expected_absolute, actual_absolute)

    # -------------------------------------------------------------------------

    def test_get_project_root_dir(self):
        expected_relative = "{0}/{1}/{2}/{3}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME, self.COURSE_NAME,
            self.SEMESTER_NAME, self.PROJECT_NAME)

        actual_relative = ut.get_project_relative_root_dir(self.project)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = settings.MEDIA_ROOT + expected_relative

        actual_absolute = ut.get_project_root_dir(self.project)
        self.assertEqual(expected_absolute, actual_absolute)

    # -------------------------------------------------------------------------

    def test_get_project_files_dir(self):
        expected_relative = "{0}/{1}/{2}/{3}/{4}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME, self.COURSE_NAME,
            self.SEMESTER_NAME, self.PROJECT_NAME, gc.PROJECT_FILES_DIRNAME)

        actual_relative = ut.get_project_files_relative_dir(self.project)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = settings.MEDIA_ROOT + "{0}/{1}/{2}/{3}/{4}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME, self.COURSE_NAME,
            self.SEMESTER_NAME, self.PROJECT_NAME, gc.PROJECT_FILES_DIRNAME)

        actual_absolute = ut.get_project_files_dir(self.project)
        self.assertEqual(expected_absolute, actual_absolute)

    # -------------------------------------------------------------------------

    def test_get_project_submissions_by_student_dir(self):
        expected_relative = "{0}/{1}/{2}/{3}/{4}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME, self.COURSE_NAME,
            self.SEMESTER_NAME, self.PROJECT_NAME,
            gc.PROJECT_SUBMISSIONS_DIRNAME)
        actual_relative = ut.get_project_submissions_by_student_relative_dir(
            self.project)
        self.assertEqual(expected_relative, actual_relative)

        expected_absolute = settings.MEDIA_ROOT + "{0}/{1}/{2}/{3}/{4}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME, self.COURSE_NAME,
            self.SEMESTER_NAME, self.PROJECT_NAME,
            gc.PROJECT_SUBMISSIONS_DIRNAME)
        actual_absolute = ut.get_project_submissions_by_student_dir(
            self.project)
        self.assertEqual(expected_absolute, actual_absolute)
