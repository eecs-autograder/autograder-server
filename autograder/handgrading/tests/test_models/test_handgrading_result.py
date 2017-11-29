"""Handgrading Result tests"""

import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase
from django.core.exceptions import ValidationError


class HandgradingResultTestCases(UnitTestBase):
    """
    Test cases relating the Handgrading Result Model
    """
    def setUp(self):
        self.default_handgrading_rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
                max_points=0,
                show_grades_and_rubric_to_students=False,
                handgraders_can_leave_comments=True,
                handgraders_can_apply_arbitrary_points=True,
                project=obj_build.build_project()
            )
        )

    def test_default_initialization(self):
        result_inputs = {
            "submission": obj_build.build_submission(),
            "handgrading_rubric": self.default_handgrading_rubric
        }

        result_obj = handgrading_models.HandgradingResult.objects.validate_and_create(
            **result_inputs)
        self.assertEqual(result_obj.submission, result_inputs["submission"])
        self.assertEqual(result_obj.handgrading_rubric, result_inputs["handgrading_rubric"])

    def test_serializable_fields(self):
        expected_fields = [
            'pk',
            'last_modified',
            'submission',
            'handgrading_rubric'
        ]

        result_inputs = {
            "submission": obj_build.build_submission(),
            "handgrading_rubric": self.default_handgrading_rubric
        }

        result_obj = handgrading_models.HandgradingResult.objects.validate_and_create(
            **result_inputs
        )

        result_dict = result_obj.to_dict()
        self.assertCountEqual(expected_fields, result_dict.keys())

        with self.assertRaises(ValidationError):
            result_obj.validate_and_update(**result_dict)
