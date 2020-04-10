from django.urls import reverse
from rest_framework import status

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase
from autograder.rest_api.tests.test_views.ag_view_test_base import AGViewTestBase
from rest_framework.test import APIClient


class _InvitationsSetUp(test_data.Client, test_data.Project, test_data.Group):
    pass


# TODO: remove common_generic_data module


class ListGroupInvitationsTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.project = obj_build.make_project()
        self.course = self.project.course
        self.invitation_data = [
            obj_build.make_group_invitation(project=self.project).to_dict(),
            obj_build.make_group_invitation(project=self.project).to_dict(),
            obj_build.make_group_invitation(project=self.project).to_dict(),
            obj_build.make_group_invitation(project=self.project).to_dict(),
        ]
        self.url = reverse('group-invitations', kwargs={'pk': self.project.pk})

    def test_admin_list_invitations(self):
        self.do_list_objects_test(
            self.client, obj_build.make_admin_user(self.course), self.url, self.invitation_data)

    def test_staff_list_invitations(self):
        self.do_list_objects_test(
            self.client, obj_build.make_staff_user(self.course), self.url, self.invitation_data)

    def test_student_list_invitations_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True)
        self.do_permission_denied_get_test(
            self.client, obj_build.make_student_user(self.course), self.url)

    def test_handgrader_list_invitations_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        self.do_permission_denied_get_test(
            self.client, obj_build.make_handgrader_user(self.course), self.url)

    def test_guest_list_invitations_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        self.do_permission_denied_get_test(self.client, obj_build.make_user(), self.url)

    # def build_invitations(self, project):
    #     project.validate_and_update(max_group_size=3)
    #     first = ag_models.GroupInvitation.objects.validate_and_create(
    #         self.admin, [self.staff], project=project)
    #     second = ag_models.GroupInvitation.objects.validate_and_create(
    #         self.clone_user(self.staff), [self.clone_user(self.admin)],
    #         project=project)
    #     return ag_serializers.SubmissionGroupInvitationSerializer(
    #         [first, second], many=True).data


class CreateInvitationTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.project = obj_build.make_project(max_group_size=3)
        self.course = self.project.course

        self.url = reverse('group-invitations', kwargs={'pk': self.project.pk})

    def test_admin_create_invitation(self):
        admin = obj_build.make_admin_user(self.course)
        staff = obj_build.make_staff_user(self.course)

        self.do_create_object_test(
            self.project.group_invitations, self.client, admin, self.url,
            {'invited_usernames': [staff.username]})

    def test_staff_create_invitation(self):
        admin = obj_build.make_admin_user(self.course)
        staff = obj_build.make_staff_user(self.course)

        self.do_create_object_test(
            self.project.group_invitations, self.client, staff, self.url,
            {'invited_usernames': [admin.username]})

    def test_student_create_invitation(self):
        self.project.validate_and_update(visible_to_students=True)
        student = obj_build.make_student_user(self.course)
        other_student = obj_build.make_student_user(self.course)

        self.do_create_object_test(
            self.project.group_invitations, self.client, student, self.url,
            {'invited_usernames': [other_student.username]})

    def test_handgrader_create_invitation_permission_denied(self):
        handgrader = obj_build.make_handgrader_user(self.course)
        other_handgrader = obj_build.make_handgrader_user(self.course)

        self.do_permission_denied_create_test(
            self.project.group_invitations, self.client, handgrader, self.url,
            {'invited_usernames': [other_handgrader.username]})

    def test_handgrader_also_student_create_invitation(self):
        handgrader_student = obj_build.make_user()
        self.course.handgraders.add(handgrader_student)
        self.course.students.add(handgrader_student)

        other_student = obj_build.make_student_user(self.course)
        self.do_create_object_test(
            self.project.group_invitations, self.client, handgrader_student, self.url,
            {'invited_usernames': [other_student.username]})

    def test_handgrader_also_staff_create_invitation(self):
        handgrader_staff = obj_build.make_user()
        self.course.handgraders.add(handgrader_staff)
        self.course.staff.add(handgrader_staff)

        other_staff = obj_build.make_staff_user(self.course)
        self.do_create_object_test(
            self.project.group_invitations, self.client, handgrader_staff, self.url,
            {'invited_usernames': [other_staff.username]})

    def test_guest_create_invitation(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        guest = obj_build.make_user()
        other_guest = obj_build.make_user()

        self.do_create_object_test(
            self.project.group_invitations, self.client, guest, self.url,
            {'invited_usernames': [other_guest.username, 'steve']})

    def test_invalid_create_invitation_enrollement_mismatch(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        guest = obj_build.make_user()
        student = obj_build.make_student_user(self.course)

        response = self.do_invalid_create_object_test(
            self.project.group_invitations, self.client, student, self.url,
            {'invited_usernames': [guest.username]})
        self.assertIn('invited_users', response.data)
        self.assertIn('non-enrolled', response.data['invited_users'][0])

        self.do_invalid_create_object_test(
            self.project.group_invitations, self.client, guest, self.url,
            {'invited_usernames': [student.username]})
        self.assertIn('invited_users', response.data)
        self.assertIn('non-enrolled', response.data['invited_users'][0])

    def test_invalid_create_invitation_group_too_big(self):
        self.project.validate_and_update(
            max_group_size=2, visible_to_students=True, guests_can_submit=True)

        response = self.do_invalid_create_object_test(
            self.project.group_invitations,
            self.client, obj_build.make_user(), self.url,
            {'invited_usernames': ['steve', 'stove']})
        self.assertIn('invited_users', response.data)
        self.assertIn('max', response.data['invited_users'][0])

    def test_invalid_create_invitation_missing_invited_usernames(self):
        admin = obj_build.make_admin_user(self.course)
        other_admin = obj_build.make_admin_user(self.course)
        self.do_invalid_create_object_test(
            self.project.group_invitations, self.client, admin, self.url, {})

    def test_student_create_invitation_hidden_project_permission_denied(self):
        student = obj_build.make_student_user(self.course)
        other_student = obj_build.make_student_user(self.course)
        self.do_permission_denied_create_test(
            self.project.group_invitations, self.client, student, self.url,
            {'invited_usernames': [other_student.username]})

    def test_guest_create_invitation_sender_has_wrong_domain_permission_denied(self):
        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        wrong_domain = obj_build.make_user()
        right_domain = obj_build.make_allowed_domain_guest_user(self.course)

        self.do_permission_denied_create_test(
            self.project.group_invitations, self.client, wrong_domain, self.url,
            {'invited_usernames': [right_domain.username]})

    def test_guest_create_invitation_recipient_has_wrong_domain_invalid(self) -> None:
        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        wrong_domain = obj_build.make_user()
        right_domain = obj_build.make_allowed_domain_guest_user(self.course)

        self.do_invalid_create_object_test(
            self.project.group_invitations, self.client, right_domain, self.url,
            {'invited_usernames': [wrong_domain.username]})

    def test_guest_create_invitation_right_domain(self):
        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        inviter = obj_build.make_allowed_domain_guest_user(self.course)
        invitee = obj_build.make_allowed_domain_guest_user(self.course)
        response = self.do_create_object_test(
            self.project.group_invitations, self.client, inviter, self.url,
            {'invited_usernames': [invitee.username]})

    def test_guest_create_invitation_project_private_or_hidden_permission_denied(self):
        sender = obj_build.make_user()
        invitee = obj_build.make_user()

        self.project.validate_and_update(visible_to_students=True, guests_can_submit=False)
        self.do_permission_denied_create_test(
            self.project.group_invitations, self.client, sender, self.url,
            {'invited_usernames': [invitee.username]})

        self.project.validate_and_update(visible_to_students=False, guests_can_submit=True)
        self.do_permission_denied_create_test(
            self.project.group_invitations, self.client, sender, self.url,
            {'invited_usernames': [invitee.username]})

    def test_registration_disabled_permission_denied(self):
        self.project.validate_and_update(
            disallow_group_registration=True, visible_to_students=True, guests_can_submit=True)

        student = obj_build.make_student_user(self.course)
        other_student = obj_build.make_student_user(self.course)
        self.do_permission_denied_create_test(
            ag_models.GroupInvitation.objects, self.client, student, self.url,
            {'invited_usernames': [other_student.username]})

        guest = obj_build.make_user()
        other_guest = obj_build.make_user()
        self.do_permission_denied_create_test(
            ag_models.GroupInvitation.objects, self.client, guest, self.url,
            {'invited_usernames': [other_guest.username]})

    def test_registration_disabled_staff_can_still_send_invitations(self):
        self.project.validate_and_update(disallow_group_registration=True)
        staff = obj_build.make_staff_user(self.course)
        other_staff = obj_build.make_staff_user(self.course)

        self.do_create_object_test(
            self.project.group_invitations, self.client, staff, self.url,
            {'invited_usernames': [other_staff.username]})

    def test_invalid_fields_other_than_invited_usernames_in_request(self):
        staff = obj_build.make_staff_user(self.course)
        other_staff = obj_build.make_staff_user(self.course)
        response = self.do_invalid_create_object_test(
            self.project.group_invitations, self.client, staff, self.url,
            {'invited_usernames': [other_staff.username],
             '_invitees_who_accepted': [staff.username]}
        )
        self.assertIn('invalid_fields', response.data)
        self.assertIn('_invitees_who_accepted', response.data['invalid_fields'])


class GetGroupInvitationTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.project = obj_build.make_project(max_group_size=2)
        self.course = self.project.course

    def invitation_url(self, invitation: ag_models.GroupInvitation) -> str:
        return reverse('group-invitation-detail', kwargs={'pk': invitation.pk})

    def test_admin_or_staff_get_any_invitation(self):
        admin_invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.admin)
        staff_invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.staff)
        student_invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.student)

        admin = obj_build.make_admin_user(self.course)
        staff = obj_build.make_staff_user(self.course)

        for invitation in admin_invitation, staff_invitation, student_invitation:
            for user in admin, staff:
                self.do_get_object_test(
                    self.client, user, self.invitation_url(invitation), invitation.to_dict())

        guest_invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.guest)
        for user in admin, staff:
            self.do_get_object_test(
                self.client,
                user,
                self.invitation_url(guest_invitation),
                guest_invitation.to_dict())

    def test_student_get_own_invitation(self):
        self.project.validate_and_update(visible_to_students=True)
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.student)

        self.do_get_object_test(
            self.client,
            invitation.invitation_creator,
            self.invitation_url(invitation),
            invitation.to_dict())

        self.do_get_object_test(
            self.client,
            invitation.invited_users.first(),
            self.invitation_url(invitation),
            invitation.to_dict())

    def test_guest_get_own_invitation(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.guest)

        self.do_get_object_test(
            self.client,
            invitation.invitation_creator,
            self.invitation_url(invitation),
            invitation.to_dict())

        self.do_get_object_test(
            self.client,
            invitation.invited_users.first(),
            self.invitation_url(invitation),
            invitation.to_dict())

    def test_student_or_guest_get_other_users_invitation_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        student_invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.student)
        guest_invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.guest)

        other_student = obj_build.make_student_user(self.course)
        self.do_permission_denied_get_test(
            self.client, other_student, self.invitation_url(student_invitation))
        self.do_permission_denied_get_test(
            self.client, other_student, self.invitation_url(guest_invitation))

        other_guest = obj_build.make_user()
        self.do_permission_denied_get_test(
            self.client, other_guest, self.invitation_url(student_invitation))
        self.do_permission_denied_get_test(
            self.client, other_guest, self.invitation_url(guest_invitation))

    def test_student_get_invitation_project_hidden_permission_denied(self):
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.student)
        self.do_permission_denied_get_test(
            self.client, invitation.invitation_creator, self.invitation_url(invitation))

    def test_guest_get_invitation_project_hidden_permission_denied(self):
        self.project.validate_and_update(guests_can_submit=True)
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.guest)
        self.do_permission_denied_get_test(
            self.client, invitation.invitation_creator, self.invitation_url(invitation))

    def test_guest_get_invitation_project_private_permission_denied(self):
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.guest)

        self.project.validate_and_update(visible_to_students=True, guests_can_submit=False)
        self.do_permission_denied_get_test(
            self.client, invitation.invitation_creator, self.invitation_url(invitation))

    def test_guest_get_invitation_allowed_domain(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        self.course.validate_and_update(allowed_guest_domain='@llama.edu')

        sender = obj_build.make_allowed_domain_guest_user(self.course)
        recipient = obj_build.make_allowed_domain_guest_user(self.course)
        invitation = ag_models.GroupInvitation.objects.validate_and_create(
            sender, [recipient], project=self.project)

        self.do_get_object_test(
            self.client, sender, self.invitation_url(invitation), invitation.to_dict())

    def test_guest_get_invitation_wrong_domain_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        sender = obj_build.make_user()
        recipient = obj_build.make_user()
        invitation = ag_models.GroupInvitation.objects.validate_and_create(
            sender, [recipient], project=self.project)

        self.course.validate_and_update(allowed_guest_domain='@llama.edu')
        self.do_permission_denied_get_test(
            self.client, sender, self.invitation_url(invitation))

    def test_handgrader_get_student_invitation_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.student)
        self.do_permission_denied_get_test(
            self.client,
            obj_build.make_handgrader_user(self.course),
            self.invitation_url(invitation))


class AcceptGroupInvitationTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.project = obj_build.make_project(max_group_size=2)
        self.course = self.project.course

    def test_admin_all_invitees_accept(self):
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.admin)
        self.do_all_accept_test(invitation)

    def test_staff_all_invitees_accept(self):
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.staff)
        self.do_all_accept_test(invitation)

    def test_student_all_invitees_accept(self):
        self.project.validate_and_update(visible_to_students=True)
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.student)
        self.do_all_accept_test(invitation)

    def test_guest_all_invitees_accept(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.guest)
        self.do_all_accept_test(invitation)

    def test_student_accept_hidden_project_permission_denied(self):
        self.project.validate_and_update(guests_can_submit=True)

        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.student)

        self.do_accept_permission_denied_test(invitation, invitation.invited_users.first())

    def test_guest_accept_invitation_project_hidden_permission_denied(self):
        self.project.validate_and_update(guests_can_submit=True)

        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.guest)

        self.do_accept_permission_denied_test(invitation, invitation.invited_users.first())

    def test_non_involved_user_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.guest)

        admin = obj_build.make_admin_user(self.course)
        staff = obj_build.make_staff_user(self.course)
        student = obj_build.make_student_user(self.course)
        handgrader = obj_build.make_handgrader_user(self.course)
        guest = obj_build.make_user()

        for user in admin, staff, student, handgrader, guest:
            self.do_accept_permission_denied_test(invitation, user)

    def test_allowed_domain_guest_accept(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        self.course.validate_and_update(allowed_guest_domain='@llama.edu')

        invitor = obj_build.make_allowed_domain_guest_user(self.course)
        invitee = obj_build.make_allowed_domain_guest_user(self.course)
        invitation = ag_models.GroupInvitation.objects.validate_and_create(
            invitor, [invitee], project=self.project)

        self.do_all_accept_test(invitation)

    def test_wrong_domain_guest_accept_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        invitor = obj_build.make_user()
        invitee = obj_build.make_user()
        invitation = ag_models.GroupInvitation.objects.validate_and_create(
            invitor, [invitee], project=self.project)

        self.course.validate_and_update(allowed_guest_domain='@llama.edu')

        self.do_accept_permission_denied_test(invitation, invitee)

    def test_guest_accept_invitation_project_private_permission_denied(self):
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.guest)

        self.project.validate_and_update(visible_to_students=True, guests_can_submit=False)
        self.do_accept_permission_denied_test(invitation, invitation.invited_users.first())

    def test_creator_accepts_nothing_happens(self):
        self.project.validate_and_update(visible_to_students=True)
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.student)

        self.client.force_authenticate(invitation.invitation_creator)
        response = self.client.post(self.accept_invitation_url(invitation))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(0, len(response.data['invitees_who_accepted']))

    def test_registration_disabled_permission_denied_for_student(self):
        self.project.validate_and_update(
            visible_to_students=True, disallow_group_registration=True)
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.student)

        self.do_accept_permission_denied_test(invitation, invitation.invited_users.first())

    def test_registration_disabled_permission_denied_for_guest(self):
        self.project.validate_and_update(
            visible_to_students=True, guests_can_submit=True, disallow_group_registration=True)
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.student)

        self.do_accept_permission_denied_test(invitation, invitation.invited_users.first())

    def test_registration_disabled_staff_can_still_accept_invitations(self):
        self.project.validate_and_update(disallow_group_registration=True)
        admin_invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.admin)
        staff_invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.staff)

        self.do_all_accept_test(admin_invitation)
        self.do_all_accept_test(staff_invitation)

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


class RejectGroupInvitationTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.project = obj_build.make_project(max_group_size=2)
        self.course = self.project.course

    def test_admin_invitee_rejects(self):
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.admin)
        self.do_reject_invitation_test(invitation, invitation.invited_users.last())

    def test_staff_invitee_rejects(self):
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.staff)
        self.do_reject_invitation_test(invitation, invitation.invited_users.last())

    def test_student_invitee_rejects(self):
        self.project.validate_and_update(visible_to_students=True)
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.student)
        self.do_reject_invitation_test(invitation, invitation.invited_users.last())

    def test_guest_invitee_rejects(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.guest)
        self.do_reject_invitation_test(invitation, invitation.invited_users.last())

    def test_admin_sender_revokes(self):
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.admin)
        self.do_reject_invitation_test(invitation, invitation.invitation_creator)

    def test_staff_sender_revokes(self):
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.staff)
        self.do_reject_invitation_test(invitation, invitation.invitation_creator)

    def test_student_sender_revokes(self):
        self.project.validate_and_update(visible_to_students=True)
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.student)
        self.do_reject_invitation_test(invitation, invitation.invitation_creator)

    def test_guest_sender_revokes(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.guest)
        self.do_reject_invitation_test(invitation, invitation.invitation_creator)

    def test_student_reject_hidden_project_permission_denied(self):
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.student)
        self.do_delete_object_permission_denied_test(
            invitation, self.client, invitation.invitation_creator,
            self.invitation_url(invitation))

        self.do_delete_object_permission_denied_test(
            invitation, self.client, invitation.invited_users.last(),
            self.invitation_url(invitation))

    def test_non_involved_user_permission_denied(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.guest)

        admin = obj_build.make_admin_user(self.course)
        staff = obj_build.make_staff_user(self.course)
        student = obj_build.make_student_user(self.course)
        handgrader = obj_build.make_handgrader_user(self.course)
        guest = obj_build.make_user()

        for user in admin, staff, student, handgrader, guest:
            self.do_delete_object_permission_denied_test(
                invitation, self.client, user, self.invitation_url(invitation))

    def test_guest_reject_invitation_project_hidden_permission_denied(self):
        self.project.validate_and_update(guests_can_submit=True)
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.guest)

        self.do_delete_object_permission_denied_test(
            invitation, self.client, invitation.invitation_creator,
            self.invitation_url(invitation))

        self.do_delete_object_permission_denied_test(
            invitation, self.client, invitation.invited_users.first(),
            self.invitation_url(invitation))

    def test_guest_reject_invitation_project_private_permission_denied(self):
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.guest)

        self.project.validate_and_update(visible_to_students=True, guests_can_submit=False)

        self.do_delete_object_permission_denied_test(
            invitation, self.client, invitation.invitation_creator,
            self.invitation_url(invitation))

        self.do_delete_object_permission_denied_test(
            invitation, self.client, invitation.invited_users.first(),
            self.invitation_url(invitation))

    def test_student_reject_invitation_registration_disabled_permission_denied(self):
        self.project.validate_and_update(
            visible_to_students=True, disallow_group_registration=True)
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.student)

        self.do_delete_object_permission_denied_test(
            invitation, self.client, invitation.invitation_creator,
            self.invitation_url(invitation))

        self.do_delete_object_permission_denied_test(
            invitation, self.client, invitation.invited_users.first(),
            self.invitation_url(invitation))

    def test_guest_reject_invitation_registration_disabled_permission_denied(self):
        self.project.validate_and_update(
            visible_to_students=True, guests_can_submit=True, disallow_group_registration=True)
        invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.guest)

        self.do_delete_object_permission_denied_test(
            invitation, self.client, invitation.invitation_creator,
            self.invitation_url(invitation))

        self.do_delete_object_permission_denied_test(
            invitation, self.client, invitation.invited_users.first(),
            self.invitation_url(invitation))

    def test_staff_can_reject_invitation_with_registration_disabled(self):
        self.project.validate_and_update(disallow_group_registration=True)
        admin_invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.admin)
        staff_invitation = obj_build.make_group_invitation(
            project=self.project, users_role=obj_build.UserRole.staff)

        self.do_reject_invitation_test(admin_invitation, admin_invitation.invitation_creator)
        self.do_reject_invitation_test(staff_invitation, staff_invitation.invitation_creator)

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

    def invitation_url(self, invitation: ag_models.GroupInvitation) -> str:
        return reverse('group-invitation-detail', kwargs={'pk': invitation.pk})
