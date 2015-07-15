import os

from django.core.exceptions import ValidationError

from autograder.models import Semester, Course

import autograder.shared.utilities as ut

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)


class SemesterTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.course = Course.objects.validate_and_create(name="eecs280")
        self.SEMESTER_NAME = "fall2015"

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def test_valid_initialization(self):
        new_semester = Semester.objects.validate_and_create(
            name=self.SEMESTER_NAME, course=self.course)

        loaded_semester = Semester.objects.get(
            name=self.SEMESTER_NAME, course=self.course)
        self.assertEqual(loaded_semester.name, self.SEMESTER_NAME)
        self.assertEqual(loaded_semester.course, self.course)
        self.assertEqual(new_semester, loaded_semester)

    def test_name_whitespace_stripped(self):
        Semester.objects.validate_and_create(
            name='    ' + self.SEMESTER_NAME + '   ',
            course=self.course)

        loaded_semester = Semester.objects.get(
            name=self.SEMESTER_NAME, course=self.course)
        self.assertEqual(loaded_semester.name, self.SEMESTER_NAME)

    def test_exception_on_name_is_only_whitespace(self):
        with self.assertRaises(ValidationError) as cm:
            Semester.objects.validate_and_create(
                name='    ', course=self.course)
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_empty_name(self):
        with self.assertRaises(ValidationError) as cm:
            Semester.objects.validate_and_create(name='', course=self.course)
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_null_name(self):
        with self.assertRaises(ValidationError) as cm:
            Semester.objects.validate_and_create(name=None, course=self.course)
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_non_unique_name(self):
        Semester.objects.validate_and_create(
            name=self.SEMESTER_NAME, course=self.course)

        with self.assertRaises(ValidationError):
            Semester.objects.validate_and_create(
                name=self.SEMESTER_NAME, course=self.course)

    def test_no_exception_same_name_different_course(self):
        new_course_name = "eecs381"
        new_course = Course(name=new_course_name)
        new_course.validate_and_save()

        Semester.objects.validate_and_create(
            name=self.SEMESTER_NAME, course=self.course)

        new_semester = Semester.objects.validate_and_create(
            name=self.SEMESTER_NAME, course=new_course)

        loaded_new_semester = Semester.objects.get(
            name=self.SEMESTER_NAME, course=new_course)

        self.assertEqual(loaded_new_semester, new_semester)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class SemesterFilesystemTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.course = Course.objects.create(name="eecs280")
        self.SEMESTER_NAME = "fall2015"

    # -------------------------------------------------------------------------

    def test_semester_root_dir_created_and_removed(self):
        semester = Semester(name=self.SEMESTER_NAME, course=self.course)
        expected_semester_root_dir = ut.get_semester_root_dir(semester)

        self.assertFalse(os.path.exists(expected_semester_root_dir))

        semester.validate_and_save()

        self.assertTrue(os.path.isdir(expected_semester_root_dir))

        semester.delete()
        self.assertFalse(os.path.exists(expected_semester_root_dir))
