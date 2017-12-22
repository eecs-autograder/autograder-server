from django.core import exceptions

import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase


class AnnotationTestCase(UnitTestBase):
    def setUp(self):
        self.rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
                max_points=42,
                show_grades_and_rubric_to_students=False,
                handgraders_can_leave_comments=True,
                handgraders_can_adjust_points=True,
                project=obj_build.build_project())
        )

    def test_default_init(self):
        annotation = handgrading_models.Annotation.objects.validate_and_create(
            handgrading_rubric=self.rubric)

        self.assertEqual(self.rubric, annotation.handgrading_rubric)
        self.assertEqual('', annotation.short_description)
        self.assertEqual('', annotation.long_description)
        self.assertEqual(0, annotation.deduction)
        self.assertIsNone(annotation.max_deduction)

    def test_create_non_defaults(self):
        annotation_kwargs = {
            'handgrading_rubric': self.rubric,
            'short_description': "wee",
            'long_description': "This is a long description.",
            'deduction': -5,
            'max_deduction': -20
        }

        annotation = handgrading_models.Annotation.objects.validate_and_create(
            **annotation_kwargs)

        for field, value in annotation_kwargs.items():
            self.assertEqual(getattr(annotation, field), value, msg=field)

    def test_error_deduction_is_positive(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            handgrading_models.Annotation.objects.validate_and_create(
                handgrading_rubric=self.rubric,
                deduction=1)

        self.assertIn('deduction', cm.exception.message_dict)

    def test_error_max_deduction_non_negative(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            handgrading_models.Annotation.objects.validate_and_create(
                handgrading_rubric=self.rubric,
                max_deduction=1)

        self.assertIn('max_deduction', cm.exception.message_dict)

    def test_serializable_fields(self):
        expected_fields = [
            'pk',
            'handgrading_rubric',

            'short_description',
            'long_description',

            'deduction',
            'max_deduction',

            'last_modified',

        ]

        annotation = handgrading_models.Annotation.objects.validate_and_create(
            handgrading_rubric=self.rubric)

        annotation_dict = annotation.to_dict()
        self.assertCountEqual(expected_fields, annotation_dict.keys())

        for non_editable in ['pk', 'last_modified', 'handgrading_rubric']:
            annotation_dict.pop(non_editable)

        annotation.validate_and_update(**annotation_dict)
