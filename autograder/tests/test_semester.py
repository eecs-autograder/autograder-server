import django
from django.test import TestCase
from autograder.models import Semester, Course
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError


class SemesterTestCase(TestCase):
    def setUp(self):
        self.course = Course.objects.create(name="eecs280")
        self.SEMESTER_NAME = "fall2015"

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def test_valid_initialization(self):
        original_semester = Semester.objects.create(
            name=self.SEMESTER_NAME, course=self.course)

        loaded_semester = Semester.get_by_composite_key(
            self.SEMESTER_NAME, self.course)
        self.assertEqual(loaded_semester.name, self.SEMESTER_NAME)
        self.assertEqual(original_semester, loaded_semester)

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
        sem1 = Semester.objects.create(name=self.SEMESTER_NAME, course=self.course)
        print("\n" + sem1.pk)
        with self.assertRaises(IntegrityError):
            sem2 = Semester.objects.create(
                name=self.SEMESTER_NAME, course=self.course)
            print(sem2.pk)

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
