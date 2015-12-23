import itertools

from django.core.urlresolvers import reverse

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk


class GetUpdateDeleteStudentTestSuiteTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_course_admin_or_semester_staff_get_suite(self):
        self.fail()

    def test_other_get_suite_permission_denied(self):
        self.fail()

    def test_course_admin_get_suite_not_found(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_course_admin_edit_suite(self):
        self.fail()

    def test_other_edit_suite_permission_denied(self):
        self.fail()

    def test_course_admin_edit_suite_invalid_settings(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_course_admin_delete_suite(self):
        self.fail()

    def test_other_delete_suite_permission_denied(self):
        self.fail()
