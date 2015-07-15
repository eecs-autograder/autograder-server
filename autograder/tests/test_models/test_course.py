import os

from django.core.exceptions import ValidationError

from autograder.models import Course

import autograder.shared.utilities as ut

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)


class CourseTestCase(TemporaryFilesystemTestCase):
    def test_valid_save(self):
        name = "eecs280"
        Course.objects.validate_and_create(name=name)

        loaded = Course.objects.get(pk=name)

        self.assertEqual(name, loaded.name)

    def test_strip_name_whitespace(self):
        name = '   eecs280       '
        Course.objects.validate_and_create(name=name)

        stripped_name = 'eecs280'
        loaded = Course.objects.get(pk=stripped_name)
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
