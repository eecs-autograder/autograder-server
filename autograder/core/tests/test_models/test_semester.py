import os

from django.core.exceptions import ValidationError

from autograder.core.models import Semester, Course

import autograder.core.shared.utilities as ut

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.core.tests.dummy_object_utils as obj_ut


class SemesterTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.course = Course.objects.validate_and_create(name="eecs280")
        self.SEMESTER_NAME = "fall2015"

    def test_valid_initialization(self):
        new_semester = Semester.objects.validate_and_create(
            name=self.SEMESTER_NAME, course=self.course)

        loaded_semester = Semester.objects.get(
            name=self.SEMESTER_NAME, course=self.course)
        self.assertEqual(loaded_semester.name, self.SEMESTER_NAME)
        self.assertEqual(loaded_semester.course, self.course)
        self.assertEqual(new_semester, loaded_semester)

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
        new_course = Course.objects.validate_and_create(name=new_course_name)

        Semester.objects.validate_and_create(
            name=self.SEMESTER_NAME, course=self.course)

        new_semester = Semester.objects.validate_and_create(
            name=self.SEMESTER_NAME, course=new_course)

        loaded_new_semester = Semester.objects.get(
            name=self.SEMESTER_NAME, course=new_course)

        self.assertEqual(loaded_new_semester, new_semester)

    def test_to_dict_default_fields(self):
        expected_fields = [
            'name',
            'course'
        ]

        self.assertCountEqual(expected_fields,
                              Semester.get_default_to_dict_fields())

        semester = obj_ut.build_semester()
        self.assertTrue(semester.to_dict())


class SemesterStaffAndEnrolledStudentTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)
        self.user = obj_ut.create_dummy_user()

    def test_is_semester_staff(self):
        self.assertFalse(self.semester.is_semester_staff(self.user))

        self.semester.staff.add(self.user)
        self.assertTrue(self.semester.is_semester_staff(self.user))

    def test_is_enrolled_student(self):
        self.assertFalse(self.semester.is_enrolled_student(self.user))

        self.semester.enrolled_students.add(self.user)
        self.assertTrue(self.semester.is_enrolled_student(self.user))

    def test_get_staff_semesters_for_user(self):
        # Staff only
        expected_semesters = [
            obj_ut.build_semester(semester_kwargs={'staff': [self.user]})
            for i in range(4)
        ]
        # Staff and admin
        expected_semesters.append(obj_ut.build_semester(
            course_kwargs={'administrators': [self.user]},
            semester_kwargs={'staff': [self.user]}))
        # Admin only
        expected_semesters.append(obj_ut.build_semester(
            course_kwargs={'administrators': [self.user]}))
        # Nothing
        obj_ut.build_semester()

        actual_semesters = Semester.get_staff_semesters_for_user(self.user)
        self.assertCountEqual(expected_semesters, actual_semesters)

    def test_semester_staff_names_includes_administrators(self):
        self.course.administrators.add(self.user)

        self.assertTrue(self.semester.is_semester_staff(self.user))
        self.assertCountEqual(
            (self.user.username,), self.semester.semester_staff_names)


class SemesterFilesystemTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.course = Course.objects.validate_and_create(name="eecs280")
        self.SEMESTER_NAME = "fall2015"

    def test_semester_root_dir_created(self):
        semester = Semester(name=self.SEMESTER_NAME, course=self.course)

        self.assertEqual(
            [],
            os.listdir(os.path.dirname(ut.get_semester_root_dir(semester))))

        semester.save()

        expected_semester_root_dir = ut.get_semester_root_dir(semester)
        self.assertTrue(os.path.isdir(expected_semester_root_dir))
