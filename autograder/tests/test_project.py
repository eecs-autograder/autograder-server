from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from autograder.models import Course, Project


class ProjectTestCase(TestCase):
    def setUp(self):
        self.course = Course.objects.create(name='eecs280')
        self.PROJECT_NAME = 'stats_project'

    # -------------------------------------------------------------------------

    def test_valid_create(self):
        new_project = Project.objects.create(
            name=self.PROJECT_NAME, course=self.course)

        loaded_project = Project.get_by_composite_key(
            self.PROJECT_NAME, self.course)

        self.assertEqual(loaded_project, new_project)
        self.assertEqual(loaded_project.name, new_project.name)
        self.assertEqual(loaded_project.course, new_project.course)

    # -------------------------------------------------------------------------

    def test_exception_on_empty_name(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(name='', course=self.course)

    # -------------------------------------------------------------------------

    def test_exception_on_null_name(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(name=None, course=self.course)

    # -------------------------------------------------------------------------

    def test_exception_on_non_unique_name(self):
        Project.objects.create(name=self.PROJECT_NAME, course=self.course)
        with self.assertRaises(IntegrityError):
            Project.objects.create(name=self.PROJECT_NAME, course=self.course)

    # -------------------------------------------------------------------------

    def test_no_exception_same_name_different_course(self):
        new_course_name = 'eecs381'
        new_course = Course.objects.create(name=new_course_name)

        Project.objects.create(name=self.PROJECT_NAME, course=self.course)
        new_project = Project.objects.create(
            name=self.PROJECT_NAME, course=new_course)

        loaded_new_project = Project.get_by_composite_key(
            self.PROJECT_NAME, new_course)

        self.assertEqual(loaded_new_project, new_project)
        self.assertEqual(loaded_new_project.name, new_project.name)
        self.assertEqual(loaded_new_project.course, new_project.course)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class ExpectedStudentFilenameOrFilepattern(TestCase):
    pass
