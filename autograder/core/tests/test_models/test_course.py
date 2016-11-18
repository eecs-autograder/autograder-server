import os

from django.core.exceptions import ValidationError

from autograder.core.models import Course

import autograder.core.utils as core_ut
from autograder.utils.testing import UnitTestBase

import autograder.utils.testing.model_obj_builders as obj_build


class CourseTestCase(UnitTestBase):
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
        course = obj_build.build_course()
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name=course.name)
        self.assertTrue('name' in cm.exception.message_dict)

    def test_serializable_fields(self):
        expected_fields = [
            'pk',
            'name'
        ]

        self.assertCountEqual(expected_fields,
                              Course.get_serializable_fields())

        course = obj_build.build_course()
        self.assertTrue(course.to_dict())

    def test_editable_fields(self):
        expected = ['name']
        self.assertCountEqual(expected, Course.get_editable_fields())


class CourseFilesystemTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.COURSE_NAME = 'eecs280'

    def test_course_root_dir_created(self):
        course = Course(name=self.COURSE_NAME)

        self.assertFalse(
            os.path.exists(os.path.dirname(core_ut.get_course_root_dir(course))))

        course.save()
        expected_course_root_dir = core_ut.get_course_root_dir(course)

        self.assertTrue(os.path.isdir(expected_course_root_dir))


class CourseAdminStaffAndEnrolledStudentTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.course = obj_build.build_course()
        self.user = obj_build.create_dummy_user()

    def test_is_administrator(self):
        self.course = obj_build.build_course()
        self.user = obj_build.create_dummy_user()

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
