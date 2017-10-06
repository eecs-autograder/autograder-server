"""
Test Handgrading models
"""
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase
from django.core.exceptions import ValidationError


class HandgradingRubricTestCase(UnitTestBase):
    """
    Test cases relating the Handgrading Rubric Model
    """
    def setUp(self):
        self.default_rubric_inputs = {
            "points_style": handgrading_models.PointsStyle.start_at_max_and_subtract,
            "max_points": 0,
            "show_grades_and_rubric_to_students": False,
            "handgraders_can_leave_comments": True,
            "handgraders_can_apply_arbitrary_points": True,
            "project": obj_build.build_project()
        }

    def test_default_initialization(self):
        rubric_obj = handgrading_models.HandgradingRubric.objects.validate_and_create(
            **self.default_rubric_inputs)

        self.assertEqual(rubric_obj.points_style, self.default_rubric_inputs["points_style"])
        self.assertEqual(rubric_obj.max_points, self.default_rubric_inputs["max_points"])
        self.assertEqual(rubric_obj.show_grades_and_rubric_to_students,
                         self.default_rubric_inputs["show_grades_and_rubric_to_students"])
        self.assertEqual(rubric_obj.handgraders_can_leave_comments,
                         self.default_rubric_inputs["handgraders_can_leave_comments"])
        self.assertEqual(rubric_obj.handgraders_can_apply_arbitrary_points,
                         self.default_rubric_inputs["handgraders_can_apply_arbitrary_points"])
        self.assertEqual(rubric_obj.project,
                         self.default_rubric_inputs["project"])

    def test_create_average_case(self):
        rubric_inputs = {
            "points_style": handgrading_models.PointsStyle.start_at_zero_and_add,
            "max_points": 25,
            "show_grades_and_rubric_to_students": True,
            "handgraders_can_leave_comments": False,
            "handgraders_can_apply_arbitrary_points": False,
            "project": obj_build.build_project()
        }

        rubric_obj = handgrading_models.HandgradingRubric.objects.validate_and_create(
            **rubric_inputs)

        self.assertEqual(rubric_obj.points_style,
                         handgrading_models.PointsStyle.start_at_zero_and_add)
        self.assertEqual(rubric_obj.max_points, 25)
        self.assertEqual(rubric_obj.show_grades_and_rubric_to_students, True)
        self.assertEqual(rubric_obj.handgraders_can_leave_comments, False)
        self.assertEqual(rubric_obj.handgraders_can_apply_arbitrary_points, False)

    def test_reject_invalid_point_style_handgrading_rubric(self):
        """
        Assert that a handgrading object cannot be created with random string as point style
        """
        rubric_inputs = self.default_rubric_inputs
        rubric_inputs["points_style"] = "INVALID_POINTS_STYLE"

        with self.assertRaises(ValidationError):
            handgrading_models.HandgradingRubric.objects.validate_and_create(**rubric_inputs)

    def test_reject_invalid_max_points_handgrading_rubric(self):
        """
        Assert that a handgrading object cannot be created with invalid max points input
        (ex. negative numbers, floats, strings)
        """
        inputs_negative = self.default_rubric_inputs
        inputs_negative["max_points"] = -1

        with self.assertRaises(ValidationError):
            handgrading_models.HandgradingRubric.objects.validate_and_create(**inputs_negative)

    def test_zero_max_points_handgrading_rubric(self):
        """
        Assert that a handgrading object can be created with 0 as max points
        """
        rubric_inputs = self.default_rubric_inputs
        rubric_inputs["max_points"] = 0

        rubric_obj = handgrading_models.HandgradingRubric.objects.validate_and_create(
            **rubric_inputs)

        self.assertEqual(rubric_obj.max_points, 0)


