"""Criterion Result tests"""

import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase
import datetime


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
            submission_group=submission.submission_group,
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

    def test_criterion_results_ordering(self):
        for i in range(10):
            self.criterion_inputs["criterion"] = (
                handgrading_models.Criterion.objects.validate_and_create(
                    points=0,
                    handgrading_rubric=self.default_handgrading_rubric))
            handgrading_models.CriterionResult.objects.validate_and_create(**self.criterion_inputs)

        all_criterion_results = handgrading_models.Criterion.objects.all()

        self.assertTrue(all_criterion_results.ordered)
        last_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=10)

        # Check that queryset is ordered chronologically by 'created' field of corresponding
        # criterion item
        for criterion_result in all_criterion_results:
            self.assertLess(last_date, criterion_result.criterion.created)
            last_date = criterion_result.criterion.created

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
