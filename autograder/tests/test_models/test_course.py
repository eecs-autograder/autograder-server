import os

from django.core.exceptions import ValidationError

from autograder.models import Course

import autograder.shared.utilities as ut

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.tests.dummy_object_utils as obj_ut


class CourseTestCase(TemporaryFilesystemTestCase):
    def test_valid_save(self):
        name = "eecs280"
        Course.objects.validate_and_create(name=name)

        loaded = Course.objects.get(name=name)

        self.assertEqual(name, loaded.name)

    def test_strip_name_whitespace(self):
        name = '   eecs280       '
        Course.objects.validate_and_create(name=name)

        stripped_name = 'eecs280'
        loaded = Course.objects.get(name=stripped_name)
        self.assertEqual(stripped_name, loaded.name)

    def test_exception_on_name_is_only_whitespace(self):
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name='     ')
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_empty_name(self):
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name='')
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_null_name(self):
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name=None)
        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_non_unique_name(self):
        NAME = "eecs280"
        Course.objects.validate_and_create(name=NAME)
        with self.assertRaises(ValidationError) as cm:
            Course.objects.validate_and_create(name=NAME)
        self.assertTrue('name' in cm.exception.message_dict)


# -----------------------------------------------------------------------------

class CourseAdminUserTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = obj_ut.create_dummy_courses()
        self.user = obj_ut.create_dummy_users()

    def test_valid_add_course_admins(self):
        self.course.add_course_admins(self.user)

        loaded = Course.objects.get(name=self.course.name)
        self.assertTrue(loaded.is_course_admin(self.user))

    def test_add_course_admins_merge_duplicates(self):
        self.course.add_course_admins(self.user)

        user2 = obj_ut.create_dummy_users()
        self.course.add_course_admins(self.user, user2)

        loaded = Course.objects.get(name=self.course.name)
        self.assertEqual(
            (self.user.username, user2.username), loaded.course_admin_names)

    def test_valid_remove_course_admin(self):
        self.course.add_course_admins(self.user)
        self.assertTrue(self.course.is_course_admin(self.user))

        self.course.remove_course_admin(self.user)

        loaded = Course.objects.get(name=self.course.name)
        self.assertFalse(loaded.is_course_admin(self.user))

    def test_exception_on_remove_non_course_admin_user(self):
        with self.assertRaises(ValidationError):
            self.course.remove_course_admin(self.user)

    def test_is_course_admin(self):
        self.assertFalse(self.course.is_course_admin(self.user))
        self.assertFalse(self.course.is_course_admin(self.user.username))

        self.course.add_course_admins(self.user)

        self.assertTrue(self.course.is_course_admin(self.user))
        self.assertTrue(self.course.is_course_admin(self.user.username))

    def test_get_courses_for_user(self):
        self.course.delete()
        courses = obj_ut.create_dummy_courses(10)
        subset = [courses[2], courses[5], courses[7]]
        for course in subset:
            course.add_course_admins(self.user)

        courses_queryset = Course.get_courses_for_user(self.user)
        self.assertCountEqual(courses_queryset, subset)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class CourseFilesystemTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.COURSE_NAME = 'eecs280'

    # -------------------------------------------------------------------------

    def test_course_root_dir_created_and_removed(self):
        course = Course(name=self.COURSE_NAME)
        expected_course_root_dir = ut.get_course_root_dir(course)

        self.assertFalse(os.path.exists(expected_course_root_dir))

        course.validate_and_save()

        self.assertTrue(os.path.isdir(expected_course_root_dir))

        course.delete()
        self.assertFalse(os.path.exists(expected_course_root_dir))
