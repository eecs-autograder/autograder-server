from django.utils import timezone

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class RetrieveGroupTestCase(test_data.Client,
                            test_data.Project,
                            test_data.Group,
                            test_impls.GetObjectTest,
                            TemporaryFilesystemTestCase):
    def test_admin_or_staff_get_group(self):
        for project in self.all_projects:
            for group in self.at_least_enrolled_groups(project):
                for user in self.admin, self.staff:
                    self.do_get_object_test(
                        self.client, user, self.group_url(group),
                        group.to_dict())

        for project in self.public_projects:
            group = self.non_enrolled_group(project)
            for user in self.admin, self.staff:
                self.do_get_object_test(
                    self.client, user, self.group_url(group), group.to_dict())

    def test_enrolled_get_group(self):
        for project in self.visible_projects:
            group = self.enrolled_group(project)
            for user in group.members.all():
                self.do_get_object_test(
                    self.client, user, self.group_url(group), group.to_dict())

    def test_non_enrolled_get_group(self):
        group = self.non_enrolled_group(self.visible_public_project)
        for user in group.members.all():
            self.do_get_object_test(
                self.client, user, self.group_url(group), group.to_dict())

    def test_non_member_view_group_permission_denied(self):
        group = self.enrolled_group(self.visible_public_project)
        non_member = self.clone_user(self.enrolled)
        for user in non_member, self.nobody:
            self.do_permission_denied_get_test(
                self.client, user, self.group_url(group))

    def test_enrolled_view_group_project_hidden_permission_denied(self):
        for project in self.hidden_projects:
            group = self.enrolled_group(project)
            self.do_permission_denied_get_test(
                self.client, self.enrolled, self.group_url(group))

    def test_non_enrolled_view_group_project_hidden_permission_denied(self):
        group = self.non_enrolled_group(self.hidden_public_project)
        self.do_permission_denied_get_test(
            self.client, self.nobody, self.group_url(group))

    def test_non_enrolled_view_group_project_private_permission_denied(self):
        group = self.non_enrolled_group(self.visible_public_project)
        self.visible_public_project.validate_and_update(
            allow_submissions_from_non_enrolled_students=False)
        self.do_permission_denied_get_test(
            self.client, self.nobody, self.group_url(group))


class UpdateGroupTestCase(test_data.Client,
                          test_data.Project,
                          test_data.Group,
                          test_impls.UpdateObjectTest,
                          TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.new_due_date = timezone.now().replace(microsecond=0)

    def get_names(self, users):
        return [user.username for user in users]

    def test_admin_update_admin_and_staff_group_members(self):
        for project in self.all_projects:
            group = self.staff_group(project)
            new_members = (list(group.members.all())[:-1] +
                           [self.clone_user(self.admin)])
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'member_names': self.get_names(new_members)})

    def test_admin_update_enrolled_group_members(self):
        for project in self.all_projects:
            group = self.enrolled_group(project)
            new_members = (list(group.members.all())[:-1] +
                           [self.clone_user(self.enrolled)])
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'member_names': self.get_names(new_members)})

    def test_admin_update_non_enrolled_group_members(self):
        for project in self.public_projects:
            group = self.non_enrolled_group(project)
            new_members = self.get_names(
                list(group.members.all())[:-1]) + ['stove']
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'member_names': new_members})

    def test_admin_update_group_override_size(self):
        for project in self.all_projects:
            group = self.enrolled_group(project)
            new_members = (list(group.members.all()) +
                           [self.clone_user(self.enrolled)])
            self.assertGreater(len(new_members), project.max_group_size)
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'member_names': self.get_names(new_members)})

    def test_admin_update_group_extension(self):
        for project in self.all_projects:
            group = self.enrolled_group(project)
            # give and revoke extension
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'extended_due_date': self.new_due_date})
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'extended_due_date': None})

        for project in self.public_projects:
            group = self.non_enrolled_group(project)
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'extended_due_date': self.new_due_date})
            self.do_patch_object_test(
                group, self.client, self.admin, self.group_url(group),
                {'extended_due_date': None})

    def test_admin_update_group_invalid_members(self):
        for project in self.all_projects:
            group = self.enrolled_group(project)
            new_members = self.get_names(
                list(group.members.all())[:-1]) + ['stove']
            response = self.do_patch_object_invalid_args_test(
                group, self.client, self.admin, self.group_url(group),
                {'member_names': new_members})
            self.assertIn('members', response.data)

    def test_admin_update_group_bad_date(self):
        group = self.enrolled_group(self.visible_public_project)
        response = self.do_patch_object_invalid_args_test(
            group, self.client, self.admin, self.group_url(group),
            {'extended_due_date': 'not a date'})
        self.assertIn('extended_due_date', response.data)

    def test_other_update_group_permission_denied(self):
        for group in (self.staff_group(self.visible_public_project),
                      self.enrolled_group(self.visible_public_project),
                      self.non_enrolled_group(self.visible_public_project)):
            for user in self.staff, self.enrolled, self.nobody:
                self.do_patch_object_permission_denied_test(
                    group, self.client, user, self.group_url(group),
                    {'extended_due_date': self.new_due_date})
