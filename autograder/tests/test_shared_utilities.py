from django.test import TestCase
from django.conf import settings

from autograder.models import Project, Course

from autograder.shared import utilities as ut


class FileSystemUtilTestCase(TestCase):
    def setUp(self):
        self.course = Course.objects.create(name='eecs280')
        # self.project = Project.objects.create(name='p1', course=self.course)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def test_get_course_root_dir(self):
        expected = settings.MEDIA_ROOT + "courses/eecs280"
        actual = ut.get_course_root_dir(self.course)
        self.assertEqual(expected, actual)

    # -------------------------------------------------------------------------

    # def test_get_project_root_dir(self):
    #     expected = settings.MEDIA_ROOT + "courses/eecs280/projects/p1"
    #     actual = ut.get_project_root_dir(self.project)
    #     self.assertEqual(expected, actual)

    # # -------------------------------------------------------------------------

    # def test_get_project_files_dir(self):
    #     expected = (
    #         settings.MEDIA_ROOT + "courses/eecs280/projects/p1/project_files")

    #     actual = ut.get_project_files_dir(self.project)
    #     self.assertEqual(expected, actual)

