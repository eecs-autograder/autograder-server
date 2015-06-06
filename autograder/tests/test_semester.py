from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from autograder.models import Semester, Course, Project


class SemesterTestCase(TestCase):
    def setUp(self):
        self.course = Course.objects.create(name="eecs280")
        self.SEMESTER_NAME = "fall2015"

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def test_valid_initialization(self):
        new_semester = Semester.objects.create(
            name=self.SEMESTER_NAME, course=self.course)

        loaded_semester = Semester.get_by_composite_key(
            self.SEMESTER_NAME, self.course)
        self.assertEqual(loaded_semester.name, self.SEMESTER_NAME)
        self.assertEqual(loaded_semester.course, self.course)
        self.assertEqual(new_semester, loaded_semester)

    # -------------------------------------------------------------------------

    def test_exception_on_empty_name(self):
        with self.assertRaises(ValidationError):
            Semester.objects.create(name='', course=self.course)

    # -------------------------------------------------------------------------

    def test_exception_on_null_name(self):
        with self.assertRaises(ValidationError):
            Semester.objects.create(name=None, course=self.course)

    # -------------------------------------------------------------------------

    def test_exception_on_non_unique_name(self):
        Semester.objects.create(name=self.SEMESTER_NAME, course=self.course)
        with self.assertRaises(IntegrityError):
            Semester.objects.create(
                name=self.SEMESTER_NAME, course=self.course)

    # -------------------------------------------------------------------------

    def test_no_exception_same_name_different_course(self):
        new_course_name = "eecs381"
        new_course = Course.objects.create(name=new_course_name)

        Semester.objects.create(
            name=self.SEMESTER_NAME, course=self.course)
        new_semester = Semester.objects.create(
            name=self.SEMESTER_NAME, course=new_course)

        loaded_new_semester = Semester.get_by_composite_key(
            self.SEMESTER_NAME, new_course)

        self.assertEqual(loaded_new_semester, new_semester)

    # -------------------------------------------------------------------------

    def test_exception_on_null_course(self):
        with self.assertRaises(ValueError):
            Semester.objects.create(name=self.SEMESTER_NAME, course=None)

    # -------------------------------------------------------------------------

    def test_valid_semester_with_projects(self):
        project1_name = "p1"
        project2_name = "p2"
        project1 = Project.objects.create(
            name=project1_name, course=self.course)
        project2 = Project.objects.create(
            name=project2_name, course=self.course)

        semester = Semester.objects.create(
            name=self.SEMESTER_NAME, course=self.course)

        semester.projects.add(project1)
        semester.projects.add(project2)
        semester.save()

        loaded_semester = Semester.get_by_composite_key(
            self.SEMESTER_NAME, self.course)

        self.assertTrue(project1 in loaded_semester.projects.all())
        self.assertTrue(project2 in loaded_semester.projects.all())
