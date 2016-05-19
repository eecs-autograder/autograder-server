import os

from django.core.exceptions import ValidationError

from autograder.core.models import Course

import autograder.core.shared.utilities as ut

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.core.tests.dummy_object_utils as obj_ut


class CourseTestCase(TemporaryFilesystemTestCase):
    def test_valid_create(self):
        name = "eecs280"
        course = Course.objects.validate_and_create(name=name)

        course.refresh_from_db()

        self.assertEqual(name, course.name)

    def test_exception_on_empty_name(self):
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name='')
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_null_name(self):
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name=None)
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_non_unique_name(self):
        course = obj_ut.build_course()
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name=course.name)
        self.assertTrue('name' in cm.exception.message_dict)

    def test_to_dict_default_fields(self):
        expected_fields = [
            'name'
        ]

        self.assertCountEqual(expected_fields,
                              Course.get_default_to_dict_fields())

        course = obj_ut.build_course()
        self.assertTrue(course.to_dict())

    def test_editable_fields(self):
        expected = ['name']
        self.assertCountEqual(expected, Course.get_editable_fields())


class CourseFilesystemTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.COURSE_NAME = 'eecs280'

    def test_course_root_dir_created(self):
        course = Course(name=self.COURSE_NAME)

        self.assertFalse(
            os.path.exists(os.path.dirname(ut.get_course_root_dir(course))))

        course.save()
        expected_course_root_dir = ut.get_course_root_dir(course)

        self.assertTrue(os.path.isdir(expected_course_root_dir))


class CourseAdminStaffAndEnrolledStudentTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = obj_ut.build_course()
        self.user = obj_ut.create_dummy_user()

    def test_is_administrator(self):
        self.course = obj_ut.build_course()
        self.user = obj_ut.create_dummy_user()

        self.assertFalse(self.course.is_administrator(self.user))

        self.course.administrators.add(self.user)
        self.assertTrue(self.course.is_administrator(self.user))

    def test_is_course_staff(self):
        self.assertFalse(self.course.is_course_staff(self.user))

        self.course.staff.add(self.user)
        self.assertTrue(self.course.is_course_staff(self.user))

    def test_admin_counts_as_staff(self):
        self.assertFalse(self.course.is_course_staff(self.user))

        self.course.administrators.add(self.user)
        self.assertTrue(self.course.is_course_staff(self.user))

    def test_is_enrolled_student(self):
        self.assertFalse(self.course.is_enrolled_student(self.user))

        self.course.enrolled_students.add(self.user)
        self.assertTrue(self.course.is_enrolled_student(self.user))
