"""Criterion Result tests"""

import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase


class CriterionResultTestCases(UnitTestBase):
    """
    Test cases relating the Criterion Result Model
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

        self.criterion_obj = handgrading_models.Criterion.objects.validate_and_create(
            points=0,
            handgrading_rubric=self.default_handgrading_rubric
        )

        submission = obj_build.build_submission()

        self.result_obj = handgrading_models.HandgradingResult.objects.validate_and_create(
            submission=submission,
            submission_group=submission.group,
            handgrading_rubric=self.default_handgrading_rubric
        )

        self.criterion_inputs = {
            "selected": True,
            "criterion": self.criterion_obj,
            "handgrading_result": self.result_obj
        }

    def test_create_average_case(self):
        criterion_result_obj = handgrading_models.CriterionResult.objects.validate_and_create(
            **self.criterion_inputs)

        self.assertEqual(criterion_result_obj.selected, self.criterion_inputs["selected"])
        self.assertEqual(criterion_result_obj.criterion, self.criterion_inputs["criterion"])
        self.assertEqual(criterion_result_obj.handgrading_result,
                         self.criterion_inputs["handgrading_result"])

    def test_serializable_fields(self):
        expected_fields = [
            'pk',
            'last_modified',

            'selected',
            'criterion',
            'handgrading_result',
        ]

        criterion_res_obj = handgrading_models.CriterionResult.objects.validate_and_create(
            **self.criterion_inputs
        )

        criterion_res_dict = criterion_res_obj.to_dict()
        self.assertCountEqual(expected_fields, criterion_res_dict.keys())

        for non_editable in ['pk', 'last_modified', 'criterion', 'handgrading_result']:
            criterion_res_dict.pop(non_editable)

        criterion_res_obj.validate_and_update(**criterion_res_dict)

    def test_serialize_related(self):
        expected_fields = [
            'pk',
            'last_modified',

            'selected',
            'criterion',
            'handgrading_result',
        ]

        criterion_res_obj = handgrading_models.CriterionResult.objects.validate_and_create(
            **self.criterion_inputs
        )

        criterion_res_dict = criterion_res_obj.to_dict()
        self.assertCountEqual(expected_fields, criterion_res_dict.keys())

        self.assertIsInstance(criterion_res_dict["criterion"], object)
        self.assertCountEqual(criterion_res_dict["criterion"].keys(),
                              self.criterion_obj.to_dict().keys())

    def test_criterion_result_ordering(self):
        cr1 = handgrading_models.CriterionResult.objects.validate_and_create(
                **self.criterion_inputs)

        # Create a new criterion item for second criterion result, since two criterion results
        #   in one handgrading result should not share the same criterion
        cr2 = handgrading_models.CriterionResult.objects.validate_and_create(
                selected=True,
                criterion=handgrading_models.Criterion.objects.validate_and_create(
                    points=0,
                    handgrading_rubric=self.default_handgrading_rubric),
                handgrading_result=self.result_obj)

        self.assertCountEqual([cr1.criterion.pk, cr2.criterion.pk],
                              self.default_handgrading_rubric.get_criterion_order())

        self.default_handgrading_rubric.set_criterion_order([cr1.criterion.pk, cr2.criterion.pk])
        self.assertSequenceEqual([cr1.criterion.pk, cr2.criterion.pk],
                                 self.default_handgrading_rubric.get_criterion_order())
        self.assertSequenceEqual([cr1, cr2],
                                 handgrading_models.CriterionResult.objects.all())

        self.default_handgrading_rubric.set_criterion_order([cr2.criterion.pk, cr1.criterion.pk])
        self.assertSequenceEqual([cr2.criterion.pk, cr1.criterion.pk],
                                 self.default_handgrading_rubric.get_criterion_order())
        self.assertSequenceEqual([cr2, cr1],
                                 handgrading_models.CriterionResult.objects.all())
