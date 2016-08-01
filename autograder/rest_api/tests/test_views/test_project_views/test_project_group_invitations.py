import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class _InvitationsSetUp(test_data.Client, test_data.Project, test_data.Group):
    pass


class ListGroupInvitationsTestCase(_InvitationsSetUp,
                                   test_impls.ListObjectsTest,
                                   test_impls.PermissionDeniedGetTest,
                                   UnitTestBase):
    def test_admin_list_invitations(self):
        for project in self.all_projects:
            self.do_list_objects_test(
                self.client, self.admin, self.get_invitations_url(project),
                self.build_invitations(project))

    def test_staff_list_invitations(self):
        for project in self.all_projects:
            self.do_list_objects_test(
                self.client, self.staff, self.get_invitations_url(project),
                self.build_invitations(project))

    def test_enrolled_list_invitations(self):
        for project in self.all_projects:
            self.do_permission_denied_get_test(
                self.client, self.enrolled, self.get_invitations_url(project))

    def test_other_list_invitations(self):
        for project in self.all_projects:
            self.do_permission_denied_get_test(
                self.client, self.nobody, self.get_invitations_url(project))

    def build_invitations(self, project):
        project.validate_and_update(max_group_size=3)
        first = ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            self.admin, [self.staff], project=project)
        second = ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            self.staff, [self.admin], project=project)
        return ag_serializers.SubmissionGroupInvitationSerializer(
            [first, second], many=True).data


class CreateInvitationTestCase(_InvitationsSetUp,
                               test_impls.CreateObjectTest,
                               test_impls.CreateObjectInvalidArgsTest,
                               test_impls.PermissionDeniedCreateTest,
                               UnitTestBase):
    def test_admin_create_invitation(self):
        self.project.validate_and_update(max_group_size=3)
        args = {'invited_usernames': [self.staff.username]}
        self.do_create_object_test(
            self.project.submission_group_invitations, self.client,
            self.admin, self.get_invitations_url(self.project), args)

    def test_staff_create_invitation(self):
        self.project.validate_and_update(max_group_size=3)
        args = {'invited_usernames': [self.admin.username]}
        self.do_create_object_test(
            self.project.submission_group_invitations, self.client,
            self.staff, self.get_invitations_url(self.project), args)

    def test_enrolled_create_invitation(self):
        self.visible_private_project.validate_and_update(max_group_size=3)
        other_enrolled = self.clone_user(self.enrolled)
        args = {'invited_usernames': [other_enrolled.username]}
        self.do_create_object_test(
            self.visible_private_project.submission_group_invitations,
            self.client, self.enrolled,
            self.get_invitations_url(self.visible_private_project),
            args)

    def test_other_create_invitation(self):
        self.visible_public_project.validate_and_update(max_group_size=3)
        other_nobody = obj_build.create_dummy_user()
        args = {'invited_usernames': [other_nobody.username, 'steve']}
        self.do_create_object_test(
            self.visible_public_project.submission_group_invitations,
            self.client, self.nobody,
            self.get_invitations_url(self.visible_public_project), args)

    def test_invalid_create_invitation_enrollement_mismatch(self):
        self.visible_public_project.validate_and_update(max_group_size=3)
        args = {'invited_usernames': [self.nobody.username]}
        response = self.do_invalid_create_object_test(
            self.visible_public_project.submission_group_invitations,
            self.client, self.enrolled,
            self.get_invitations_url(self.visible_public_project), args)
        print(response.data)

    def test_invalid_create_invitation_group_too_big(self):
        args = {'invited_usernames': ['steve']}
        response = self.do_invalid_create_object_test(
            self.visible_public_project.submission_group_invitations,
            self.client, self.nobody,
            self.get_invitations_url(self.visible_public_project), args)
        print(response.data)

    def test_enrolled_create_invitation_hidden_project_permission_denied(self):
        other_enrolled = self.clone_user(self.enrolled)
        args = {'invited_usernames': [other_enrolled.username]}
        for project in self.hidden_projects:
            project.validate_and_update(max_group_size=3)
            self.do_permission_denied_create_test(
                project.submission_group_invitations, self.client,
                self.enrolled, self.get_invitations_url(project), args)

    def test_nobody_create_invitation_private_or_hidden_project_permission_denied(self):
        other_nobody = obj_build.create_dummy_user()
        args = {'invited_usernames': [other_nobody.username]}
        for project in (self.visible_private_project,
                        self.hidden_public_project,
                        self.hidden_private_project):
            self.do_permission_denied_create_test(
                project.submission_group_invitations, self.client,
                self.nobody, self.get_invitations_url(project), args)

    def test_registration_disabled_permission_denied_for_enrolled(self):
        self.visible_public_project.validate_and_update(
            max_group_size=3, disallow_group_registration=True)
        other_enrolled = self.clone_user(self.enrolled)
        data = {'invited_usernames': [other_enrolled.username]}
        self.do_permission_denied_create_test(
            ag_models.SubmissionGroupInvitation.objects,
            self.client, self.enrolled,
            self.get_invitations_url(self.visible_public_project), data)

    def test_registration_disabled_permission_denied_for_non_enrolled(self):
        self.visible_public_project.validate_and_update(
            max_group_size=3, disallow_group_registration=True)
        data = {'invited_usernames': [obj_build.create_dummy_user().username]}
        self.do_permission_denied_create_test(
            ag_models.SubmissionGroupInvitation.objects,
            self.client, self.nobody,
            self.get_invitations_url(self.visible_public_project), data)

    def test_registration_disabled_staff_can_still_send_invitations(self):
        self.project.validate_and_update(
            max_group_size=3, disallow_group_registration=True)
        args = {'invited_usernames': [self.staff.username]}
        self.do_create_object_test(
            self.project.submission_group_invitations, self.client,
            self.admin, self.get_invitations_url(self.project), args)

        args['invited_usernames'] = [self.admin.username]
        self.do_create_object_test(
            self.project.submission_group_invitations, self.client,
            self.staff, self.get_invitations_url(self.project), args)