class CriterionTestCase(UnitTestBase):
    """
    Test cases relating the Criterion Model
    """
    def setUp(self):
        default_rubric_inputs = {
            "points_style": handgrading_models.PointsStyle.start_at_max_and_subtract,
            "max_points": 0,
            "show_grades_and_rubric_to_students": False,
            "handgraders_can_leave_comments": True,
            "handgraders_can_apply_arbitrary_points": True,
            "project": obj_build.build_project()
        }

        self.default_handgrading_rubric = \
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                **default_rubric_inputs)

        self.default_criterion = {
            "short_description": "",
            "long_description": "",
            "points": 0,
            "handgrading_rubric": self.default_handgrading_rubric
        }

    def test_default_initialization(self):
        criterion_obj = handgrading_models.Criterion.objects.validate_and_create(
                                    **self.default_criterion)

        self.assertEqual(criterion_obj.short_description,
                         self.default_criterion["short_description"])
        self.assertEqual(criterion_obj.long_description,
                         self.default_criterion["long_description"])
        self.assertEqual(criterion_obj.points, self.default_criterion["points"])
        self.assertEqual(criterion_obj.handgrading_rubric,
                         self.default_criterion["handgrading_rubric"])

    def test_create_average_case(self):
        criterion_inputs = {
            "short_description": "This is a short description used for testing.",
            "long_description": "This is a short description used for testing.",
            "points": 20,
            "handgrading_rubric": self.default_handgrading_rubric
        }

        criterion_obj = handgrading_models.Criterion.objects.validate_and_create(
            **criterion_inputs)

        self.assertEqual(criterion_obj.short_description, criterion_inputs["short_description"])
        self.assertEqual(criterion_obj.long_description, criterion_inputs["long_description"])
        self.assertEqual(criterion_obj.points, criterion_inputs["points"])
        self.assertEqual(criterion_obj.handgrading_rubric, criterion_inputs["handgrading_rubric"])


class AnnotationTestCase(UnitTestBase):
    """
    Test cases relating the Annotation Model
    """
    def setUp(self):
        default_rubric_inputs = {
            "points_style": handgrading_models.PointsStyle.start_at_max_and_subtract,
            "max_points": 0,
            "show_grades_and_rubric_to_students": False,
            "handgraders_can_leave_comments": True,
            "handgraders_can_apply_arbitrary_points": True,
            "project": obj_build.build_project()
        }

        self.default_handgrading_rubric = \
            handgrading_models.HandgradingRubric.objects.validate_and_create(
                **default_rubric_inputs)

        self.default_annotation = {
            "short_description": "",
            "long_description": "",
            "points": 0,
            "handgrading_rubric": self.default_handgrading_rubric
        }

    def test_default_initialization(self):
        annotation_obj = handgrading_models.Annotation.objects.validate_and_create(
                                    **self.default_annotation)

        self.assertEqual(annotation_obj.short_description,
                         self.default_annotation["short_description"])
        self.assertEqual(annotation_obj.long_description,
                         self.default_annotation["long_description"])
        self.assertEqual(annotation_obj.points, self.default_annotation["points"])
        self.assertEqual(annotation_obj.handgrading_rubric,
                         self.default_annotation["handgrading_rubric"])

    def test_create_average_case(self):
        annotation_inputs = {
            "short_description": "This is a short description used for testing.",
            "long_description": "This is a long description used for testing.",
            "points": 20,
            "handgrading_rubric": self.default_handgrading_rubric
        }

        annotation_obj = handgrading_models.Annotation.objects.validate_and_create(
            **annotation_inputs)

        self.assertEqual(annotation_obj.short_description, annotation_inputs["short_description"])
        self.assertEqual(annotation_obj.long_description, annotation_inputs["long_description"])
        self.assertEqual(annotation_obj.points, annotation_inputs["points"])


class HandgradingResultTestCases(UnitTestBase):
    """
    Test cases relating the Handgrading Result Model
    """
    def test_default_initialization(self):
        result_inputs = {"submission": obj_build.build_submission()}
        result_obj = handgrading_models.HandgradingResult.objects.validate_and_create(
            **result_inputs)
        self.assertEqual(result_obj.submission, result_inputs["submission"])


