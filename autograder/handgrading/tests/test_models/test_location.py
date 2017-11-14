"""Location tests"""

import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase
from django.core.exceptions import ValidationError


class LocationTestCase(UnitTestBase):
    def test_default_initialization(self):
        location_obj = handgrading_models.Location.objects.validate_and_create(
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
            handgrading_models.Location.objects.validate_and_create(**location_inputs)

    def test_serialization(self):
        expected_fields = [
            'pk',
            'last_modified',

            'first_line',
            'last_line',
            'filename',
        ]

        location_obj = handgrading_models.Location.objects.validate_and_create(
            first_line=0,
            last_line=0,
            filename="stats.cpp"
        )

        location_dict = location_obj.to_dict()

        self.assertCountEqual(expected_fields, location_dict.keys())

        for non_editable in ['pk', 'last_modified', 'filename']:
            location_dict.pop(non_editable)

        location_obj.validate_and_update(**location_dict)
