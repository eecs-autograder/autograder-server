"""Applied Annotation tests"""

import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase
from django.core.exceptions import ValidationError
from copy import deepcopy
# import pprint


class AppliedAnnotationTestCase(UnitTestBase):
    """
    Test cases relating the Applied Annotation Model
    """
    def setUp(self):
        default_handgrading_rubric = (
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
                max_points=0,
                show_grades_and_rubric_to_students=False,
                handgraders_can_leave_comments=True,
                handgraders_can_apply_arbitrary_points=True,
                project=obj_build.build_project()
            )
        )

        self.default_location_dict = {
            "first_line": 0,
            "last_line": 1,
            "filename": "test.cpp"
        }

        self.default_annotation_obj = handgrading_models.Annotation.objects.validate_and_create(
            short_description="",
            long_description="",
            points=0,
            handgrading_rubric=default_handgrading_rubric
        )

        submission = obj_build.build_submission(submitted_filenames=["test.cpp"])

        self.default_handgrading_result_obj = (
            handgrading_models.HandgradingResult.objects.validate_and_create(
                submission=submission,
                submission_group=submission.submission_group,
                handgrading_rubric=default_handgrading_rubric
            )
        )

        self.default_applied_annotation_inputs = {
            "comment": "",
            "location": self.default_location_dict,
            "annotation": self.default_annotation_obj,
            "handgrading_result": self.default_handgrading_result_obj
        }

    def test_default_initialization(self):
        app_annotation_obj = handgrading_models.AppliedAnnotation.objects.validate_and_create(
            **self.default_applied_annotation_inputs
        )

        self.assertEqual(app_annotation_obj.comment,
                         self.default_applied_annotation_inputs["comment"])
        self.assertEqual(app_annotation_obj.annotation,
                         self.default_applied_annotation_inputs["annotation"])
        self.assertEqual(app_annotation_obj.handgrading_result,
                         self.default_applied_annotation_inputs["handgrading_result"])

        self.assertEqual(app_annotation_obj.location.first_line,
                         self.default_applied_annotation_inputs["location"]["first_line"])
        self.assertEqual(app_annotation_obj.location.last_line,
                         self.default_applied_annotation_inputs["location"]["last_line"])
        self.assertEqual(app_annotation_obj.location.filename,
                         self.default_applied_annotation_inputs["location"]["filename"])

    def test_applied_annotation_with_comment(self):
        inputs = {
            "comment": "Testing comment. This can be longer.",
            "location": self.default_location_dict,
            "annotation": self.default_annotation_obj,
            "handgrading_result": self.default_handgrading_result_obj
        }

        app_annotation_obj = handgrading_models.AppliedAnnotation.objects.validate_and_create(
            **inputs
        )

        self.assertEqual(app_annotation_obj.comment, inputs["comment"])
        self.assertEqual(app_annotation_obj.annotation, inputs["annotation"])
        self.assertEqual(app_annotation_obj.handgrading_result, inputs["handgrading_result"])

        self.assertEqual(app_annotation_obj.location.first_line, inputs["location"]["first_line"])
        self.assertEqual(app_annotation_obj.location.last_line, inputs["location"]["last_line"])
        self.assertEqual(app_annotation_obj.location.filename, inputs["location"]["filename"])

    def test_allow_applied_annotation_to_not_have_comments(self):
        annotation_obj = handgrading_models.AppliedAnnotation.objects.validate_and_create(
            location=self.default_location_dict,
            annotation=self.default_annotation_obj,
            handgrading_result=self.default_handgrading_result_obj
        )

        self.assertEqual(annotation_obj.comment, "")

    def test_filename_in_location_must_be_in_submitted_files(self):
        """
        Default submission filename is "test.cpp" (see handgrading_obj_builders)
        """

        # Submission in handgrading_result contains filename "test.cpp" (see defaults),
        # but location's filename is set to "WRONG.cpp"

        with self.assertRaises(ValidationError):
            handgrading_models.AppliedAnnotation.objects.validate_and_create(
                location={
                    "first_line": 0,
                    "last_line": 1,
                    "filename": "WRONG.cpp"
                },
                annotation=self.default_annotation_obj,
                handgrading_result=self.default_handgrading_result_obj
            )

    def test_serializable_fields(self):
        expected_fields = [
            'pk',
            'last_modified',

            'comment',
            'location',
            'annotation',
            'handgrading_result',
        ]

        app_annotation_obj = handgrading_models.AppliedAnnotation.objects.validate_and_create(
            **self.default_applied_annotation_inputs
        )

        app_annotation_dict = app_annotation_obj.to_dict()

        self.assertCountEqual(expected_fields, app_annotation_dict.keys())
        self.assertIsInstance(app_annotation_dict['location'], dict)

        for non_editable in ['pk', 'last_modified', 'location', 'annotation', 'handgrading_result']:
            app_annotation_dict.pop(non_editable)

        app_annotation_obj.validate_and_update(**app_annotation_dict)

    def test_serialize_related(self):
        expected_fields = [
            'pk',
            'last_modified',

            'comment',
            'location',
            'annotation',
            'handgrading_result',
        ]

        app_annotation_obj = handgrading_models.AppliedAnnotation.objects.validate_and_create(
            **self.default_applied_annotation_inputs
        )

        app_annotation_dict = app_annotation_obj.to_dict()
        self.assertCountEqual(expected_fields, app_annotation_dict.keys())

        self.assertIsInstance(app_annotation_dict["annotation"], object)
        self.assertCountEqual(app_annotation_dict["annotation"].keys(),
                              self.default_annotation_obj.to_dict().keys())
