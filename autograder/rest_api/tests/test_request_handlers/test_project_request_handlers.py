from django.core.urlresolvers import reverse

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk


class RetrieveUpdateProjectTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_course_admin_or_semester_staff_get_project(self):
        self.fail()

    def test_enrolled_student_or_other_get_hidden_project_permission_denied(self):
        self.fail()

    def test_enrolled_student_or_other_get_visible_public_project(self):
        self.fail()

    def test_other_get_visible_non_public_project_permission_denied(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_course_admin_edit_some_project_fields(self):
        self.fail()

    def test_course_admin_edit_all_project_fields(self):
        self.fail()

    def test_edit_project_invalid_settings(self):
        self.fail()

    def test_other_edit_project_permission_denied(self):
        self.fail()

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddProjectFileTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_course_admin_or_semester_staff_list_files(self):
        self.fail()

    def test_other_list_files_permission_denied(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_course_admin_add_files_all_success(self):
        self.fail()

    def test_course_admin_add_files_all_failure(self):
        self.fail()

    def test_course_admin_add_files_some_success_some_failure(self):
        self.fail()

    def test_other_add_files_permission_denied(self):
        self.fail()

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class GetUpdateDeleteProjectFileTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_course_admin_or_semester_staff_get_file(self):
        self.fail()

    def test_other_get_file_permission_denied(self):
        self.fail()

    def test_course_admin_edit_file(self):
        self.fail()

    def test_other_edit_file_permission_denied(self):
        self.fail()

    def test_course_admin_delete_file(self):
        self.fail()

    def test_other_delete_file_permission_denied(self):
        self.fail()


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddAutograderTestCaseTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_course_admin_or_semester_staff_list_tests(self):
        self.fail()

    def test_other_list_tests_permission_denied(self):
        self.fail()

    def test_course_admin_add_test(self):
        self.fail()

    def test_other_add_test_permission_denied(self):
        self.fail()

    def test_add_test_invalid_settings(self):
        self.fail()

    def test_add_test_invalid_test_type(self):
        self.fail()

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddStudentTestSuiteTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_course_admin_or_semester_staff_list_suites(self):
        self.fail()

    def test_other_list_suites_permission_denied(self):
        self.fail()

    def test_course_admin_add_suite(self):
        self.fail()

    def test_other_add_suite_permission_denied(self):
        self.fail()

    def test_add_suite_invalid_settings(self):
        self.fail()

    def test_add_suite_invalid_suite_type(self):
        self.fail()

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddSubmissionGroupTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_course_admin_or_semester_staff_list_first_page(self):
        self.fail()

    def test_course_admin_or_semester_staff_list_middle_page(self):
        self.fail()

    def test_course_admin_or_semester_staff_list_last_page(self):
        self.fail()

    def test_course_admin_or_semester_staff_list_default_page(self):
        self.fail()

    def test_enrolled_student_in_submission_group_list_groups(self):
        self.fail()

    def test_non_enrolled_student_public_project_list_groups(self):
        self.fail()

    def test_hidden_project_permission_denied(self):
        self.fail()

    def test_non_enrolled_student_private_project_permission_denied(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_course_admin_create_group_that_has_self_and_others(self):
        self.fail()

    def test_course_admin_create_group_of_others(self):
        self.fail()

    def test_course_admin_create_group_of_others_override_max_size(self):
        self.fail()

    def test_course_admin_create_group_of_others_override_min_size(self):
        self.fail()

    def test_course_admin_create_group_error_group_size_zero(self):
        self.fail()

    # def

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddSubmissionGroupRequestTestCase(TemporaryFilesystemTestCase):
    pass
