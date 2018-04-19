import itertools

from django.core import exceptions

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build

import autograder.core.models as ag_models


class _SetUp:
    def setUp(self):
        super().setUp()

        self.to_invite = obj_build.create_dummy_users(3)
        self.to_invite_usernames = [user.username for user in self.to_invite]

        self.invitation_creator = obj_build.create_dummy_user()
        self.invitation_creator_username = self.invitation_creator.username

        self.project = obj_build.build_project(
            project_kwargs={'min_group_size': 1, 'max_group_size': 4},
            course_kwargs={
                'students': list(itertools.chain(
                    [self.invitation_creator], self.to_invite))})


class MiscSubmissionGroupInvitationTestCase(_SetUp, UnitTestBase):
    def test_serializable_fields(self):
        expected_fields = [
            'pk',
            'project',
            'invited_usernames',
            'invitees_who_accepted',
            'invitation_creator'
        ]

        self.assertCountEqual(
            expected_fields,
            ag_models.SubmissionGroupInvitation.get_serializable_fields())

        invitation = ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            invited_users=self.to_invite,
            invitation_creator=self.invitation_creator,
            project=self.project)

        self.assertTrue(invitation.to_dict())

    def test_editable_fields(self):
        self.assertCountEqual(
            [],
            ag_models.SubmissionGroupInvitation.get_editable_fields())

    def test_invitation_creator_username_expanded(self):
        invitation = ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            invited_users=self.to_invite,
            invitation_creator=self.invitation_creator,
            project=self.project)

        result = invitation.to_dict()
        self.assertEqual(self.invitation_creator.username,
                         result['invitation_creator'])

    def test_valid_initialization(self):
        invitation = ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            invited_users=self.to_invite,
            invitation_creator=self.invitation_creator,
            project=self.project)

        invitation.refresh_from_db()
        self.assertEqual(
            self.invitation_creator, invitation.invitation_creator)

        self.assertCountEqual(self.to_invite, invitation.invited_users.all())
        self.assertEqual(self.project, invitation.project)
        self.assertCountEqual([], invitation.invitees_who_accepted)
        self.assertFalse(invitation.all_invitees_accepted)

    def test_invitee_accept(self):
        invitation = ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            invited_users=self.to_invite,
            invitation_creator=self.invitation_creator,
            project=self.project)

        invitation.invitee_accept(self.to_invite[0])

        self.assertCountEqual(
            self.to_invite_usernames[:1], invitation.invitees_who_accepted)
        self.assertFalse(invitation.all_invitees_accepted)

    def test_all_members_accepted(self):
        invitation = ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            invited_users=self.to_invite,
            invitation_creator=self.invitation_creator,
            project=self.project)

        for invitee in self.to_invite:
            invitation.invitee_accept(invitee)

        self.assertCountEqual(
            self.to_invite_usernames, invitation.invitees_who_accepted)
        self.assertTrue(invitation.all_invitees_accepted)


