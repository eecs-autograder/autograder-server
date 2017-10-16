"""Handgrading Result tests"""

import autograder.utils.testing.model_obj_builders as obj_build
import autograder.handgrading.models as handgrading_models
from autograder.utils.testing import UnitTestBase


class HandgradingResultTestCases(UnitTestBase):
    """
    Test cases relating the Handgrading Result Model
    """
    def test_default_initialization(self):
        result_inputs = {"submission": obj_build.build_submission()}
        result_obj = handgrading_models.HandgradingResult.objects.validate_and_create(
            **result_inputs)
        self.assertEqual(result_obj.submission, result_inputs["submission"])
