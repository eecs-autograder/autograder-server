from django.urls import reverse
from rest_framework import status

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase


class _InvitationsSetUp(test_data.Client, test_data.Project, test_data.Group):
    pass


# TODO: remove common_generic_data module


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

    def test_handgrader_list_invitations(self):
        for project in self.all_projects:
            self.do_permission_denied_get_test(
                self.client, self.handgrader, self.get_invitations_url(project))

    def test_other_list_invitations(self):
        for project in self.all_projects:
            self.do_permission_denied_get_test(
                self.client, self.nobody, self.get_invitations_url(project))

    def build_invitations(self, project):
        project.validate_and_update(max_group_size=3)
        first = ag_models.GroupInvitation.objects.validate_and_create(
            self.admin, [self.staff], project=project)
        second = ag_models.GroupInvitation.objects.validate_and_create(
            self.clone_user(self.staff), [self.clone_user(self.admin)],
            project=project)
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
            self.project.group_invitations, self.client,
            self.admin, self.get_invitations_url(self.project), args)

    def test_staff_create_invitation(self):
        self.project.validate_and_update(max_group_size=3)
        args = {'invited_usernames': [self.admin.username]}
        self.do_create_object_test(
            self.project.group_invitations, self.client,
            self.staff, self.get_invitations_url(self.project), args)

    def test_enrolled_create_invitation(self):
        self.visible_private_project.validate_and_update(max_group_size=3)
        other_enrolled = self.clone_user(self.enrolled)
        args = {'invited_usernames': [other_enrolled.username]}
        self.do_create_object_test(
            self.visible_private_project.group_invitations,
            self.client, self.enrolled,
            self.get_invitations_url(self.visible_private_project),
            args)

    def test_handgrader_create_invitation_permission_denied(self):
        args = {'invited_usernames': ["some_user"]}
        for project in self.all_projects:
            project.validate_and_update(max_group_size=3)
            self.do_permission_denied_create_test(
                project.group_invitations, self.client,
                self.handgrader, self.get_invitations_url(project), args)

    def test_handgrader_also_enrolled_create_invitation(self):
        [handgrader_student] = obj_build.make_users(1)
        self.course.handgraders.add(handgrader_student)
        self.course.students.add(handgrader_student)

        self.project.validate_and_update(max_group_size=3)
        other_enrolled = self.clone_user(self.enrolled)
        args = {'invited_usernames': [other_enrolled.username]}
        self.do_create_object_test(
            self.project.group_invitations,
            self.client, handgrader_student,
            self.get_invitations_url(self.project),
            args)

    def test_handgrader_also_staff_create_invitation(self):
        [handgrader_staff] = obj_build.make_users(1)
        self.course.handgraders.add(handgrader_staff)
        self.course.staff.add(handgrader_staff)

        self.project.validate_and_update(max_group_size=3)
        args = {'invited_usernames': [self.admin.username]}
        self.do_create_object_test(
            self.project.group_invitations, self.client,
            handgrader_staff, self.get_invitations_url(self.project), args)

    def test_other_create_invitation(self):
        self.visible_public_project.validate_and_update(max_group_size=3)
        other_nobody = obj_build.create_dummy_user()
        args = {'invited_usernames': [other_nobody.username, 'steve']}
        self.do_create_object_test(
            self.visible_public_project.group_invitations,
            self.client, self.nobody,
            self.get_invitations_url(self.visible_public_project), args)

    def test_invalid_create_invitation_enrollement_mismatch(self):
        self.visible_public_project.validate_and_update(max_group_size=3)
        args = {'invited_usernames': [self.nobody.username]}
        response = self.do_invalid_create_object_test(
            self.visible_public_project.group_invitations,
            self.client, self.enrolled,
            self.get_invitations_url(self.visible_public_project), args)
        print(response.data)

    def test_invalid_create_invitation_group_too_big(self):
        args = {'invited_usernames': ['steve']}
        response = self.do_invalid_create_object_test(
            self.visible_public_project.group_invitations,
            self.client, self.nobody,
            self.get_invitations_url(self.visible_public_project), args)
        print(response.data)

    def test_invalid_create_invitation_missing_invited_usernames(self):
        self.project.validate_and_update(max_group_size=3)
        other_admin = obj_build.make_admin_user(self.course)
        self.do_invalid_create_object_test(
            self.project.group_invitations, self.client, self.admin,
            self.get_invitations_url(self.project),
            {})

    def test_enrolled_create_invitation_hidden_project_permission_denied(self):
        other_enrolled = self.clone_user(self.enrolled)
        args = {'invited_usernames': [other_enrolled.username]}
        for project in self.hidden_projects:
            project.validate_and_update(max_group_size=3)
            self.do_permission_denied_create_test(
                project.group_invitations, self.client,
                self.enrolled, self.get_invitations_url(project), args)

    def test_guest_create_invitation_wrong_domain_permission_denied(self):
        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.visible_public_project.validate_and_update(max_group_size=2)

        inviter = obj_build.make_user()
        invitee = obj_build.make_allowed_domain_guest_user(self.course)

        args = {'invited_usernames': [invitee.username]}
        self.do_permission_denied_create_test(
            self.visible_public_project.group_invitations, self.client,
            inviter, self.get_invitations_url(self.visible_public_project), args)

    def test_invalid_non_allowed_domain_guest_invited_by_allowed_domain_guest(self):
        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.visible_public_project.validate_and_update(max_group_size=2)

        inviter = obj_build.make_allowed_domain_guest_user(self.course)
        invitee = obj_build.make_user()

        self.do_invalid_create_object_test(
            self.visible_public_project.group_invitations, self.client, inviter,
            self.get_invitations_url(self.visible_public_project),
            {'invited_usernames': [invitee.username]})

    def test_guest_create_invitation_right_domain(self):
        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.visible_public_project.validate_and_update(max_group_size=2)

        inviter = obj_build.make_allowed_domain_guest_user(self.course)
        invitee = obj_build.make_allowed_domain_guest_user(self.course)
        args = {'invited_usernames': [invitee.username]}
        self.do_create_object_test(
            self.visible_public_project.group_invitations,
            self.client, inviter,
            self.get_invitations_url(self.visible_public_project), args)

    def test_nobody_create_invitation_private_or_hidden_project_permission_denied(self):
        other_nobody = obj_build.create_dummy_user()
        args = {'invited_usernames': [other_nobody.username]}
        for project in (self.visible_private_project,
                        self.hidden_public_project,
                        self.hidden_private_project):
            self.do_permission_denied_create_test(
                project.group_invitations, self.client,
                self.nobody, self.get_invitations_url(project), args)

    def test_registration_disabled_permission_denied_for_enrolled(self):
        self.visible_public_project.validate_and_update(
            max_group_size=3, disallow_group_registration=True)
        other_enrolled = self.clone_user(self.enrolled)
        data = {'invited_usernames': [other_enrolled.username]}
        self.do_permission_denied_create_test(
            ag_models.GroupInvitation.objects,
            self.client, self.enrolled,
            self.get_invitations_url(self.visible_public_project), data)

    def test_registration_disabled_permission_denied_for_non_enrolled(self):
        self.visible_public_project.validate_and_update(
            max_group_size=3, disallow_group_registration=True)
        data = {'invited_usernames': [obj_build.create_dummy_user().username]}
        self.do_permission_denied_create_test(
            ag_models.GroupInvitation.objects,
            self.client, self.nobody,
            self.get_invitations_url(self.visible_public_project), data)

    def test_registration_disabled_staff_can_still_send_invitations(self):
        self.project.validate_and_update(
            max_group_size=3, disallow_group_registration=True)
        args = {'invited_usernames': [self.staff.username]}
        self.do_create_object_test(
            self.project.group_invitations, self.client,
            self.admin, self.get_invitations_url(self.project), args)

        args['invited_usernames'] = [self.clone_user(self.admin).username]
        self.do_create_object_test(
            self.project.group_invitations, self.client,
            self.clone_user(self.staff), self.get_invitations_url(self.project),
            args)

    def test_invalid_fields_other_than_invited_usernames_in_request(self):
        self.project.validate_and_update(max_group_size=3)
        args = {'invited_usernames': [self.staff.username],
                '_invitees_who_accepted': [self.staff.username]}
        response = self.do_invalid_create_object_test(
            self.project.group_invitations, self.client,
            self.admin, self.get_invitations_url(self.project), args)
        self.assertIn('invalid_fields', response.data)
        self.assertIn('_invitees_who_accepted', response.data['invalid_fields'])