class CriterionResultTestCases(UnitTestBase):
    """
    Test cases relating the Criterion Result Model
    """
    def test_create_average_case(self):
        criterion_obj = handgrading_models.Criterion.objects.validate_and_create(
            points=0,
            handgrading_rubric=handgrading_models.HandgradingRubric.objects.validate_and_create(
                points_style=handgrading_models.PointsStyle.start_at_max_and_subtract,
                max_points=0,
                show_grades_and_rubric_to_students=False,
                handgraders_can_leave_comments=True,
                handgraders_can_apply_arbitrary_points=True,
                project=obj_build.build_project()
            )
        )

        result_obj = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=obj_build.build_submission()
        )

        criterion_inputs = {
            "selected": True,
            "criterion": criterion_obj,
            "handgrading_result": result_obj
        }

        criterion_result_obj = handgrading_models.CriterionResult.objects.validate_and_create(
            **criterion_inputs)

        self.assertEqual(criterion_result_obj.selected, criterion_inputs["selected"])
        self.assertEqual(criterion_result_obj.criterion, criterion_inputs["criterion"])
        self.assertEqual(criterion_result_obj.handgrading_result,
                         criterion_inputs["handgrading_result"])


# TODO: Check if Location "first_line" and "last_line" should have min value of 0
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

        self.default_location_obj = handgrading_models.Location.objects.validate_and_create(
            first_line=0,
            last_line=1,
            filename="test.cpp"
        )

        self.default_annotation_obj = handgrading_models.Annotation.objects.validate_and_create(
            short_description="",
            long_description="",
            points=0,
            handgrading_rubric=default_handgrading_rubric
        )

        # TODO: CHECK CLEANUP FILE -> SHOULD FILENAME BE REQUIRED?
        self.default_handgrading_result_obj = \
            handgrading_models.HandgradingResult.objects.validate_and_create(
                submission=obj_build.build_submission(submitted_filenames=["test.cpp"])
            )

        self.default_applied_annotation_inputs = {
            "comment": "",
            "location": self.default_location_obj,
            "annotation": self.default_annotation_obj,
            "handgrading_result": self.default_handgrading_result_obj
        }

    def test_default_initialization(self):
        app_annotation_obj = handgrading_models.AppliedAnnotation.objects.validate_and_create(
            **self.default_applied_annotation_inputs
        )

        self.assertEqual(app_annotation_obj.comment,
                         self.default_applied_annotation_inputs["comment"])
        self.assertEqual(app_annotation_obj.location,
                         self.default_applied_annotation_inputs["location"])
        self.assertEqual(app_annotation_obj.annotation,
                         self.default_applied_annotation_inputs["annotation"])
        self.assertEqual(app_annotation_obj.handgrading_result,
                         self.default_applied_annotation_inputs["handgrading_result"])

    def test_applied_annotation_with_comment(self):
        inputs = {
            "comment": "Testing comment. This can be longer.",
            "location": self.default_location_obj,
            "annotation": self.default_annotation_obj,
            "handgrading_result": self.default_handgrading_result_obj
        }

        app_annotation_obj = handgrading_models.AppliedAnnotation.objects.validate_and_create(
            **inputs
        )

        self.assertEqual(app_annotation_obj.comment, inputs["comment"])
        self.assertEqual(app_annotation_obj.location, inputs["location"])
        self.assertEqual(app_annotation_obj.annotation, inputs["annotation"])
        self.assertEqual(app_annotation_obj.handgrading_result, inputs["handgrading_result"])

    def test_allow_applied_annotation_to_not_have_comments(self):
        annotation_obj = handgrading_models.AppliedAnnotation.objects.validate_and_create(
            location=self.default_location_obj,
            annotation=self.default_annotation_obj,
            handgrading_result=self.default_handgrading_result_obj  # Contains filename "test.cpp"
        )

        self.assertEqual(annotation_obj.comment, None)

    def test_filename_in_location_must_be_in_submitted_files(self):
        """
        Default submission filename is "test.cpp" (see handgrading_obj_builders)
        """

        # Submission in handgrading_result contains filename "test.cpp" (see defaults),
        # but location's filename is set to "WRONG.cpp"

        with self.assertRaises(ValidationError):
            handgrading_models.AppliedAnnotation.objects.validate_and_create(
                location=handgrading_models.Location.objects.validate_and_create(
                    first_line=0,
                    last_line=1,
                    filename="WRONG.cpp"
                ),
                annotation=self.default_annotation_obj,
                handgrading_result=self.default_handgrading_result_obj
            )


