import itertools

from django.urls import reverse

import autograder.core.models as ag_models

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls


base_pattern_kwargs = {
    'pattern': 'spaaaaaam',
    'min_num_matches': 1,
    'max_num_matches': 4
}


def build_pattern(project):
    return ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
        project=project, **base_pattern_kwargs)


def pattern_url(pattern_obj):
    return reverse('expected-pattern-detail', kwargs={'pk': pattern_obj.pk})


class RetrieveExpectedPatternTestCase(test_data.Client,
                                      test_data.Project,
                                      test_impls.GetObjectTest,
                                      UnitTestBase):
    def test_admin_get_pattern(self):
        for project in self.all_projects:
            pattern = build_pattern(project)
            self.do_get_object_test(self.client, self.admin,
                                    pattern_url(pattern), pattern.to_dict())

    def test_staff_get_pattern(self):
        for project in self.all_projects:
            pattern = build_pattern(project)
            self.do_get_object_test(self.client, self.staff,
                                    pattern_url(pattern), pattern.to_dict())

    def test_enrolled_get_pattern(self):
        for project in self.visible_projects:
            pattern = build_pattern(project)
            self.do_get_object_test(self.client, self.enrolled,
                                    pattern_url(pattern), pattern.to_dict())

        for project in self.hidden_projects:
            pattern = build_pattern(project)
            self.do_permission_denied_get_test(self.client, self.enrolled,
                                               pattern_url(pattern))

    def test_other_get_pattern(self):
        visible_pattern = build_pattern(self.visible_public_project)
        self.do_get_object_test(self.client, self.nobody,
                                pattern_url(visible_pattern),
                                visible_pattern.to_dict())

        for project in itertools.chain([self.visible_private_project],
                                       self.hidden_projects):
            hidden_pattern = build_pattern(project)
            self.do_permission_denied_get_test(self.client, self.nobody,
                                               pattern_url(hidden_pattern))


class UpdateExpectedPatternTestCase(test_data.Client,
                                    test_data.Project,
                                    test_impls.UpdateObjectTest,
                                    UnitTestBase):
    @property
    def valid_args(self):
        return {
            'pattern': 'waaaaa',
            'max_num_matches': base_pattern_kwargs['max_num_matches'] + 2
        }

    def test_admin_patch_pattern(self):
        for project in self.all_projects:
            pattern = build_pattern(project)
            self.do_patch_object_test(pattern, self.client, self.admin,
                                      pattern_url(pattern), self.valid_args)

    def test_admin_put_pattern(self):
        for project in self.all_projects:
            pattern = build_pattern(project)
            self.do_put_object_test(pattern, self.client, self.admin,
                                    pattern_url(pattern), self.valid_args)

    def test_admin_update_pattern_invalid_args(self):
        args = {
            'min_num_matches': 3,
            'max_num_matches': 1
        }
        pattern = build_pattern(self.visible_public_project)
        self.do_patch_object_invalid_args_test(
            pattern, self.client, self.admin, pattern_url(pattern), args)

        self.do_put_object_invalid_args_test(
            pattern, self.client, self.admin, pattern_url(pattern), args)

    def test_other_update_pattern_permission_denied(self):
        args = {
            'pattern': 'kjahdfkjhasdf'
        }
        pattern = build_pattern(self.visible_public_project)
        url = pattern_url(pattern)
        for user in self.staff, self.enrolled, self.nobody:
            self.do_patch_object_permission_denied_test(
                pattern, self.client, user, url, args)
            self.do_put_object_permission_denied_test(
                pattern, self.client, user, url, args)


class DeleteExpectedPatternTestCase(test_data.Client,
                                    test_data.Project,
                                    test_impls.DestroyObjectTest,
                                    UnitTestBase):
    def test_admin_delete_pattern(self):
        for project in self.all_projects:
            pattern = build_pattern(project)
            self.do_delete_object_test(
                pattern, self.client, self.admin, pattern_url(pattern))

    def test_other_delete_pattern_permission_denied(self):
        pattern = build_pattern(self.visible_public_project)
        url = pattern_url(pattern)
        for user in self.staff, self.enrolled, self.nobody:
            self.do_delete_object_permission_denied_test(
                pattern, self.client, user, url)
