import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase


class HandgradingResultTestCase(UnitTestBase):
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
        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.default_handgrading_rubric)

        self.assertEqual(result.submission, self.submission)
        self.assertEqual(result.handgrading_rubric, self.default_handgrading_rubric)
        self.assertEqual(result.submission_group, self.submission.submission_group)
        self.assertFalse(result.finished_grading)

    def test_edit_finished_grading(self):
        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.default_handgrading_rubric)
        self.assertFalse(result.finished_grading)

        result.validate_and_update(finished_grading=True)
        result.refresh_from_db()
        self.assertTrue(result.finished_grading)

    def test_serialization(self):
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

            'finished_grading',
        ]

        submission = obj_build.build_submission(submitted_filenames=["test.cpp"])

        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            submission_group=submission.submission_group,
            handgrading_rubric=self.default_handgrading_rubric
        )

        result_dict = result.to_dict()
        self.assertCountEqual(expected_fields, result_dict.keys())

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
            handgrading_result=result
        )

        arbitrary_points = handgrading_models.ArbitraryPoints.objects.validate_and_create(
            location={
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            text="",
            points=0,
            handgrading_result=result
        )

        comment = handgrading_models.Comment.objects.validate_and_create(
            location={
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            text="HI",
            handgrading_result=result
        )

        criterion_result = handgrading_models.CriterionResult.objects.validate_and_create(
            selected=True,
            criterion=handgrading_models.Criterion.objects.validate_and_create(
                points=0,
                handgrading_rubric=self.default_handgrading_rubric
            ),
            handgrading_result=result
        )

        app_annotation_dict = applied_annotation.to_dict()
        arbitrary_points_dict = arbitrary_points.to_dict()
        comment_dict = comment.to_dict()
        criterion_result_dict = criterion_result.to_dict()
        result_dict = result.to_dict()

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
