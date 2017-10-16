"""Criterion tests"""

import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase


class CriterionTestCase(UnitTestBase):
    """
    Test cases relating the Criterion Model
    """
    def setUp(self):
        default_rubric_inputs = {
            "points_style": handgrading_models.PointsStyle.start_at_max_and_subtract,
            "max_points": 0,
            "show_grades_and_rubric_to_students": False,
            "handgraders_can_leave_comments": True,
            "handgraders_can_apply_arbitrary_points": True,
            "project": obj_build.build_project()
        }

        self.default_handgrading_rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                **default_rubric_inputs)
        )

        self.default_criterion = {
            "short_description": "",
            "long_description": "",
            "points": 0,
            "handgrading_rubric": self.default_handgrading_rubric
        }

    def test_default_initialization(self):
        criterion_obj = handgrading_models.Criterion.objects.validate_and_create(
                                    **self.default_criterion)

        self.assertEqual(criterion_obj.short_description,
                         self.default_criterion["short_description"])
        self.assertEqual(criterion_obj.long_description,
                         self.default_criterion["long_description"])
        self.assertEqual(criterion_obj.points, self.default_criterion["points"])
        self.assertEqual(criterion_obj.handgrading_rubric,
                         self.default_criterion["handgrading_rubric"])

    def test_create_average_case(self):
        criterion_inputs = {
            "short_description": "This is a short description used for testing.",
            "long_description": "This is a short description used for testing.",
            "points": 20,
            "handgrading_rubric": self.default_handgrading_rubric
        }

        criterion_obj = handgrading_models.Criterion.objects.validate_and_create(
            **criterion_inputs)

        self.assertEqual(criterion_obj.short_description, criterion_inputs["short_description"])
        self.assertEqual(criterion_obj.long_description, criterion_inputs["long_description"])
        self.assertEqual(criterion_obj.points, criterion_inputs["points"])
        self.assertEqual(criterion_obj.handgrading_rubric, criterion_inputs["handgrading_rubric"])
