import os

from django.core.exceptions import ValidationError

from autograder.models import Semester, Course

import autograder.shared.utilities as ut

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.tests.dummy_object_utils as obj_ut


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

class SemesterStaffAndEnrolledStudentTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)
        self.user = obj_ut.create_dummy_users()

    def test_valid_add_semester_staff(self):
        self.semester.add_semester_staff(self.user)

        loaded = Semester.objects.get(pk=self.semester.pk)
        self.assertTrue(loaded.is_semester_staff(self.user))

    def test_exception_on_user_already_staff(self):
        self.semester.add_semester_staff(self.user)
        with self.assertRaises(ValidationError):
            self.semester.add_semester_staff(self.user)

    def test_valid_remove_semester_staff(self):
        self.semester.add_semester_staff(self.user)
        self.assertTrue(self.semester.is_semester_staff(self.user))

        self.semester.remove_semester_staff(self.user)
        loaded = Semester.objects.get(pk=self.semester.pk)
        self.assertFalse(loaded.is_semester_staff(self.user))

    def test_exception_remove_user_not_semester_staff(self):
        with self.assertRaises(ValidationError):
            self.semester.remove_semester_staff(self.user)

    def test_is_semester_staff(self):
        self.assertFalse(self.semester.is_semester_staff(self.user))
        self.semester.add_semester_staff(self.user)
        self.assertTrue(self.semester.is_semester_staff(self.user))

    def test_valid_add_enrolled_student(self):
        self.semester.add_enrolled_student(self.user)

        loaded = Semester.objects.get(pk=self.semester.pk)
        self.assertTrue(loaded.is_enrolled_student(self.user))

    def test_exception_on_user_already_enrolled_student(self):
        self.semester.add_enrolled_student(self.user)
        with self.assertRaises(ValidationError):
            self.semester.add_enrolled_student(self.user)

    def test_valid_remove_enrolled_student(self):
        self.semester.add_enrolled_student(self.user)
        self.assertTrue(self.semester.is_enrolled_student(self.user))

        self.semester.remove_enrolled_student(self.user)

        loaded = Semester.objects.get(pk=self.semester.pk)
        self.assertFalse(loaded.is_enrolled_student(self.user))

    def test_exception_on_remove_user_not_enrolled_student(self):
        with self.assertRaises(ValidationError):
            self.semester.remove_enrolled_student(self.user)

    def test_is_enrolled_student(self):
        self.assertFalse(self.semester.is_enrolled_student(self.user))
        self.semester.add_enrolled_student(self.user)
        self.assertTrue(self.semester.is_enrolled_student(self.user))

    def test_get_staff_semesters_for_user(self):
        self.semester.delete()
        semesters = obj_ut.create_dummy_semesters(self.course, 10)
        subset = [semesters[1], semesters[6]]
        for semester in subset:
            semester.add_semester_staff(self.user)

        semesters_queryset = Semester.get_staff_semesters_for_user(self.user)
        self.assertEqual(
            list(semesters_queryset),
            sorted(subset, key=lambda semester: semester.name))

    def test_get_enrolled_semesters_for_user(self):
        self.semester.delete()
        semesters = obj_ut.create_dummy_semesters(self.course, 10)
        subset = [semesters[3], semesters[8]]
        for semester in subset:
            semester.add_enrolled_student(self.user)

        semesters_queryset = Semester.get_enrolled_semesters_for_user(
            self.user)
        self.assertEqual(
            list(semesters_queryset),
            sorted(subset, key=lambda semester: semester.name))


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
