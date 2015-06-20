from django.test import TestCase
from django.conf import settings

from autograder.models import Project, Course, Semester

import autograder.shared.utilities as ut
import autograder.shared.global_constants as gc


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