class GetGroupInvitationTestCase(test_data.Client,
                                 test_data.Project,
                                 test_data.Group,
                                 test_impls.GetObjectTest,
                                 UnitTestBase):
    def test_admin_or_staff_view_invitation(self):
        for project in self.all_projects:
            for invite in (self.admin_group_invitation(project),
                           self.staff_group_invitation(project),
                           self.enrolled_group_invitation(project)):
                for user in self.admin, self.staff:
                    self.do_get_object_test(
                        self.client, user, self.invitation_url(invite),
                        invite.to_dict())

        for project in self.public_projects:
            invite = self.non_enrolled_group_invitation(project)
            for user in self.admin, self.staff:
                self.do_get_object_test(
                    self.client, user, self.invitation_url(invite),
                    invite.to_dict())

    def test_enrolled_view_invitation(self):
        for project in self.visible_projects:
            invite = self.enrolled_group_invitation(project)
            self.do_get_object_test(
                self.client, self.enrolled, self.invitation_url(invite),
                invite.to_dict())

    def test_non_enrolled_view_invitation(self):
        invite = self.non_enrolled_group_invitation(
            self.visible_public_project)
        self.do_get_object_test(
            self.client, self.nobody, self.invitation_url(invite),
            invite.to_dict())

    def test_non_involved_view_invitation_permission_denied(self):
        invite = self.enrolled_group_invitation(self.visible_public_project)
        non_involved_user = self.clone_user(self.enrolled)
        self.do_permission_denied_get_test(
            self.client, non_involved_user, self.invitation_url(invite))

    def test_enrolled_view_invitation_project_hidden_permission_denied(self):
        for project in self.hidden_projects:
            invite = self.enrolled_group_invitation(project)
            self.do_permission_denied_get_test(
                self.client, self.enrolled, self.invitation_url(invite))

    def test_non_enrolled_view_invitation_project_hidden_permission_denied(self):
        invitation = self.non_enrolled_group_invitation(
            self.hidden_public_project)
        self.do_permission_denied_get_test(
            self.client, self.nobody, self.invitation_url(invitation))

    def test_non_enrolled_view_invitation_project_private_permission_denied(self):
        invitation = self.non_enrolled_group_invitation(
            self.visible_public_project)
        self.visible_public_project.validate_and_update(
            guests_can_submit=False)
        self.do_permission_denied_get_test(
            self.client, self.nobody, self.invitation_url(invitation))

    def test_guest_get_invitation_allowed_domain(self):
        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.visible_public_project.validate_and_update(max_group_size=2)

        invitor = obj_build.make_allowed_domain_guest_user(self.course)
        invitee = obj_build.make_allowed_domain_guest_user(self.course)
        invitation = ag_models.GroupInvitation.objects.validate_and_create(
            invitor, [invitee], project=self.visible_public_project)

        self.do_get_object_test(
            self.client, invitor, self.invitation_url(invitation), invitation.to_dict())

    def test_guest_get_invitation_wrong_domain_permission_denied(self):
        self.visible_public_project.validate_and_update(max_group_size=2)

        invitor = obj_build.make_user()
        invitee = obj_build.make_user()
        invitation = ag_models.GroupInvitation.objects.validate_and_create(
            invitor, [invitee], project=self.visible_public_project)

        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.do_permission_denied_get_test(
            self.client, invitor, self.invitation_url(invitation))

    def test_handgrader_view_student_invitation_permission_denied(self):
        for project in self.all_projects:
            invite = self.enrolled_group_invitation(project)
            self.do_permission_denied_get_test(
                self.client, self.handgrader, self.invitation_url(invite))


