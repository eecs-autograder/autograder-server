import os

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from autograder.models import Course

import autograder.shared.utilities as ut

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)


class CourseTestCase(TemporaryFilesystemTestCase):
    def test_valid_save(self):
        NAME = "eecs280"
        Course.objects.create(name=NAME)

        loaded = Course.objects.get(pk=NAME)

        self.assertEqual(NAME, loaded.name)

    # -------------------------------------------------------------------------

    def test_exception_on_empty_name(self):
        with self.assertRaises(ValidationError):
            Course.objects.create(name='')

    # -------------------------------------------------------------------------

    def test_exception_on_null_name(self):
        with self.assertRaises(ValidationError):
            Course.objects.create(name=None)

    # -------------------------------------------------------------------------

    def test_exception_on_non_unique_name(self):
        NAME = "eecs280"
        Course.objects.create(name=NAME)
        with self.assertRaises(IntegrityError):
            Course.objects.create(name=NAME)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class CourseFilesystemTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.COURSE_NAME = 'eecs280'

    # -------------------------------------------------------------------------

    def test_course_root_dir_created(self):
        course = Course(name=self.COURSE_NAME)
        expected_course_root_dir = ut.get_course_root_dir(course)

        self.assertFalse(os.path.exists(expected_course_root_dir))

        course.save()

        self.assertTrue(os.path.isdir(expected_course_root_dir))
