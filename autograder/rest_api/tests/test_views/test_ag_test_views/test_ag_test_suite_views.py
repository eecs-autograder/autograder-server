from django.core.urlresolvers import reverse

from rest_framework import status
from rest_framework.test import APIClient

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class ListAGTestSuitesTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.suite1 = obj_build.make_ag_test_suite()
        self.project = self.suite1.project
        self.suite2 = obj_build.make_ag_test_suite(self.project)
        self.client = APIClient()
        self.url = reverse('project-ag-test-suites-list', kwargs={'project_pk': self.project.pk})

    def test_staff_valid_list_suites(self):
        [staff] = obj_build.make_staff_users(self.project.course, 1)
        self.client.force_authenticate(staff)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertSequenceEqual([self.suite1.to_dict(), self.suite2.to_dict()], response.data)

    def test_non_staff_list_suites_permission_denied(self):
        [enrolled] = obj_build.make_enrolled_users(self.project.course, 1)
        self.client.force_authenticate(enrolled)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class CreateAGTestSuiteTestCase(UnitTestBase):
    def test_admin_valid_create(self):
        self.fail()

    def test_non_admin_create_permission_denied(self):
        self.fail()


class GetAGTestSuiteTestCase(UnitTestBase):
    def test_admin_or_staff_valid_get(self):
        self.fail()

    def test_non_staff_get_permission_denied(self):
        self.fail()


class UpdateAGTestSuiteTestCase(UnitTestBase):
    def test_admin_valid_update(self):
        self.fail()

    def test_non_admin_update_permission_denied(self):
        self.fail()

    def test_admin_update_bad_values(self):
        self.fail()


class DeleteAGTestSuiteTestCase(UnitTestBase):
    def test_admin_valid_delete(self):
        self.fail()

    def test_non_admin_delete_permission_denied(self):
        self.fail()
