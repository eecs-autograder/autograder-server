"""Comment tests"""

import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase
from django.core.exceptions import ValidationError


class CommentTestCase(UnitTestBase):
    """
    Test cases relating the Comment Model
    """
    def test_default_initialization(self):
        comment_inputs = {
            "location": {
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            "text": "HI",
            "handgrading_result": handgrading_models.HandgradingResult.objects.validate_and_create(
                submission=obj_build.build_submission(submitted_filenames=["test.cpp"])
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

        handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=obj_build.build_submission(submitted_filenames=["test.cpp"])
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

    def test_serializable_fields(self):
        expected_fields = [
            'pk',
            'last_modified',

            'location',
            'text',
            'handgrading_result',
        ]

        self.assertCountEqual(
            expected_fields,
            handgrading_models.Comment.get_serializable_fields())

        comment_obj = handgrading_models.Comment.objects.validate_and_create(
            location={
                "first_line": 0,
                "last_line": 1,
                "filename": "test.cpp"
            },
            text="hello",
            handgrading_result=handgrading_models.HandgradingResult.objects.validate_and_create(
                submission=obj_build.build_submission(submitted_filenames=["test.cpp"])
            )
        )

        self.assertTrue(comment_obj.to_dict())