class CommentTestCase(UnitTestBase):
    """
    Test cases relating the Comment Model
    """
    # TODO: MODIFY DEFAULT IF FILENAME CAN BE NULL
    # TODO: CAN TEXT BE BLANK IN COMMENT???
    # TODO: DOES COMMENT NEED A CLEAN FUNCTION?
    def test_default_initialization(self):
        comment_inputs = {
            "location": handgrading_models.Location.objects.validate_and_create(
                first_line=0,
                last_line=1,
                filename="test.cpp"
            ),
            "text": "HI",
            "handgrading_result": handgrading_models.HandgradingResult.objects.validate_and_create(
                submission=obj_build.build_submission(submitted_filenames=["test.cpp"])
            )
        }

        comment_obj = handgrading_models.Comment.objects.validate_and_create(**comment_inputs)

        self.assertEqual(comment_obj.location, comment_inputs["location"])
        self.assertEqual(comment_obj.text, comment_inputs["text"])
        self.assertEqual(comment_obj.handgrading_result, comment_inputs["handgrading_result"])

    def test_filename_in_location_must_be_in_submitted_files(self):
        # Submission in handgrading_result contains filename "test.cpp" (see defaults),
        # but location's filename is set to "WRONG.cpp"

        handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=obj_build.build_submission(submitted_filenames=["test.cpp"])
        )

        with self.assertRaises(ValidationError):
            handgrading_models.Comment.objects.validate_and_create(
                location=handgrading_models.Location.objects.validate_and_create(
                    first_line=0,
                    last_line=1,
                    filename="WRONG.cpp"
                ),
                text="hello",
                handgrading_result=handgrading_result
            )


class ArbitraryPointsTestCase(UnitTestBase):
    def test_default_initialization(self):
        arb_points_obj = handgrading_models.ArbitraryPoints.objects.validate_and_create(
            location=handgrading_models.Location.objects.validate_and_create(
                first_line=0,
                last_line=1,
                filename="test.cpp"
            ),
            text="",
            points=0,
            handgrading_result=handgrading_models.HandgradingResult.objects.validate_and_create(
                submission=obj_build.build_submission(submitted_filenames=["test.cpp"])
            )
        )

        self.assertEqual(arb_points_obj.points, 0)

    def test_create_average_case(self):
        arb_points_inputs = {
            "location": handgrading_models.Location.objects.validate_and_create(
                first_line=0,
                last_line=1,
                filename="test.cpp"
            ),
            "text": "Testing text field. This can be longer.",
            "points": 24,
            "handgrading_result": handgrading_models.HandgradingResult.objects.validate_and_create(
                submission=obj_build.build_submission(submitted_filenames=["test.cpp"])
            )
        }

        arb_points_obj = handgrading_models.ArbitraryPoints.objects.validate_and_create(
            **arb_points_inputs)

        self.assertEqual(arb_points_obj.location, arb_points_inputs["location"])
        self.assertEqual(arb_points_obj.text, arb_points_inputs["text"])
        self.assertEqual(arb_points_obj.points, arb_points_inputs["points"])
        self.assertEqual(arb_points_obj.handgrading_result,
                         arb_points_inputs["handgrading_result"])

    def test_filename_in_location_must_be_in_submitted_files(self):
        # Submission in handgrading_result contains filename "test.cpp" (see defaults),
        # but location's filename is set to "WRONG.cpp"

        handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=obj_build.build_submission(submitted_filenames=["test.cpp"])
        )

        with self.assertRaises(ValidationError):
            handgrading_models.ArbitraryPoints.objects.validate_and_create(
                location=handgrading_models.Location.objects.validate_and_create(
                    first_line=0,
                    last_line=1,
                    filename="WRONG.cpp"
                ),
                text="",
                points=0,
                handgrading_result=handgrading_result
            )


# TODO: DO WE WANT LOCATION FILENAME TO HAVE BLANK=TRUE?
class LocationTestCase(UnitTestBase):
    def test_default_initialization(self):
        location_obj = handgrading_models.Location.objects.validate_and_create(
            first_line=0,
            last_line=0,
            filename="stats.cpp"
        )

        self.assertEqual(location_obj.first_line, 100)
        self.assertEqual(location_obj.last_line, 200)
        self.assertEqual(location_obj.filename, "stats.cpp")

    def test_last_line_less_than_first_line(self):
        location_inputs = {
            "first_line": 21,
            "last_line": 20
        }

        with self.assertRaises(ValidationError):
            handgrading_models.Location.objects.validate_and_create(**location_inputs)
