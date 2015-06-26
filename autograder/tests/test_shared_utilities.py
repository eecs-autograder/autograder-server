import re

from django.test import TestCase
from django.conf import settings

from autograder.models import Project, Course, Semester

import autograder.shared.utilities as ut
import autograder.shared.global_constants as gc


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

class FileSystemUtilTestCase(TestCase):
    def setUp(self):
        self.COURSE_NAME = 'eecs280'
        self.SEMESTER_NAME = 'fall2015'
        self.PROJECT_NAME = 'p1'
        self.course = Course(name='eecs280')
        self.semester = Semester(name='fall2015', course=self.course)
        self.project = Project(name='p1', semester=self.semester)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def test_get_course_root_dir(self):
        expected = settings.MEDIA_ROOT + "{0}/{1}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME, self.COURSE_NAME)
        actual = ut.get_course_root_dir(self.course)
        self.assertEqual(expected, actual)

    # -------------------------------------------------------------------------

    def test_get_semester_root_dir(self):
        expected = settings.MEDIA_ROOT + "{0}/{1}/{2}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME, self.COURSE_NAME,
            self.SEMESTER_NAME)
        actual = ut.get_semester_root_dir(self.semester)
        self.assertEqual(expected, actual)

    # -------------------------------------------------------------------------

    def test_get_project_root_dir(self):
        expected = settings.MEDIA_ROOT + "{0}/{1}/{2}/{3}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME, self.COURSE_NAME,
            self.SEMESTER_NAME, self.PROJECT_NAME)
        actual = ut.get_project_root_dir(self.project)
        self.assertEqual(expected, actual)

    # -------------------------------------------------------------------------

    def test_get_project_files_dir(self):
        expected = settings.MEDIA_ROOT + "{0}/{1}/{2}/{3}/{4}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME, self.COURSE_NAME,
            self.SEMESTER_NAME, self.PROJECT_NAME, gc.PROJECT_FILES_DIRNAME)
        actual = ut.get_project_files_dir(self.project)
        self.assertEqual(expected, actual)

    # -------------------------------------------------------------------------

    def test_get_project_submissions_by_student_dir(self):
        expected = settings.MEDIA_ROOT + "{0}/{1}/{2}/{3}/{4}".format(
            gc.FILESYSTEM_ROOT_COURSES_DIRNAME, self.COURSE_NAME,
            self.SEMESTER_NAME, self.PROJECT_NAME,
            gc.PROJECT_SUBMISSIONS_DIRNAME)
        actual = ut.get_project_submissions_by_student_dir(self.project)
        self.assertEqual(expected, actual)
