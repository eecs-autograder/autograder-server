"""Applied Annotation tests"""

from pathlib import Path
import subprocess
import tempfile

import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile


class AppliedAnnotationTestCase(UnitTestBase):
    """
    Test cases relating the Applied Annotation Model
    """
    def setUp(self):
        super().setUp()

        # Note: setting submitted_filenames directly like this does not create any files
        # in the filesystem.
        submission = obj_build.make_submission(submitted_filenames=["test.cpp"])
        self.project = submission.project

        self.rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
            points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
            max_points=10,
            show_grades_and_rubric_to_students=False,
            handgraders_can_leave_comments=True,
            handgraders_can_adjust_points=True,
            project=self.project
        )

        self.default_location_dict = {
            "first_line": 0,
            "last_line": 1,
            "filename": "test.cpp"
        }

        self.annotation = handgrading_models.Annotation.objects.validate_and_create(
            handgrading_rubric=self.rubric)

        self.default_handgrading_result_obj = (
            handgrading_models.HandgradingResult.objects.validate_and_create(
                submission=submission,
                group=submission.group,
                handgrading_rubric=self.rubric
            )
        )

        self.default_applied_annotation_inputs = {
            "location": self.default_location_dict,
            "annotation": self.annotation,
            "handgrading_result": self.default_handgrading_result_obj
        }

    def test_default_initialization(self):
        app_annotation_obj = handgrading_models.AppliedAnnotation.objects.validate_and_create(
            **self.default_applied_annotation_inputs
        )

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

    def test_filename_in_location_must_be_in_submitted_files(self):
        # Submission in handgrading_result contains filename "test.cpp" (see defaults),
        # but location's filename is set to "WRONG.cpp"

        with self.assertRaises(ValidationError):
            handgrading_models.AppliedAnnotation.objects.validate_and_create(
                location={
                    "first_line": 0,
                    "last_line": 1,
                    "filename": "WRONG.cpp"
                },
                annotation=self.annotation,
                handgrading_result=self.default_handgrading_result_obj
            )

    def test_annotation_and_handgrading_result_belong_to_different_rubrics(self) -> None:
        other_rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
            project=obj_build.build_project())
        other_annotation = handgrading_models.Annotation.objects.validate_and_create(
            handgrading_rubric=other_rubric)

        data = dict(self.default_applied_annotation_inputs)
        data['annotation'] = other_annotation

        with self.assertRaises(ValidationError) as cm:
            handgrading_models.AppliedAnnotation.objects.validate_and_create(**data)

        self.assertIn('annotation', cm.exception.message_dict)

    def test_serializable_fields(self):
        expected_fields = [
            'pk',
            'last_modified',

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

        for non_editable in ['pk', 'last_modified', 'location',
                             'annotation', 'handgrading_result']:
            app_annotation_dict.pop(non_editable)

        app_annotation_obj.validate_and_update(**app_annotation_dict)

    def test_serialize_related(self):
        expected_fields = [
            'pk',
            'last_modified',

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
                              self.annotation.to_dict().keys())


class ApplyAnnotationToMemberOfZipArchiveTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        with tempfile.TemporaryDirectory() as temp_dir:
            subprocess.run([
                'bash', '-c',
                f'mkdir -p {temp_dir}/spam/egg; '
                f'echo "wee.txt content" > {temp_dir}/spam/wee.txt; '
                f'echo "waa.txt content" > {temp_dir}/spam/egg/waa.txt; '
                f'echo "waluigi.txt content" > {temp_dir}/waluigi.txt ;'
                f'cd {temp_dir} && zip -r spam.zip spam waluigi.txt'
            ], check=True)
            with open(Path(temp_dir) / 'spam.zip', 'rb') as f:
                self.zip_file = SimpleUploadedFile('spam.zip', f.read())

        self.project = obj_build.make_project()
        group = obj_build.make_group(project=self.project)
        obj_build.make_expected_student_file(self.project, pattern='*')
        submission = obj_build.make_submission(group=group, submitted_files=[self.zip_file])

        self.rubric = handgrading_models.HandgradingRubric.objects.validate_and_create(
            points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
            max_points=10,
            show_grades_and_rubric_to_students=False,
            handgraders_can_leave_comments=True,
            handgraders_can_adjust_points=True,
            project=self.project
        )

        self.annotation = handgrading_models.Annotation.objects.validate_and_create(
            handgrading_rubric=self.rubric)

        self.handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            group=submission.group,
            handgrading_rubric=self.rubric
        )

    def test_filename_in_location_exists_in_zip_file(self) -> None:
        applied_annotation = handgrading_models.AppliedAnnotation.objects.validate_and_create(
            location={
                'first_line': 0,
                'last_line': 1,
                'filename': 'spam.zip/waluigi.txt'
            },
            annotation=self.annotation,
            handgrading_result=self.handgrading_result
        )

        self.assertEqual(applied_annotation.annotation,
                         self.annotation)
        self.assertEqual(applied_annotation.handgrading_result,
                         self.handgrading_result)

        self.assertEqual(applied_annotation.location.first_line, 0)
        self.assertEqual(applied_annotation.location.last_line, 1)
        self.assertEqual(applied_annotation.location.filename, 'spam.zip/waluigi.txt')

    def test_filename_in_location_not_in_zip_file(self) -> None:
        with self.assertRaises(ValidationError) as cm:
            handgrading_models.AppliedAnnotation.objects.validate_and_create(
                location={
                    'first_line': 0,
                    'last_line': 1,
                    'filename': self.zip_file.name + '/nope.txt'
                },
                annotation=self.annotation,
                handgrading_result=self.handgrading_result
            )

        self.assertIn(
            'Filename is not part of submitted files', cm.exception.message_dict['__all__'])
