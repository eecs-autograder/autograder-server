from django.core.urlresolvers import reverse

import autograder.core.models as ag_models

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


_ag_test_kwargs = {
    'name': 'testy',
    'type_str': 'interpreted_test_case',
    'interpreter': 'python3',
    'entry_point_filename': 'spammy.py'
}


def build_ag_test(project):
    return ag_models.AutograderTestCaseFactory.validate_and_create(
        project=project, **_ag_test_kwargs)


def ag_test_url(ag_test):
    return reverse('ag-test-detail', kwargs={'pk': ag_test.pk})


class AGTestCaseRetrieveTestCase(test_data.Client,
                                 test_data.Project,
                                 test_impls.GetObjectTest,
                                 UnitTestBase):
    def test_admin_get_ag_test(self):
        for project in self.all_projects:
            ag_test = build_ag_test(project)
            self.do_get_object_test(self.client, self.admin,
                                    ag_test_url(ag_test), ag_test.to_dict())

    def test_staff_get_ag_test(self):
        for project in self.all_projects:
            ag_test = build_ag_test(project)
            self.do_get_object_test(self.client, self.staff,
                                    ag_test_url(ag_test), ag_test.to_dict())

    def test_enrolled_get_ag_test(self):
        for project in self.all_projects:
            ag_test = build_ag_test(project)
            self.do_permission_denied_get_test(self.client, self.enrolled,
                                               ag_test_url(ag_test))

    def test_other_get_ag_test(self):
        for project in self.all_projects:
            ag_test = build_ag_test(project)
            self.do_permission_denied_get_test(self.client, self.nobody,
                                               ag_test_url(ag_test))


class AGTestCaseUpdateTestCase(test_data.Client,
                               test_data.Project,
                               test_impls.UpdateObjectTest,
                               UnitTestBase):
    def setUp(self):
        super().setUp()
        self.updated_kwargs = {
            'entry_point_filename': (_ag_test_kwargs['entry_point_filename'] +
                                     'waaaluigi'),
            'interpreter_flags': ['spam', 'egg', 'sausage'],
            'command_line_arguments': ['waaluigi', 'waaario']
        }

    def test_admin_update_ag_test(self):
        for project in self.all_projects:
            ag_test = build_ag_test(project)
            self.do_patch_object_test(ag_test, self.client, self.admin,
                                      ag_test_url(ag_test), self.updated_kwargs)

    def test_admin_update_ag_test_invalid_change_type(self):
        invalid_kwargs = {
            'type_str': 'compiled_and_run_test_case',  # Can't change test type
        }
        for project in self.all_projects:
            ag_test = build_ag_test(project)
            response = self.do_patch_object_invalid_args_test(
                ag_test, self.client, self.admin, ag_test_url(ag_test),
                invalid_kwargs)
            for key in invalid_kwargs:
                self.assertIn(key, response.data['non_editable_fields'])

    def test_admin_update_ag_test_invalid_args(self):
        invalid_kwargs = {
            'entry_point_filename': ''
        }
        for project in self.all_projects:
            ag_test = build_ag_test(project)
            response = self.do_patch_object_invalid_args_test(
                ag_test, self.client, self.admin, ag_test_url(ag_test),
                invalid_kwargs)
            for key in invalid_kwargs:
                self.assertIn(key, response.data)

    def test_other_update_ag_test_permission_denied(self):
        ag_test = build_ag_test(self.visible_public_project)
        url = ag_test_url(ag_test)
        for user in self.staff, self.enrolled, self.nobody:
            self.do_patch_object_permission_denied_test(
                ag_test, self.client, user, url, self.updated_kwargs)


class AGTestCaseDeleteTestCase(test_data.Client,
                               test_data.Project,
                               test_impls.DestroyObjectTest,
                               UnitTestBase):
    def test_admin_delete_ag_test(self):
        for project in self.all_projects:
            ag_test = build_ag_test(project)
            self.do_delete_object_test(
                ag_test, self.client, self.admin, ag_test_url(ag_test))

    def test_other_delete_ag_test_permission_denied(self):
        ag_test = build_ag_test(self.visible_public_project)
        url = ag_test_url(ag_test)
        for user in self.staff, self.enrolled, self.nobody:
            self.do_delete_object_permission_denied_test(
                ag_test, self.client, user, url)
