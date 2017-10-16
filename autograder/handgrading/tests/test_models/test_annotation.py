"""Annotation tests"""

import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase


class AnnotationTestCase(UnitTestBase):
    """
    Test cases relating the Annotation Model
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

        self.default_annotation = {
            "short_description": "",
            "long_description": "",
            "points": 0,
            "handgrading_rubric": self.default_handgrading_rubric
        }

    def test_default_initialization(self):
        annotation_obj = handgrading_models.Annotation.objects.validate_and_create(
                                    **self.default_annotation)

        self.assertEqual(annotation_obj.short_description,
                         self.default_annotation["short_description"])
        self.assertEqual(annotation_obj.long_description,
                         self.default_annotation["long_description"])
        self.assertEqual(annotation_obj.points, self.default_annotation["points"])
        self.assertEqual(annotation_obj.handgrading_rubric,
                         self.default_annotation["handgrading_rubric"])

    def test_create_average_case(self):
        annotation_inputs = {
            "short_description": "This is a short description used for testing.",
            "long_description": "This is a long description used for testing.",
            "points": 20,
            "handgrading_rubric": self.default_handgrading_rubric
        }

        annotation_obj = handgrading_models.Annotation.objects.validate_and_create(
            **annotation_inputs)

        self.assertEqual(annotation_obj.short_description, annotation_inputs["short_description"])
        self.assertEqual(annotation_obj.long_description, annotation_inputs["long_description"])
        self.assertEqual(annotation_obj.points, annotation_inputs["points"])
