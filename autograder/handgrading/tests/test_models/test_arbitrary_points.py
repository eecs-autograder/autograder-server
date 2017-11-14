"""Arbitrary Points tests"""

import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase
from django.core.exceptions import ValidationError


class ArbitraryPointsTestCase(UnitTestBase):
    def setUp(self):
        self.default_arb_points_inputs = {
            "location": {
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            "text": "",
            "points": 0,
            "handgrading_result": handgrading_models.HandgradingResult.objects.validate_and_create(
                submission=obj_build.build_submission(submitted_filenames=["test.cpp"])
            )
        }

    def test_default_initialization(self):
        arb_points_obj = handgrading_models.ArbitraryPoints.objects.validate_and_create(
            **self.default_arb_points_inputs
        )

        self.assertEqual(arb_points_obj.points, 0)

    def test_create_average_case(self):
        arb_points_inputs = {
            "location": {
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            "text": "Testing text field. This can be longer.",
            "points": 24,
            "handgrading_result": handgrading_models.HandgradingResult.objects.validate_and_create(
                submission=obj_build.build_submission(submitted_filenames=["test.cpp"])
            )
        }

        arb_points_obj = handgrading_models.ArbitraryPoints.objects.validate_and_create(
            **arb_points_inputs)

        self.assertEqual(arb_points_obj.text, arb_points_inputs["text"])
        self.assertEqual(arb_points_obj.points, arb_points_inputs["points"])
        self.assertEqual(arb_points_obj.handgrading_result,
                         arb_points_inputs["handgrading_result"])

        self.assertEqual(arb_points_obj.location.first_line,
                         arb_points_inputs["location"]["first_line"])
        self.assertEqual(arb_points_obj.location.last_line,
                         arb_points_inputs["location"]["last_line"])
        self.assertEqual(arb_points_obj.location.filename,
                         arb_points_inputs["location"]["filename"])

    def test_filename_in_location_must_be_in_submitted_files(self):
        """Submission in handgrading_result contains filename "test.cpp" (see defaults),
             but location's filename is set to "WRONG.cpp" """

        handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=obj_build.build_submission(submitted_filenames=["test.cpp"])
        )

        with self.assertRaises(ValidationError):
            handgrading_models.ArbitraryPoints.objects.validate_and_create(
                location={
                    "first_line": 0,
                    "last_line": 1,
                    "filename": "WRONG.cpp"
                },
                text="",
                points=0,
                handgrading_result=handgrading_result
            )

    def test_serializable_fields(self):
        expected_fields = [
            'pk',
            'last_modified',

            'location',
            'text',
            'points',
            'handgrading_result',
        ]

        arb_points_obj = handgrading_models.ArbitraryPoints.objects.validate_and_create(
            **self.default_arb_points_inputs
        )

        arb_points_dict = arb_points_obj.to_dict()

        self.assertCountEqual(expected_fields, arb_points_dict.keys())
        self.assertIsInstance(arb_points_dict['location'], dict)

        for non_editable in ['pk', 'last_modified', 'location', 'handgrading_result']:
            arb_points_dict.pop(non_editable)

        arb_points_obj.validate_and_update(**arb_points_dict)
