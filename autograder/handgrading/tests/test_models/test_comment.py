"""Comment tests"""

import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase
from django.core.exceptions import ValidationError


class CommentTestCase(UnitTestBase):
    """
    Test cases relating the Comment Model
    """
    def setUp(self):
        self.default_handgrading_rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
                max_points=0,
                show_grades_and_rubric_to_students=False,
                handgraders_can_leave_comments=True,
                handgraders_can_adjust_points=True,
                project=obj_build.build_project()
            )
        )

    def test_default_initialization(self):
        submission = obj_build.make_submission(submitted_filenames=["test.cpp"])

        comment_inputs = {
            "location": {
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            "text": "HI",
            "handgrading_result": handgrading_models.HandgradingResult.objects.validate_and_create(
                submission=submission,
                group=submission.group,
                handgrading_rubric=self.default_handgrading_rubric
            )
        }

        comment_obj = handgrading_models.Comment.objects.validate_and_create(**comment_inputs)

        self.assertEqual(comment_obj.location.first_line, comment_inputs["location"]["first_line"])
        self.assertEqual(comment_obj.location.last_line, comment_inputs["location"]["last_line"])
        self.assertEqual(comment_obj.location.filename, comment_inputs["location"]["filename"])

        self.assertEqual(comment_obj.text, comment_inputs["text"])
        self.assertEqual(comment_obj.handgrading_result, comment_inputs["handgrading_result"])

    def test_filename_in_location_must_be_in_submitted_files(self):
        """ Submission in handgrading_result contains filename "test.cpp" (see defaults),
            but location's filename is set to "WRONG.cpp" """
        submission = obj_build.make_submission(submitted_filenames=["test.cpp"])

        handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            group=submission.group,
            handgrading_rubric=self.default_handgrading_rubric
        )

        with self.assertRaises(ValidationError):
            handgrading_models.Comment.objects.validate_and_create(
                location={
                    "first_line": 0,
                    "last_line": 1,
                    "filename": "WRONG.cpp"
                },
                text="hello",
                handgrading_result=handgrading_result
            )

    def test_comment_doesnt_require_location(self):
        submission = obj_build.make_submission()

        handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            group=submission.group,
            handgrading_rubric=self.default_handgrading_rubric
        )

        handgrading_models.Comment.objects.validate_and_create(
            text="hello",
            handgrading_result=handgrading_result
        )

    def test_comment_ordering(self):
        submission = obj_build.make_submission()

        handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            group=submission.group,
            handgrading_rubric=self.default_handgrading_rubric)

        # Using create instead of validate_and_create in order to define the pk
        handgrading_models.Comment.objects.create(
            text="hello",
            handgrading_result=handgrading_result,
            pk=10)

        handgrading_models.Comment.objects.create(
            text="hello",
            handgrading_result=handgrading_result,
            pk=24)

        handgrading_models.Comment.objects.create(
            text="hello",
            handgrading_result=handgrading_result,
            pk=1)

        all_comments = handgrading_models.Comment.objects.all()

        self.assertTrue(all_comments.ordered)
        self.assertEqual(all_comments[0].pk, 1)
        self.assertEqual(all_comments[1].pk, 10)
        self.assertEqual(all_comments[2].pk, 24)

    def test_serializable_fields(self):
        expected_fields = [
            'pk',
            'last_modified',

            'location',
            'text',
            'handgrading_result',
        ]

        submission = obj_build.make_submission(submitted_filenames=["test.cpp"])

        comment_obj = handgrading_models.Comment.objects.validate_and_create(
            location={
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            text="hello",
            handgrading_result=handgrading_models.HandgradingResult.objects.validate_and_create(
                submission=submission,
                group=submission.group,
                handgrading_rubric=self.default_handgrading_rubric
            )
        )

        comment_dict = comment_obj.to_dict()

        self.assertCountEqual(expected_fields, comment_dict.keys())
        self.assertIsInstance(comment_dict['location'], dict)

        for non_editable in ['pk', 'last_modified', 'location', 'handgrading_result']:
            comment_dict.pop(non_editable)

        comment_obj.validate_and_update(**comment_dict)
