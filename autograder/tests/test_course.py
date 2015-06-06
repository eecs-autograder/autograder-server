from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from autograder.models import Course


class CourseTestCase(TestCase):
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
