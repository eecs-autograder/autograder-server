# import itertools
# import random

from django.core import exceptions

# from django.core.files.uploadedfile import SimpleUploadedFile

import autograder.core.models as ag_models
import autograder.core.models.autograder_test_case.feedback_config as fdbk_lvls

import autograder.core.shared.global_constants as gc

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .models import _DummyAutograderTestCase


class FdbkConfigUsedTestCase():
    def test_admin_or_staff_view_own_result(self):
        self.fail()

    def test_admin_or_staff_view_all_others_result(self):
        self.fail()

    def test_admin_or_staff_view_other_with_student_view(self):
        self.fail()

    def test_student_view_result_with_normal_fdbk(self):
        self.fail()

    def test_student_view_result_past_submission_limit(self):
        self.fail()

    def test_student_view_result_as_ultimate_submission(self):
        self.fail()
