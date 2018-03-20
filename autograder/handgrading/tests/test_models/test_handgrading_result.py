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
        self.rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
            project=obj_build.build_project())

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

    def test_total_points_all_points_sources(self):
        self.rubric.validate_and_update(
            points_style=handgrading_models.PointsStyle.start_at_zero_and_add,
            max_points=None)

        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.rubric)

        selected_positive_crit = handgrading_models.Criterion.objects.validate_and_create(
            points=16,
            handgrading_rubric=self.rubric)
        handgrading_models.CriterionResult.objects.validate_and_create(
            selected=True,
            criterion=selected_positive_crit,
            handgrading_result=result)

        unselected_positive_crit = handgrading_models.Criterion.objects.validate_and_create(
            points=8,
            handgrading_rubric=self.rubric)
        handgrading_models.CriterionResult.objects.validate_and_create(
            selected=False,
            criterion=unselected_positive_crit,
            handgrading_result=result)

        selected_negative_crit = handgrading_models.Criterion.objects.validate_and_create(
            points=-4,
            handgrading_rubric=self.rubric)
        handgrading_models.CriterionResult.objects.validate_and_create(
            selected=True,
            criterion=selected_negative_crit,
            handgrading_result=result)

        used_twice_annotation = handgrading_models.Annotation.objects.validate_and_create(
            deduction=-1.5,
            handgrading_rubric=self.rubric)
        for i in range(2):
            handgrading_models.AppliedAnnotation.objects.validate_and_create(
                location={
                    "first_line": 0,
                    "last_line": 1,
                    "filename": "file1"
                },
                annotation=used_twice_annotation,
                handgrading_result=result)

        unused_annotation = handgrading_models.Annotation.objects.validate_and_create(
            deduction=-1,
            handgrading_rubric=self.rubric)

        expected_points = (selected_positive_crit.points +
                           selected_negative_crit.points +
                           used_twice_annotation.deduction * 2)

        expected_points_possible = selected_positive_crit.points + unselected_positive_crit.points

        self.assertEqual(expected_points, result.total_points)
        self.assertEqual(expected_points_possible, result.total_points_possible)

        for adjustment in -3, 5:
            result.validate_and_update(points_adjustment=adjustment)
            self.assertEqual(expected_points + adjustment, result.total_points)
            self.assertEqual(expected_points_possible, result.total_points_possible)

    def test_max_points_null_total_points_possible_computed_from_positive_criteria_points(self):
        self.rubric.validate_and_update(
            points_style=handgrading_models.PointsStyle.start_at_zero_and_add,
            max_points=None)

        criterion1 = handgrading_models.Criterion.objects.validate_and_create(
            points=2,
            handgrading_rubric=self.rubric)
        criterion2 = handgrading_models.Criterion.objects.validate_and_create(
            points=5,
            handgrading_rubric=self.rubric)
        negative_criterion = handgrading_models.Criterion.objects.validate_and_create(
            points=-3,
            handgrading_rubric=self.rubric)

        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.rubric)

        self.assertEqual(criterion1.points + criterion2.points, result.total_points_possible)

    def test_max_points_not_null_total_points_greater_than_possible(self):
        self.rubric.validate_and_update(
            points_style=handgrading_models.PointsStyle.start_at_zero_and_add,
            max_points=6)

        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.rubric)

        criterion1 = handgrading_models.Criterion.objects.validate_and_create(
            points=2, handgrading_rubric=self.rubric)
        handgrading_models.CriterionResult.objects.validate_and_create(
            criterion=criterion1, handgrading_result=result, selected=True)

        criterion2 = handgrading_models.Criterion.objects.validate_and_create(
            points=5, handgrading_rubric=self.rubric)
        handgrading_models.CriterionResult.objects.validate_and_create(
            criterion=criterion2, handgrading_result=result, selected=True)

        self.assertEqual(criterion1.points + criterion2.points, result.total_points)
        self.assertEqual(self.rubric.max_points, result.total_points_possible)
        self.assertGreater(result.total_points, result.total_points_possible)

    def test_no_negative_total_points(self):
        self.rubric.validate_and_update(
            points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
            max_points=8)

        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.rubric,
            points_adjustment=-3)

        negative_crit = handgrading_models.Criterion.objects.validate_and_create(
            points=-4,
            handgrading_rubric=self.rubric)
        handgrading_models.CriterionResult.objects.validate_and_create(
            selected=True,
            criterion=negative_crit,
            handgrading_result=result)

        annotation = handgrading_models.Annotation.objects.validate_and_create(
            deduction=-2,
            handgrading_rubric=self.rubric)
        handgrading_models.AppliedAnnotation.objects.validate_and_create(
            location={
                "first_line": 0,
                "last_line": 1,
                "filename": "file1"
            },
            annotation=annotation,
            handgrading_result=result)

        self.assertEqual(0, result.total_points)
        self.assertEqual(self.rubric.max_points, result.total_points_possible)

    def test_total_points_start_at_max_and_subtract(self):
        self.rubric.validate_and_update(
            max_points=10, points_style=handgrading_models.PointsStyle.start_at_max_and_subtract)
        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.rubric)

        annotation = handgrading_models.Annotation.objects.validate_and_create(
            deduction=-2,
            handgrading_rubric=self.rubric)

        for i in range(3):
            handgrading_models.AppliedAnnotation.objects.validate_and_create(
                location={
                    "first_line": 0,
                    "last_line": 1,
                    "filename": "file1"
                },
                annotation=annotation,
                handgrading_result=result
            )

        self.assertEqual(4, result.total_points)
        self.assertEqual(self.rubric.max_points, result.total_points_possible)

    def test_total_points_respects_max_deduction_on_annotations(self):
        self.rubric.validate_and_update(
            max_points=20, points_style=handgrading_models.PointsStyle.start_at_max_and_subtract)
        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.rubric)

        annotation = handgrading_models.Annotation.objects.validate_and_create(
            deduction=-2,
            max_deduction=-8,
            handgrading_rubric=self.rubric)

        for i in range(8):
            handgrading_models.AppliedAnnotation.objects.validate_and_create(
                location={
                    "first_line": 0,
                    "last_line": 1,
                    "filename": "file1"
                },
                annotation=annotation,
                handgrading_result=result
            )

        self.assertEqual(self.rubric.max_points + annotation.max_deduction, result.total_points)
        self.assertEqual(self.rubric.max_points, result.total_points_possible)

    def test_total_points_with_no_criteria_or_annotations(self):
        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.rubric)

        self.assertEqual(0, result.criterion_results.count())
        self.assertEqual(0, self.rubric.criteria.count())
        self.assertEqual(0, result.total_points_possible)
        self.assertEqual(0, result.total_points)

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
            'total_points_possible',
        ]

        submission = obj_build.build_submission(submitted_filenames=["test.cpp"])

        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            submission_group=submission.submission_group,
            handgrading_rubric=self.rubric
        )

        applied_annotation = handgrading_models.AppliedAnnotation.objects.validate_and_create(
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
            handgrading_result=result)

        comment2 = handgrading_models.Comment.objects.validate_and_create(
            location={
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            text="HI",
            handgrading_result=result)

        criterion1 = handgrading_models.Criterion.objects.validate_and_create(
            points=0,
            handgrading_rubric=self.rubric)
        criterion_result1 = handgrading_models.CriterionResult.objects.validate_and_create(
            selected=True,
            criterion=criterion1,
            handgrading_result=result)

        criterion2 = handgrading_models.Criterion.objects.validate_and_create(
            points=0,
            handgrading_rubric=self.rubric)
        criterion_result2 = handgrading_models.CriterionResult.objects.validate_and_create(
            selected=True,
            criterion=criterion2,
            handgrading_result=result)

        result.handgrading_rubric.set_criterion_order([criterion2.pk, criterion1.pk])
        expected_criterion_results = [criterion_result2.to_dict(), criterion_result1.to_dict()]

        # Make list of comments ordered by pk
        expected_comments = sorted([comment.to_dict(), comment2.to_dict()],
                                   key=lambda comment: comment["pk"])

        result.refresh_from_db()
        result_dict = result.to_dict()
        self.assertCountEqual(expected_fields, result_dict.keys())

        self.assertIsInstance(result_dict["applied_annotations"], list)
        self.assertIsInstance(result_dict["comments"], list)
        self.assertIsInstance(result_dict["criterion_results"], list)
        self.assertIsInstance(result_dict["handgrading_rubric"], object)
        self.assertIsInstance(result_dict["submission_group"], int)

        self.assertSequenceEqual(result_dict["applied_annotations"], [applied_annotation.to_dict()])
        self.assertSequenceEqual(result_dict["criterion_results"], expected_criterion_results)
        self.assertSequenceEqual(result_dict["comments"], expected_comments)

    def test_editable_fields(self):
        result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=self.submission,
            submission_group=self.submission.submission_group,
            handgrading_rubric=self.rubric)

        result.validate_and_update(points_adjustment=3, finished_grading=True)
        result.refresh_from_db()
        self.assertEqual(3, result.points_adjustment)
        self.assertTrue(result.finished_grading)
