from django.core.urlresolvers import reverse

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk


class RetrieveUpdateSemesterTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_course_admin_or_semester_staff_get_semester(self):
        self.fail()

    def test_enrolled_student_get_semester(self):
        self.fail()

    def test_other_get_semester_permission_denied(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_course_admin_patch_semester(self):
        self.fail()

    def test_other_patch_semester_permission_denied(self):
        self.fail()

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddRemoveSemesterStaffTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_course_admin_list_staff(self):
        self.fail()

    def test_other_list_staff_permission_denied(self):
        self.fail()

    def test_course_admin_add_staff(self):
        self.fail()

    def test_other_add_staff_permission_denied(self):
        self.fail()

    def test_course_admin_remove_staff(self):
        self.fail()

    def test_other_remove_staff_permission_denied(self):
        self.fail()

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddUpdateRemoveEnrolledStudentsTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_list_students_default(self):
        self.fail()

    def test_list_students_first_page_custom_page_size(self):
        self.fail()

    def test_list_students_middle_page_custom_page_size(self):
        self.fail()

    def test_list_students_last_page_custom_page_size(self):
        self.fail()

    def test_non_enrolled_list_students_permission_denied(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_admin_add_enrolled_students(self):
        self.fail()

    def test_other_add_enrolled_students_permission_denied(self):
        self.fail()

    def test_admin_update_enrolled_students(self):
        self.fail()

    def test_other_update_enrolled_students_permission_denied(self):
        self.fail()

    def test_admin_remove_enrolled_students(self):
        self.fail()

    def test_other_remove_enrolled_students_permission_denied(self):
        self.fail()

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ProjectListAddTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_admin_or_staff_list_projects(self):
        self.fail()

    def test_enrolled_student_list_projects_visible_only(self):
        self.fail()

    def test_other_list_projects_permission_denied(self):
        self.fail()

    def test_course_admin_add_project(self):
        self.fail()

    def test_other_add_project_permission_denied(self):
        self.fail()
