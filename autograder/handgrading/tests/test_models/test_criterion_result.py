"""Criterion Result tests"""

import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase


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