class AcceptGroupInvitationTestCase(test_data.Client,
                                    test_data.Project,
                                    test_data.Group,
                                    UnitTestBase):
    def test_admin_all_invitees_accept(self):
        for project in self.all_projects:
            self.do_all_accept_test(self.admin_group_invitation(project))

    def test_staff_all_invitees_accept(self):
        for project in self.all_projects:
            self.do_all_accept_test(self.staff_group_invitation(project))

    def test_enrolled_all_invitees_accept(self):
        for project in self.visible_projects:
            self.do_all_accept_test(self.enrolled_group_invitation(project))

    def test_non_enrolled_all_invitees_accept(self):
        self.do_all_accept_test(
            self.non_enrolled_group_invitation(self.visible_public_project))

    def test_enrolled_accept_hidden_project_permission_denied(self):
        for project in self.hidden_projects:
            self.do_accept_permission_denied_test(
                self.enrolled_group_invitation(project), self.enrolled)

    def test_non_involved_user_permission_denied(self):
        for user in (self.clone_user(self.admin),
                     self.clone_user(self.staff),
                     self.clone_user(self.enrolled),
                     self.clone_user(self.nobody)):
            self.do_accept_permission_denied_test(
                self.enrolled_group_invitation(self.visible_public_project),
                user)

    def test_non_enrolled_accept_invitation_project_hidden_permission_denied(self):
        self.do_accept_permission_denied_test(
            self.non_enrolled_group_invitation(self.hidden_public_project),
            self.nobody)

    def test_allowed_domain_guest_accept(self):
        self.visible_public_project.validate_and_update(max_group_size=2)
        self.course.validate_and_update(allowed_guest_domain='@llama.edu')

        invitor = obj_build.make_allowed_domain_guest_user(self.course)
        invitee = obj_build.make_allowed_domain_guest_user(self.course)
        invitation = ag_models.GroupInvitation.objects.validate_and_create(
            invitor, [invitee], project=self.visible_public_project)

        self.do_all_accept_test(invitation)

    def test_wrong_domain_guest_accept_permission_denied(self):
        self.visible_public_project.validate_and_update(max_group_size=2)
        invitor = obj_build.make_user()
        invitee = obj_build.make_user()
        invitation = ag_models.GroupInvitation.objects.validate_and_create(
            invitor, [invitee], project=self.visible_public_project)

        self.course.validate_and_update(allowed_guest_domain='@llama.edu')

        self.do_accept_permission_denied_test(invitation, invitee)

    def test_non_enrolled_accept_invitation_project_private_permission_denied(self):
        invitation = self.non_enrolled_group_invitation(
            self.visible_public_project)
        self.visible_public_project.validate_and_update(
            guests_can_submit=False)
        self.do_accept_permission_denied_test(invitation, self.nobody)

    def test_creator_accepts_nothing_happens(self):
        invite = self.enrolled_group_invitation(self.visible_private_project)
        self.client.force_authenticate(invite.invitation_creator)
        response = self.client.post(self.accept_invitation_url(invite))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(0, len(response.data['invitees_who_accepted']))

    def test_registration_disabled_permission_denied_for_enrolled(self):
        self.visible_public_project.validate_and_update(
            disallow_group_registration=True)
        self.do_accept_permission_denied_test(
            self.enrolled_group_invitation(self.visible_public_project),
            self.enrolled)

    def test_registration_disabled_permission_denied_for_non_enrolled(self):
        self.visible_public_project.validate_and_update(
            disallow_group_registration=True)
        self.do_accept_permission_denied_test(
            self.non_enrolled_group_invitation(self.visible_public_project),
            self.nobody)

    def test_registration_disabled_staff_can_still_accept_invites(self):
        self.project.validate_and_update(disallow_group_registration=True)
        for invitation in (self.admin_group_invitation(self.project),
                           self.staff_group_invitation(self.project)):
            self.do_all_accept_test(invitation)

    def do_all_accept_test(self, invitation):
        # Send accept requests for all but one user, and make sure that
        # the list of users who accepted the invitation is updated and
        # reflected in the responses.
        invited_users = list(invitation.invited_users.all())
        # Computing this for later use.
        all_users = invited_users + [invitation.invitation_creator]
        original_invite_count = (
            ag_models.GroupInvitation.objects.count())
        original_group_count = ag_models.Group.objects.count()
        num_accepted = 0
        for user in invited_users[:-1]:
            num_accepted += 1
            self.client.force_authenticate(user)
            response = self.client.post(self.accept_invitation_url(invitation))
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            invitation.refresh_from_db()
            self.assertEqual(invitation.to_dict(), response.data)
            self.assertEqual(
                num_accepted,
                len(invitation.to_dict()['invitees_who_accepted']))

        # Send the final accept request, and make sure that the
        # invitation was deleted and that a group was created with the
        # right members.
        self.client.force_authenticate(invited_users[-1])
        response = self.client.post(self.accept_invitation_url(invitation))
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        self.assertEqual(
            original_invite_count - 1,
            ag_models.GroupInvitation.objects.count())

        self.assertEqual(
            original_group_count + 1,
            ag_models.Group.objects.count())
        group = ag_models.Group.objects.first()
        self.assertCountEqual(all_users, group.members.all())
        self.assertEqual(group.to_dict(), response.data)

        # Cleanup so that this method will work if called again in the
        # same test case.
        ag_models.Group.objects.all().delete()

    def accept_invitation_url(self, invitation):
        return reverse('accept-group-invitation', kwargs={'pk': invitation.pk})

    def do_accept_permission_denied_test(self, invitation, user):
        current_invite_count = (
            ag_models.GroupInvitation.objects.count())
        self.client.force_authenticate(user)
        response = self.client.post(self.accept_invitation_url(invitation))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual(current_invite_count,
                         ag_models.GroupInvitation.objects.count())
        invitation.refresh_from_db()  # Make sure invitation is still valid.


