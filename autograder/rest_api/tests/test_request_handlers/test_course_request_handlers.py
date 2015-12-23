from django.core.urlresolvers import reverse

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
from .utilities import MockClient, json_load_bytes, sorted_by_pk


class CourseRetrieveUpdateTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

    def test_admin_get_course_all_information_returned(self):
        self.fail()

    def test_other_get_course_minimal_information_returned(self):
        self.fail()

    def test_get_course_not_found(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_admin_patch_course(self):
        self.fail()

    def test_other_patch_course_permission_denied(self):
        self.fail()

    def test_patch_course_not_found(self):
        self.fail()


class CourseListCreateTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super.setUp()

    def test_superuser_get_course_list(self):
        self.fail()

    def test_other_get_course_list_permission_denied(self):
        self.fail()

    # -------------------------------------------------------------------------

    def test_superuser_create_course(self):
        self.fail()

    def test_other_create_course_permission_denied(self):
        self.fail()

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class CourseAdministratorsListAddRemoveTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super.setUp()

    def test_superuser_or_admin_list_administrators(self):
        self.fail()

    def test_other_list_administrators_permission_denied(self):
        self.fail()

    def test_superuser_or_admin_add_administrators(self):
        self.fail()

    def test_other_add_administrators_permission_denied(self):
        self.fail()

    def test_superuser_or_admin_remove_administrators(self):
        self.fail()

    def test_other_remove_administrators_permission_denied(self):
        self.fail()

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class SemesterListAddTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super.setUp()

    def test_course_admin_list_semesters(self):
        self.fail()

    def test_other_list_semesters_permission_denied(self):
        self.fail()

    def test_course_admin_create_semester(self):
        self.fail()

    def test_other_create_semester_permission_denied(self):
        self.fail()

    def test_bad_request_semester_already_exists(self):
        self.fail()
