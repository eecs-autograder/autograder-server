import itertools

from django.core.urlresolvers import reverse

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk


class GetStudentTestSuiteResultTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_student_get_own_visible_result(self):
        self.fail()

    def test_student_get_own_hidden_result_permission_denied(self):
        self.fail()

    def test_student_get_other_student_result_permission_denied(self):
        self.fail()

    def test_course_admin_or_semester_staff_get_own_visible_result(self):
        self.fail()

    def test_course_admin_or_semester_staff_get_own_hidden_result(self):
        self.fail()

    def test_course_admin_or_semester_staff_get_student_visible_result(self):
        # should get max feedback on result
        self.fail()

    def test_course_admin_or_semester_staff_get_student_hidden_result(self):
        # should get max feedback on result
        self.fail()