class RejectGroupInvitationTestCase(test_data.Client,
                                    test_data.Project,
                                    test_data.Group,
                                    test_impls.DestroyObjectTest,
                                    UnitTestBase):
    def test_admin_invitee_rejects(self):
        for project in self.all_projects:
            invitation = self.admin_group_invitation(project)
            rejector = invitation.invited_users.last()
            self.do_reject_invitation_test(invitation, rejector)

    def test_staff_invitee_rejects(self):
        for project in self.all_projects:
            invitation = self.staff_group_invitation(project)
            rejector = invitation.invited_users.last()
            self.do_reject_invitation_test(invitation, rejector)

    def test_enrolled_invitee_rejects(self):
        for project in self.visible_projects:
            invitation = self.enrolled_group_invitation(project)
            rejector = invitation.invited_users.last()
            self.do_reject_invitation_test(invitation, rejector)

    def test_non_enrolled_invitee_rejects(self):
        invitation = self.non_enrolled_group_invitation(
            self.visible_public_project)
        self.do_reject_invitation_test(
            invitation, invitation.invited_users.last())

    def test_admin_creator_revokes(self):
        for project in self.all_projects:
            invitation = self.admin_group_invitation(project)
            rejector = invitation.invitation_creator
            self.do_reject_invitation_test(invitation, rejector)

    def test_staff_creator_revokes(self):
        for project in self.all_projects:
            invitation = self.staff_group_invitation(project)
            rejector = invitation.invitation_creator
            self.do_reject_invitation_test(invitation, rejector)

    def test_enrolled_creator_revokes(self):
        for project in self.visible_projects:
            invitation = self.enrolled_group_invitation(project)
            rejector = invitation.invitation_creator
            self.do_reject_invitation_test(invitation, rejector)

    def test_non_enrolled_creator_revokes(self):
        invitation = self.non_enrolled_group_invitation(
            self.visible_public_project)
        self.do_reject_invitation_test(
            invitation, invitation.invitation_creator)

    def test_enrolled_reject_hidden_project_permission_denied(self):
        for project in self.hidden_projects:
            invitation = self.enrolled_group_invitation(project)
            self.do_delete_object_permission_denied_test(
                invitation, self.client, self.enrolled,
                self.invitation_url(invitation))

    def test_non_involved_user_permission_denied(self):
        invitation = self.enrolled_group_invitation(
            self.visible_public_project)
        for user in (self.clone_user(self.admin),
                     self.clone_user(self.staff),
                     self.clone_user(self.enrolled),
                     self.clone_user(self.nobody)):
            self.do_delete_object_permission_denied_test(
                invitation, self.client, user, self.invitation_url(invitation))

    def test_non_enrolled_reject_invitation_project_hidden_permission_denied(self):
        invitation = self.non_enrolled_group_invitation(
            self.hidden_public_project)
        self.do_delete_object_permission_denied_test(
            invitation, self.client, self.nobody,
            self.invitation_url(invitation))

    def test_non_enrolled_reject_invitation_project_private_permission_denied(self):
        invitation = self.non_enrolled_group_invitation(
            self.visible_public_project)
        self.visible_public_project.validate_and_update(
            guests_can_submit=False)
        self.do_delete_object_permission_denied_test(
            invitation, self.client, self.nobody,
            self.invitation_url(invitation))

    def test_enrolled_reject_invitation_registration_disabled_permission_denied(self):
        invitation = self.enrolled_group_invitation(self.visible_public_project)
        self.visible_public_project.validate_and_update(
            disallow_group_registration=True)
        self.do_delete_object_permission_denied_test(
            invitation, self.client, self.enrolled,
            self.invitation_url(invitation))

    def test_non_enrolled_reject_invitation_registration_disabled_permission_denied(self):
        invitation = self.non_enrolled_group_invitation(self.visible_public_project)
        self.visible_public_project.validate_and_update(
            disallow_group_registration=True)
        self.do_delete_object_permission_denied_test(
            invitation, self.client, self.nobody,
            self.invitation_url(invitation))

    def test_staff_can_reject_invitation_with_registration_disabled(self):
        self.visible_public_project.validate_and_update(
            disallow_group_registration=True)
        for invitation in (self.admin_group_invitation(self.project),
                           self.staff_group_invitation(self.project)):
            self.do_reject_invitation_test(
                invitation, invitation.invitation_creator)

    def do_reject_invitation_test(self, invitation, user):
        original_invite_count = (
            ag_models.GroupInvitation.objects.count())
        original_group_count = ag_models.Group.objects.count()

        users = [invitation.invitation_creator] + list(invitation.invited_users.all())
        self.client.force_authenticate(user)
        response = self.client.delete(self.invitation_url(invitation))
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
        self.assertEqual(
            original_invite_count - 1,
            ag_models.GroupInvitation.objects.count())
        self.assertEqual(
            original_group_count, ag_models.Group.objects.count())
