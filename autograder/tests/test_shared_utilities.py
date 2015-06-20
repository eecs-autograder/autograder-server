from django.test import TestCase
from django.conf import settings

from autograder.models import Project, Course, Semester

from autograder.shared import utilities as ut


class FileSystemUtilTestCase(TestCase):
    def setUp(self):
        self.course = Course(name='eecs280')
        self.semester = Semester(name='fall2015', course=self.course)
        self.project = Project(name='p1', semester=self.semester)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def test_get_course_root_dir(self):
        expected = settings.MEDIA_ROOT + "courses/eecs280"
        actual = ut.get_course_root_dir(self.course)
        self.assertEqual(expected, actual)

    # -------------------------------------------------------------------------

    def test_get_semester_root_dir(self):
        expected = settings.MEDIA_ROOT + "courses/eecs280/fall2015"
        actual = ut.get_semester_root_dir(self.semester)
        self.assertEqual(expected, actual)

    # -------------------------------------------------------------------------

    def test_get_project_root_dir(self):
        expected = settings.MEDIA_ROOT + "courses/eecs280/fall2015/p1"
        actual = ut.get_project_root_dir(self.project)
        self.assertEqual(expected, actual)

    # -------------------------------------------------------------------------

    def test_get_project_files_dir(self):
        expected = (
            settings.MEDIA_ROOT + "courses/eecs280/fall2015/p1/project_files")

        actual = ut.get_project_files_dir(self.project)
        self.assertEqual(expected, actual)
