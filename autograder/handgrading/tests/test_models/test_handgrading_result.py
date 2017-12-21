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

        self.submission = obj_build.build_submission()

    def test_default_initialization(self):
        result_inputs = {
            "submission": self.submission,
            "submission_group": self.submission.submission_group,
            "handgrading_rubric": self.default_handgrading_rubric
        }

        handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            **result_inputs)  # type: handgrading_models.HandgradingResult
        self.assertEqual(handgrading_result.submission, result_inputs["submission"])
        self.assertEqual(handgrading_result.handgrading_rubric, result_inputs["handgrading_rubric"])
        self.assertEqual(handgrading_result.submission_group, result_inputs["submission_group"])
        self.assertEqual(0, handgrading_result.points_adjustment)

    def test_create_non_defaults(self):
        points_to_try = [-2, 5]
        for points in points_to_try:
            result = handgrading_models.HandgradingResult.objects.validate_and_create(
                submission=self.submission,
                submission_group=self.submission.submission_group,
                handgrading_rubric=self.default_handgrading_rubric,
                points_adjustment=points)

            result.refresh_from_db()

            self.assertEqual(points, result.points_adjustment)
            result.delete()

    def test_serializable_fields(self):
        expected_fields = [
            'pk',
            'last_modified',

            'submission',
            'submission_group',
            'handgrading_rubric',

            'applied_annotations',
            'arbitrary_points',
            'comments',
            'criterion_results',

            'points_adjustment',
        ]

        result_inputs = {
            "submission": self.submission,
            "submission_group": self.submission.submission_group,
            "handgrading_rubric": self.default_handgrading_rubric
        }

        result_obj = handgrading_models.HandgradingResult.objects.validate_and_create(
            **result_inputs
        )

        result_dict = result_obj.to_dict()
        self.assertCountEqual(expected_fields, result_dict.keys())

        with self.assertRaises(ValidationError):
            result_obj.validate_and_update(**result_dict)

    def test_serialize_related(self):
        expected_fields = [
            'pk',
            'last_modified',

            'submission',
            'handgrading_rubric',
            'submission_group',

            'applied_annotations',
            'arbitrary_points',
            'comments',
            'criterion_results',

            'points_adjustment',
        ]

        submission = obj_build.build_submission(submitted_filenames=["test.cpp"])

        result_obj = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            submission_group=submission.submission_group,
            handgrading_rubric=self.default_handgrading_rubric
        )

        applied_annotation = handgrading_models.AppliedAnnotation.objects.validate_and_create(
            comment="",
            location={
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            annotation=handgrading_models.Annotation.objects.validate_and_create(
                short_description="",
                long_description="",
                points=0,
                handgrading_rubric=self.default_handgrading_rubric
            ),
            handgrading_result=result_obj
        )

        arbitrary_points = handgrading_models.ArbitraryPoints.objects.validate_and_create(
            location={
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            text="",
            points=0,
            handgrading_result=result_obj
        )

        comment = handgrading_models.Comment.objects.validate_and_create(
            location={
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            text="HI",
            handgrading_result=result_obj
        )

        criterion_result = handgrading_models.CriterionResult.objects.validate_and_create(
            selected=True,
            criterion=handgrading_models.Criterion.objects.validate_and_create(
                points=0,
                handgrading_rubric=self.default_handgrading_rubric
            ),
            handgrading_result=result_obj
        )

        app_annotation_dict = applied_annotation.to_dict()
        arbitrary_points_dict = arbitrary_points.to_dict()
        comment_dict = comment.to_dict()
        criterion_result_dict = criterion_result.to_dict()
        result_dict = result_obj.to_dict()

        self.assertCountEqual(expected_fields, result_dict.keys())

        self.assertIsInstance(result_dict["applied_annotations"], list)
        self.assertIsInstance(result_dict["arbitrary_points"], list)
        self.assertIsInstance(result_dict["comments"], list)
        self.assertIsInstance(result_dict["criterion_results"], list)
        self.assertIsInstance(result_dict["handgrading_rubric"], object)
        self.assertIsInstance(result_dict["submission_group"], int)

        self.assertEqual(len(result_dict["applied_annotations"]), 1)
        self.assertEqual(len(result_dict["arbitrary_points"]), 1)
        self.assertEqual(len(result_dict["comments"]), 1)
        self.assertEqual(len(result_dict["criterion_results"]), 1)

        self.assertCountEqual(result_dict["applied_annotations"][0].keys(),
                              app_annotation_dict.keys())
        self.assertCountEqual(result_dict["arbitrary_points"][0].keys(),
                              arbitrary_points_dict.keys())
        self.assertCountEqual(result_dict["comments"][0].keys(),
                              comment_dict.keys())
        self.assertCountEqual(result_dict["criterion_results"][0].keys(),
                              criterion_result_dict.keys())
        self.assertCountEqual(result_dict["handgrading_rubric"].keys(),
                              self.default_handgrading_rubric.to_dict().keys())

    def test_editable_fields(self):
        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.default_handgrading_rubric)

        result.validate_and_update(points_adjustment=3)
        result.refresh_from_db()
        self.assertEqual(3, result.points_adjustment)
