from rest_framework import status

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut
import autograder.rest_api.tests.test_views.common_generic_data as test_data


class _AGTestsSetUp(test_data.Client, test_data.Project):
    pass


class ListAGTestsTestCase(_AGTestsSetUp, TemporaryFilesystemTestCase):
    def test_admin_list_ag_tests(self):
        self.fail()

    def test_staff_list_ag_tests(self):
        self.fail()

    def test_enrolled_list_ag_tests(self):
        self.fail()

    def test_other_list_ag_tests(self):
        self.fail()

    def do_list_ag_tests_test(self, user, project):
        pass
