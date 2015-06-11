from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from autograder.models import Project, Semester, Course


class ProjectTestCase(TestCase):
    def setUp(self):
        self.course = Course.objects.create(name='eecs280')
        self.semester = Semester.objects.create(name='f15', course=self.course)
        self.PROJECT_NAME = 'stats_project'

    # -------------------------------------------------------------------------

    def test_valid_create(self):
        new_project = Project.objects.create(
            name=self.PROJECT_NAME, semester=self.semester)

        loaded_project = Project.get_by_composite_key(
            self.PROJECT_NAME, self.semester)

        self.assertEqual(loaded_project, new_project)
        self.assertEqual(loaded_project.name, new_project.name)
        self.assertEqual(loaded_project.semester, new_project.semester)

    # -------------------------------------------------------------------------

    def test_exception_on_empty_name(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(name='', semester=self.semester)

    # -------------------------------------------------------------------------

    def test_exception_on_null_name(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(name=None, semester=self.semester)

    # -------------------------------------------------------------------------

    def test_exception_on_non_unique_name(self):
        Project.objects.create(name=self.PROJECT_NAME, semester=self.semester)
        with self.assertRaises(IntegrityError):
            Project.objects.create(
                name=self.PROJECT_NAME, semester=self.semester)

    # -------------------------------------------------------------------------

    def test_no_exception_same_name_different_semester(self):
        new_semester_name = 'w16'
        new_semester = Semester.objects.create(
            name=new_semester_name, course=self.course)

        Project.objects.create(name=self.PROJECT_NAME, semester=self.semester)
        new_project = Project.objects.create(
            name=self.PROJECT_NAME, semester=new_semester)

        loaded_new_project = Project.get_by_composite_key(
            self.PROJECT_NAME, new_semester)

        self.assertEqual(loaded_new_project, new_project)
        self.assertEqual(loaded_new_project.name, new_project.name)
        self.assertEqual(loaded_new_project.semester, new_project.semester)
