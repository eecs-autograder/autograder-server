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
        self.rubric_kwargs = {
            "points_style": handgrading_models.PointsStyle.start_at_max_and_subtract,
            "max_points": 0,
            "show_grades_and_rubric_to_students": False,
            "handgraders_can_leave_comments": True,
            "handgraders_can_apply_arbitrary_points": True,
            "project": obj_build.build_project()
        }

    def test_default_initialization(self):
        rubric_obj = handgrading_models.HandgradingRubric.objects.validate_and_create(
            **self.rubric_kwargs)

        self.assertEqual(rubric_obj.points_style, self.rubric_kwargs["points_style"])
        self.assertEqual(rubric_obj.max_points, self.rubric_kwargs["max_points"])
        self.assertEqual(rubric_obj.show_grades_and_rubric_to_students,
                         self.rubric_kwargs["show_grades_and_rubric_to_students"])
        self.assertEqual(rubric_obj.handgraders_can_leave_comments,
                         self.rubric_kwargs["handgraders_can_leave_comments"])
        self.assertEqual(rubric_obj.handgraders_can_apply_arbitrary_points,
                         self.rubric_kwargs["handgraders_can_apply_arbitrary_points"])
        self.assertEqual(rubric_obj.project,
                         self.rubric_kwargs["project"])

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
        rubric_inputs = self.rubric_kwargs
        rubric_inputs["points_style"] = "INVALID_POINTS_STYLE"

        with self.assertRaises(ValidationError):
            handgrading_models.HandgradingRubric.objects.validate_and_create(**rubric_inputs)

    def test_reject_invalid_max_points_handgrading_rubric(self):
        """
        Assert that a handgrading object cannot be created with invalid max points input
        (ex. negative numbers, floats, strings)
        """
        inputs_negative = self.rubric_kwargs
        inputs_negative["max_points"] = -1

        with self.assertRaises(ValidationError):
            handgrading_models.HandgradingRubric.objects.validate_and_create(**inputs_negative)

    def test_zero_max_points_handgrading_rubric(self):
        """
        Assert that a handgrading object can be created with 0 as max points
        """
        rubric_inputs = self.rubric_kwargs
        rubric_inputs["max_points"] = 0

        rubric_obj = handgrading_models.HandgradingRubric.objects.validate_and_create(
            **rubric_inputs)

        self.assertEqual(rubric_obj.max_points, 0)

    def test_serializable_fields(self):
        expected_fields = [
            'pk',
            'last_modified',

            'points_style',
            'max_points',
            'show_grades_and_rubric_to_students',
            'handgraders_can_leave_comments',
            'handgraders_can_apply_arbitrary_points',

            'project',
            'criteria',
            'annotations',
        ]

        handgrading_obj = handgrading_models.HandgradingRubric.objects.validate_and_create(
            **self.rubric_kwargs)

        handgrading_dict = handgrading_obj.to_dict()
        self.assertCountEqual(expected_fields, handgrading_dict.keys())

        for non_editable in ['pk', 'last_modified', 'project', 'criteria', 'annotations']:
            handgrading_dict.pop(non_editable)

        handgrading_obj.validate_and_update(**handgrading_dict)

    def test_serialize_related(self):
        expected_fields = [
            'pk',
            'last_modified',

            'points_style',
            'max_points',
            'show_grades_and_rubric_to_students',
            'handgraders_can_leave_comments',
            'handgraders_can_apply_arbitrary_points',

            'project',
            'criteria',
            'annotations',
        ]

        rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
            **self.rubric_kwargs)

        criterion = handgrading_models.Criterion.objects.validate_and_create(
            short_description="sample short description",
            long_description="sample loooooong description",
            points=0,
            handgrading_rubric=rubric
        )

        annotation = handgrading_models.Annotation.objects.validate_and_create(
            handgrading_rubric=rubric)

        annotation_dict = annotation.to_dict()
        criterion_dict = criterion.to_dict()
        handgrading_dict = rubric.to_dict()

        self.assertCountEqual(expected_fields, handgrading_dict.keys())

        self.assertIsInstance(handgrading_dict["criteria"], list)
        self.assertIsInstance(handgrading_dict["annotations"], list)

        self.assertEqual(len(handgrading_dict["criteria"]), 1)
        self.assertEqual(len(handgrading_dict["annotations"]), 1)

        self.assertCountEqual(handgrading_dict["criteria"][0].keys(), criterion_dict.keys())
        self.assertCountEqual(handgrading_dict["annotations"][0].keys(), annotation_dict.keys())
