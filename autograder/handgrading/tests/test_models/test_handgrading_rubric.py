"""Handgrading Rubric tests"""

import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase
from django.core.exceptions import ValidationError


class HandgradingRubricTestCase(UnitTestBase):
    """
    Test cases relating the Handgrading Rubric Model
    """
    def setUp(self):
        self.default_rubric_inputs = {
            "points_style": handgrading_models.PointsStyle.start_at_max_and_subtract,
            "max_points": 0,
            "show_grades_and_rubric_to_students": False,
            "handgraders_can_leave_comments": True,
            "handgraders_can_apply_arbitrary_points": True,
            "project": obj_build.build_project()
        }

    def test_default_initialization(self):
        rubric_obj = handgrading_models.HandgradingRubric.objects.validate_and_create(
            **self.default_rubric_inputs)

        self.assertEqual(rubric_obj.points_style, self.default_rubric_inputs["points_style"])
        self.assertEqual(rubric_obj.max_points, self.default_rubric_inputs["max_points"])
        self.assertEqual(rubric_obj.show_grades_and_rubric_to_students,
                         self.default_rubric_inputs["show_grades_and_rubric_to_students"])
        self.assertEqual(rubric_obj.handgraders_can_leave_comments,
                         self.default_rubric_inputs["handgraders_can_leave_comments"])
        self.assertEqual(rubric_obj.handgraders_can_apply_arbitrary_points,
                         self.default_rubric_inputs["handgraders_can_apply_arbitrary_points"])
        self.assertEqual(rubric_obj.project,
                         self.default_rubric_inputs["project"])

    def test_create_average_case(self):
        rubric_inputs = {
            "points_style": handgrading_models.PointsStyle.start_at_zero_and_add,
            "max_points": 25,
            "show_grades_and_rubric_to_students": True,
            "handgraders_can_leave_comments": False,
            "handgraders_can_apply_arbitrary_points": False,
            "project": obj_build.build_project()
        }

        rubric_obj = handgrading_models.HandgradingRubric.objects.validate_and_create(
            **rubric_inputs)

        self.assertEqual(rubric_obj.points_style,
                         handgrading_models.PointsStyle.start_at_zero_and_add)
        self.assertEqual(rubric_obj.max_points, 25)
        self.assertEqual(rubric_obj.show_grades_and_rubric_to_students, True)
        self.assertEqual(rubric_obj.handgraders_can_leave_comments, False)
        self.assertEqual(rubric_obj.handgraders_can_apply_arbitrary_points, False)

    def test_reject_invalid_point_style_handgrading_rubric(self):
        """
        Assert that a handgrading object cannot be created with random string as point style
        """
        rubric_inputs = self.default_rubric_inputs
        rubric_inputs["points_style"] = "INVALID_POINTS_STYLE"

        with self.assertRaises(ValidationError):
            handgrading_models.HandgradingRubric.objects.validate_and_create(**rubric_inputs)

    def test_reject_invalid_max_points_handgrading_rubric(self):
        """
        Assert that a handgrading object cannot be created with invalid max points input
        (ex. negative numbers, floats, strings)
        """
        inputs_negative = self.default_rubric_inputs
        inputs_negative["max_points"] = -1

        with self.assertRaises(ValidationError):
            handgrading_models.HandgradingRubric.objects.validate_and_create(**inputs_negative)

    def test_zero_max_points_handgrading_rubric(self):
        """
        Assert that a handgrading object can be created with 0 as max points
        """
        rubric_inputs = self.default_rubric_inputs
        rubric_inputs["max_points"] = 0

        rubric_obj = handgrading_models.HandgradingRubric.objects.validate_and_create(
            **rubric_inputs)

        self.assertEqual(rubric_obj.max_points, 0)
