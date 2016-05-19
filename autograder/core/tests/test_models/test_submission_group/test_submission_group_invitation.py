import itertools

from django.core import exceptions

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut

import autograder.core.models as ag_models


class _SetUp:
    def setUp(self):
        super().setUp()

        self.to_invite = obj_ut.create_dummy_users(3)
        self.to_invite_usernames = [user.username for user in self.to_invite]

        self.invitation_creator = obj_ut.create_dummy_user()
        self.invitation_creator_username = self.invitation_creator.username

        self.project = obj_ut.build_project(
            project_kwargs={'min_group_size': 1, 'max_group_size': 4},
            course_kwargs={
                'enrolled_students': list(itertools.chain(
                    [self.invitation_creator], self.to_invite))})


class MiscSubmissionGroupInvitationTestCase(_SetUp,
                                            TemporaryFilesystemTestCase):
    def test_to_dict_default_fields(self):
        expected_fields = [
            'project',
            'invited_usernames',
            'invitees_who_accepted',
            'invitation_creator'
        ]

        self.assertCountEqual(
            expected_fields,
            ag_models.SubmissionGroupInvitation.get_default_to_dict_fields())

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

        result = invitation.to_dict(exclude_fields=['invitation_creator'])
        self.assertNotIn('invitation_creator', result)

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


class GroupInvitationMembersTestCase(_SetUp, TemporaryFilesystemTestCase):
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
        self.to_invite.append(obj_ut.create_dummy_user())
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
            self.assertTrue(self.project.course.is_course_staff(user))

        ag_models.SubmissionGroupInvitation.objects.validate_and_create(
            invited_users=self.to_invite,
            invitation_creator=self.invitation_creator,
            project=self.project)

    def test_exception_all_invitees_not_enrolled_and_unenrolled_not_allowed(self):
        self.project.save()
        for user in itertools.chain([self.invitation_creator], self.to_invite):
            user.courses_is_enrolled_in.remove(self.project.course)
            self.assertFalse(self.project.course.is_enrolled_student(user))

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_no_exception_on_all_invitees_not_enrolled_and_unenrolled_allowed(self):
        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.save()
        for user in itertools.chain([self.invitation_creator], self.to_invite):
            user.courses_is_enrolled_in.remove(self.project.course)
            self.assertFalse(self.project.course.is_enrolled_student(user))

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
        self.project.allow_submissions_from_non_enrolled_students = True
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
        self.project.allow_submissions_from_non_enrolled_students = True
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
        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.save()

        self.invitation_creator.courses_is_enrolled_in.remove(
            self.project.course)

        for user in self.to_invite:
            user.courses_is_enrolled_in.remove(self.project.course)
            user.courses_is_staff_for.add(self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)
