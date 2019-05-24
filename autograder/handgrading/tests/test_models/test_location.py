"""Location tests"""
from django.test import TestCase

import autograder.handgrading.models as hg_models
from autograder.utils.testing import UnitTestBase
from django.core.exceptions import ValidationError


class LocationTestCase(UnitTestBase):
    def test_default_initialization(self):
        location_obj = hg_models.Location.objects.validate_and_create(
            first_line=0,
            last_line=0,
            filename="stats.cpp"
        )

        self.assertEqual(location_obj.first_line, 0)
        self.assertEqual(location_obj.last_line, 0)
        self.assertEqual(location_obj.filename, "stats.cpp")

    def test_last_line_less_than_first_line(self):
        location_inputs = {
            "first_line": 21,
            "last_line": 20
        }

        with self.assertRaises(ValidationError):
            hg_models.Location.objects.validate_and_create(**location_inputs)

    def test_serialization(self):
        expected_fields = [
            'pk',
            'last_modified',

            'first_line',
            'last_line',
            'filename',
        ]

        location_obj = hg_models.Location.objects.validate_and_create(
            first_line=0,
            last_line=0,
            filename="stats.cpp"
        )

        location_dict = location_obj.to_dict()

        self.assertCountEqual(expected_fields, location_dict.keys())

        for non_editable in ['pk', 'last_modified', 'filename']:
            location_dict.pop(non_editable)

        location_obj.validate_and_update(**location_dict)


class NewLocationTestCase(TestCase):
    def test_default_initialization(self):
        location_obj = hg_models.NewLocation.from_dict({
            'first_line': 0,
            'last_line': 0,
            'filename': "stats.cpp"
        })

        self.assertEqual(location_obj.first_line, 0)
        self.assertEqual(location_obj.last_line, 0)
        self.assertEqual(location_obj.filename, "stats.cpp")

    def test_error_last_or_first_line_negative(self):
        with self.assertRaises(ValidationError) as cm:
            hg_models.NewLocation.from_dict({
                'first_line': -1,
                'last_line': 0,
                'filename': "stats.cpp"
            })

        self.assertIn('first_line', cm.exception.message)

        with self.assertRaises(ValidationError) as cm:
            hg_models.NewLocation.from_dict({
                'first_line': 0,
                'last_line': -1,
                'filename': "stats.cpp"
            })

        self.assertIn('last_line', cm.exception.message)
        self.assertNotIn('first_line', cm.exception.message)

    def test_error_filename_empty(self):
        with self.assertRaises(ValidationError) as cm:
            hg_models.NewLocation.from_dict({
                'first_line': 0,
                'last_line': 0,
                'filename': ""
            })

        self.assertIn('filename', cm.exception.message)

    def test_last_line_less_than_first_line(self):
        location_inputs = {
            "filename": "spam.cpp",
            "first_line": 21,
            "last_line": 20
        }

        with self.assertRaises(ValidationError) as cm:
            hg_models.NewLocation.from_dict(location_inputs)

        self.assertIn('first_line', cm.exception.message)
        self.assertIn('last_line', cm.exception.message)

    def test_serialization(self):
        data = {
            'first_line': 0,
            'last_line': 0,
            'filename': "stats.cpp"
        }

        location_obj = hg_models.NewLocation.from_dict(data)

        location_dict = location_obj.to_dict()
        self.assertEqual(data, location_dict)
