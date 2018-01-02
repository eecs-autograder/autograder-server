from django.core.files.uploadedfile import SimpleUploadedFile

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase


class HandgradingResultTestCase(UnitTestBase):
    """
    Test cases relating the Handgrading Result Model
    """
    def setUp(self):
        self.rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
                max_points=0,
                project=obj_build.build_project()
            )
        )

        ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            project=self.rubric.project,
            pattern='*', max_num_matches=10)
        self.submitted_files = [
            SimpleUploadedFile('file{}'.format(i), b'waaaluigi') for i in range(4)]
        self.submission = obj_build.build_submission(
            submission_group=obj_build.make_group(project=self.rubric.project),
            submitted_files=self.submitted_files)

    def test_default_initialization(self):
        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.rubric)  # type: handgrading_models.HandgradingResult

        self.assertEqual(result.submission, self.submission)
        self.assertEqual(result.handgrading_rubric, self.rubric)
        self.assertEqual(result.submission_group, self.submission.submission_group)
        self.assertEqual(0, result.points_adjustment)
        self.assertFalse(result.finished_grading)

        self.assertCountEqual([file_.name for file_ in self.submitted_files],
                              result.submitted_filenames)

    def test_create_non_defaults(self):
        points_to_try = [-2, 5]
        for points in points_to_try:
            result = handgrading_models.HandgradingResult.objects.validate_and_create(
                submission=self.submission,
                submission_group=self.submission.submission_group,
                handgrading_rubric=self.rubric,
                points_adjustment=points)

            result.refresh_from_db()

            self.assertEqual(points, result.points_adjustment)
            result.delete()

    def test_serialization(self):
        expected_fields = [
            'pk',
            'last_modified',

            'submission',
            'handgrading_rubric',
            'submission_group',

            'applied_annotations',
            'comments',
            'criterion_results',

            'finished_grading',
            'points_adjustment',

            'submitted_filenames',
            'total_points',
            'total_possible_points',
        ]

        submission = obj_build.build_submission(submitted_filenames=["test.cpp"])

        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            submission_group=submission.submission_group,
            handgrading_rubric=self.rubric
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
                handgrading_rubric=self.rubric),
            handgrading_result=result)

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
                handgrading_rubric=self.rubric
            ),
            handgrading_result=result
        )

        app_annotation_dict = applied_annotation.to_dict()
        comment_dict = comment.to_dict()
        criterion_result_dict = criterion_result.to_dict()
        result_dict = result.to_dict()

        self.assertCountEqual(expected_fields, result_dict.keys())

        self.assertIsInstance(result_dict["applied_annotations"], list)
        self.assertIsInstance(result_dict["comments"], list)
        self.assertIsInstance(result_dict["criterion_results"], list)
        self.assertIsInstance(result_dict["handgrading_rubric"], object)
        self.assertIsInstance(result_dict["submission_group"], int)
        self.assertIsInstance(result_dict["total_points"], float)
        self.assertIsInstance(result_dict["total_possible_points"], float)

        self.assertEqual(len(result_dict["applied_annotations"]), 1)
        self.assertEqual(len(result_dict["comments"]), 1)
        self.assertEqual(len(result_dict["criterion_results"]), 1)

        self.assertCountEqual(result_dict["applied_annotations"][0].keys(),
                              app_annotation_dict.keys())
        self.assertCountEqual(result_dict["comments"][0].keys(),
                              comment_dict.keys())
        self.assertCountEqual(result_dict["criterion_results"][0].keys(),
                              criterion_result_dict.keys())
        self.assertCountEqual(result_dict["handgrading_rubric"].keys(),
                              self.rubric.to_dict().keys())

    def test_editable_fields(self):
        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.rubric)

        result.validate_and_update(points_adjustment=3, finished_grading=True)
        result.refresh_from_db()
        self.assertEqual(3, result.points_adjustment)
        self.assertTrue(result.finished_grading)

    def test_total_points_properties(self):
        total_criterion_points = 0
        total_annotation_deduction = 0
        points_adjustment = 3

        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.rubric,
            points_adjustment=points_adjustment)

        for num in range(8):
            handgrading_models.CriterionResult.objects.validate_and_create(
                selected=True,
                criterion=handgrading_models.Criterion.objects.validate_and_create(
                    points=num,
                    handgrading_rubric=self.rubric
                ),
                handgrading_result=result
            )

            total_criterion_points += num

        # Since selected=False, it should not be counted in total_points
        handgrading_models.CriterionResult.objects.validate_and_create(
            selected=False,
            criterion=handgrading_models.Criterion.objects.validate_and_create(
                points=10,
                handgrading_rubric=self.rubric
            ),
            handgrading_result=result
        )

        total_criterion_points += 10

        for num in range(-4, -1):
            handgrading_models.AppliedAnnotation.objects.validate_and_create(
                comment="",
                location={
                    "first_line": 0,
                    "last_line": 1,
                    "filename": "file1"
                },
                annotation=handgrading_models.Annotation.objects.validate_and_create(
                    deduction=num,
                    handgrading_rubric=self.rubric
                ),
                handgrading_result=result
            )

            total_annotation_deduction += num

        total_points = (total_criterion_points - 10 + total_annotation_deduction +
                        points_adjustment)

        self.assertEqual(total_criterion_points, result.total_possible_points)
        self.assertEqual(total_points, result.total_points)

    def test_no_negative_total_points(self):
        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.rubric,
            points_adjustment=-3)

        self.assertEqual(0, result.total_points)

    def test_total_points_respects_max_deduction_on_annotations(self):
        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.rubric,
            points_adjustment=20)

        annotation = handgrading_models.Annotation.objects.validate_and_create(
            deduction=-2,
            max_deduction=-8,
            handgrading_rubric=self.rubric)

        for i in range(8):
            handgrading_models.AppliedAnnotation.objects.validate_and_create(
                comment="",
                location={
                    "first_line": 0,
                    "last_line": 1,
                    "filename": "file1"
                },
                annotation=annotation,
                handgrading_result=result
            )

        self.assertEqual(20 - 8, result.total_points)
