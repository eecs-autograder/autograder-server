from urllib.parse import urlencode

from django.core.urlresolvers import reverse
from django.utils import timezone

import autograder.core.models as ag_models
from autograder.core.models.autograder_test_case.feedback_config import (
    FeedbackConfig, ReturnCodeFdbkLevel, StdoutFdbkLevel, StderrFdbkLevel,
    CompilationFdbkLevel, ValgrindFdbkLevel)

import autograder.core.tests.dummy_object_utils as obj_ut
from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class ListResultsTestCase:
    def test_staff_list_own_all_results_shown(self):
        self.fail()

    def test_enrolled_list_own_results(self):
        self.fail()

    def test_non_enrolled_list_own_results(self):
        self.fail()


class UltimateListResultsTestCase:
    def test_admin_or_staff_list_own_ultimate_all_results_shown(self):
        self.fail()

    def test_enrolled_list_own_results_ultimate_submission(self):
        self.fail()

    def test_non_enrolled_list_own_results_ultimate_submission(self):
        self.fail()

    def test_list_ultimate_results_submission_not_qualifying_normal_list(self):
        self.fail()


class PastLimitListResultsTestCase:
    def test_admin_or_staff_list_own_past_limit_all_results_shown(self):
        self.fail()

    def test_enrolled_list_own_results_past_limit(self):
        self.fail()

    def test_non_enrolled_list_own_results_past_limit(self):
        self.fail()


class StaffViewerListResultsTestCase:
    def test_admin_or_staff_list_other_all_results_shown(self):
        self.fail()