class GroupInvitationMembersTestCase(_SetUp, UnitTestBase):
    def test_exception_on_no_invitees(self):
        self.project.min_group_size = 1
        self.project.save()

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=[],
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_on_too_few_invitees(self):
        self.project.min_group_size = 3
        self.project.save()

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite[:1],
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_on_too_many_invitees(self):
        self.to_invite.append(obj_build.create_dummy_user())
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_on_invitee_already_in_another_group(self):
        ag_models.SubmissionGroup.objects.validate_and_create(
            project=self.project,
            members=self.to_invite[:1])

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_on_invitation_creator_already_in_another_group(self):
        ag_models.SubmissionGroup.objects.validate_and_create(
            project=self.project,
            members=[self.invitation_creator])

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_on_some_invitees_not_enrolled(self):
        self.to_invite[1].courses_is_enrolled_in.remove(
            self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_on_invitation_creator_not_enrolled_but_invitees_are(self):
        self.invitation_creator.courses_is_enrolled_in.remove(
            self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_no_exception_invitees_and_invitation_creator_all_staff_members(self):
        for user in itertools.chain([self.invitation_creator], self.to_invite):
            user.courses_is_enrolled_in.remove(self.project.course)
            user.courses_is_staff_for.add(self.project.course)
            self.assertTrue(self.project.course.is_staff(user))

        ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            invited_users=self.to_invite,
            invitation_creator=self.invitation_creator,
            project=self.project)

    def test_exception_all_invitees_not_enrolled_and_unenrolled_not_allowed(self):
        self.project.save()
        for user in itertools.chain([self.invitation_creator], self.to_invite):
            user.courses_is_enrolled_in.remove(self.project.course)
            self.assertFalse(self.project.course.is_student(user))

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_no_exception_on_all_invitees_not_enrolled_and_unenrolled_allowed(self):
        self.project.guests_can_submit = True
        self.project.save()
        for user in itertools.chain([self.invitation_creator], self.to_invite):
            user.courses_is_enrolled_in.remove(self.project.course)
            self.assertFalse(self.project.course.is_student(user))

        ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            invited_users=self.to_invite,
            invitation_creator=self.invitation_creator,
            project=self.project)

    def test_exception_invitees_mix_of_enrolled_and_staff(self):
        self.to_invite[0].courses_is_enrolled_in.remove(
            self.project.course)

        self.to_invite[0].courses_is_staff_for.add(self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_invitation_creator_staff_invitees_enrolled(self):
        self.invitation_creator.courses_is_enrolled_in.remove(
            self.project.course)
        self.invitation_creator.courses_is_staff_for.add(
            self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_invitation_creator_staff_invitees_not_enrolled(self):
        self.project.guests_can_submit = True
        self.project.save()

        self.invitation_creator.courses_is_enrolled_in.remove(
            self.project.course)
        self.invitation_creator.courses_is_staff_for.add(
            self.project.course)

        for user in self.to_invite:
            user.courses_is_enrolled_in.remove(self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_invitation_creator_enrolled_invitees_staff(self):
        for user in self.to_invite:
            user.courses_is_enrolled_in.remove(self.project.course)
            user.courses_is_staff_for.add(self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_invitation_creator_not_enrolled_invitees_enrolled(self):
        self.project.guests_can_submit = True
        self.project.save()

        self.invitation_creator.courses_is_enrolled_in.remove(
            self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_invitation_creator_not_enrolled_invitees_staff(self):
        self.project.guests_can_submit = True
        self.project.save()

        self.invitation_creator.courses_is_enrolled_in.remove(self.project.course)

        for user in self.to_invite:
            user.courses_is_enrolled_in.remove(self.project.course)
            user.courses_is_staff_for.add(self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_invitees_includes_invitor(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invitation_creator=self.invitation_creator,
                invited_users=[self.invitation_creator],
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)


class PendingInvitationRestrictionsTestCase(_SetUp, UnitTestBase):
    def test_invalid_invitation_create_user_has_pending_invite_sent(self):
        ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            invited_users=self.to_invite,
            invitation_creator=self.invitation_creator,
            project=self.project)

        other_invitees = obj_build.create_dummy_users(len(self.to_invite))
        self.project.course.students.add(*other_invitees)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invitation_creator=self.invitation_creator,
                invited_users=other_invitees,
                project=self.project)

        self.assertIn('pending_invitation', cm.exception.message_dict)

    def test_invalid_invitation_create_user_has_pending_invite_received(self):
        ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            invitation_creator=self.invitation_creator,
            invited_users=self.to_invite,
            project=self.project)

        creator = self.to_invite[0]
        other_invitees = obj_build.create_dummy_users(len(self.to_invite))
        self.project.course.students.add(*other_invitees)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invitation_creator=creator, invited_users=other_invitees,
                project=self.project)

        self.assertIn('pending_invitation', cm.exception.message_dict)

    def test_valid_invitations_across_projects(self):
        project2 = ag_models.Project.objects.validate_and_create(
            course=self.project.course, max_group_size=4,
            name='project2')

        ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            invitation_creator=self.invitation_creator,
            invited_users=self.to_invite,
            project=self.project)

        # Same creator (and invitees), different project
        ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            invitation_creator=self.invitation_creator,
            invited_users=self.to_invite,
            project=project2)

        project3 = ag_models.Project.objects.validate_and_create(
            course=self.project.course, max_group_size=4,
            name='project3')

        # Creator has pending invites received on different project
        ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            invitation_creator=self.to_invite[0],
            invited_users=self.to_invite[1:],
            project=project3)
