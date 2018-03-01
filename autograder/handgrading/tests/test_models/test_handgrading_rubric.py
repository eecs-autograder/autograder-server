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
        self.project = obj_build.make_project()

    def test_default_initialization(self):
        rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
            project=self.project)  # type: handgrading_models.HandgradingRubric

        self.assertEqual(self.project, rubric.project)
        self.assertEqual(handgrading_models.PointsStyle.start_at_zero_and_add, rubric.points_style)
        self.assertIsNone(rubric.max_points)
        self.assertFalse(rubric.show_grades_and_rubric_to_students)
        self.assertFalse(rubric.handgraders_can_leave_comments)
        self.assertFalse(rubric.handgraders_can_adjust_points)

    def test_create_non_defaults(self):
        rubric_kwargs = {
            "points_style": handgrading_models.PointsStyle.start_at_max_and_subtract,
            "max_points": 25,
            "show_grades_and_rubric_to_students": True,
            "handgraders_can_leave_comments": True,
            "handgraders_can_adjust_points": True,
            "project": self.project
        }

        rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
            **rubric_kwargs)

        for field, value in rubric_kwargs.items():
            self.assertEqual(value, getattr(rubric, field))

    def test_invalid_points_style(self):
        """
        Assert that a handgrading object cannot be created with random string as point style
        """
        with self.assertRaises(ValidationError) as cm:
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                project=self.project,
                points_style='not_a_points_style')

        self.assertIn('points_style', cm.exception.message_dict)

    def test_invalid_negative_max_points(self):
        """
        Assert that a handgrading object cannot be created with invalid max points input
        (ex. negative numbers, floats, strings)
        """

        with self.assertRaises(ValidationError) as cm:
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                project=self.project, max_points=-1)

        self.assertIn('max_points', cm.exception.message_dict)

    def test_invalid_max_points_null_with_start_at_max_points_style(self):
        with self.assertRaises(ValidationError) as cm:
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                project=self.project,
                points_style=handgrading_models.PointsStyle.start_at_max_and_subtract)

        self.assertIn('max_points', cm.exception.message_dict)

    def test_serializable_fields(self):
        expected_fields = [
            'pk',
            'last_modified',

            'points_style',
            'max_points',
            'show_grades_and_rubric_to_students',
            'handgraders_can_leave_comments',
            'handgraders_can_adjust_points',

            'project',
            'criteria',
            'annotations',
        ]

        handgrading_obj = handgrading_models.HandgradingRubric.objects.validate_and_create(
            project=self.project)

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
            'handgraders_can_adjust_points',

            'project',
            'criteria',
            'annotations',
        ]

        rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
            project=self.project)

        criterion = handgrading_models.Criterion.objects.validate_and_create(
            short_description="sample short description",
            long_description="sample loooooong description",
            points=0,
            handgrading_rubric=rubric)

        criterion2 = handgrading_models.Criterion.objects.validate_and_create(
            short_description="sample short description",
            long_description="sample loooooong description",
            points=0,
            handgrading_rubric=rubric)

        annotation = handgrading_models.Annotation.objects.validate_and_create(
            handgrading_rubric=rubric)

        annotation2 = handgrading_models.Annotation.objects.validate_and_create(
            handgrading_rubric=rubric)

        rubric.set_criterion_order([criterion2.pk, criterion.pk])
        expected_criterion_order = [criterion2.to_dict(), criterion.to_dict()]
        rubric.set_annotation_order([annotation2.pk, annotation.pk])
        expected_annotation_order = [annotation2.to_dict(), annotation.to_dict()]

        rubric.refresh_from_db()
        handgrading_rubric_dict = rubric.to_dict()
        self.assertCountEqual(expected_fields, handgrading_rubric_dict.keys())

        self.assertIsInstance(handgrading_rubric_dict["criteria"], list)
        self.assertIsInstance(handgrading_rubric_dict["annotations"], list)

        self.assertSequenceEqual(handgrading_rubric_dict["criteria"], expected_criterion_order)
        self.assertSequenceEqual(handgrading_rubric_dict["annotations"], expected_annotation_order)
