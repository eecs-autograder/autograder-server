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

        self.sender = obj_build.create_dummy_user()
        self.sender_username = self.sender.username

        self.project = obj_build.build_project(
            project_kwargs={'min_group_size': 1, 'max_group_size': 4},
            course_kwargs={
                'students': list(itertools.chain(
                    [self.sender], self.to_invite))})


class MiscSubmissionGroupInvitationTestCase(_SetUp, UnitTestBase):
    def test_serializable_fields(self):
        expected_fields = [
            'pk',
            'project',
            'sender',
            'recipients',
            'sender_username',
            'recipient_usernames',
            'recipients_who_accepted',
        ]

        invitation = ag_models.GroupInvitation.objects.validate_and_create(
            recipients=self.to_invite,
            sender=self.sender,
            project=self.project)
        serialized = invitation.to_dict()

        self.assertCountEqual(expected_fields, serialized.keys())

        self.assertIsInstance(serialized['sender'], dict)
        self.assertIsInstance(serialized['recipients'], list)
        self.assertIsInstance(serialized['recipients'][0], dict)

    def test_editable_fields(self):
        self.assertCountEqual(
            [],
            ag_models.GroupInvitation.get_editable_fields())

    def test_valid_initialization(self):
        invitation = ag_models.GroupInvitation.objects.validate_and_create(
            recipients=self.to_invite,
            sender=self.sender,
            project=self.project)

        invitation.refresh_from_db()
        self.assertEqual(
            self.sender, invitation.sender)

        self.assertCountEqual(self.to_invite, invitation.recipients.all())
        self.assertEqual(self.project, invitation.project)
        self.assertCountEqual([], invitation.recipients_who_accepted)
        self.assertFalse(invitation.all_recipients_accepted)

    def test_recipient_accept(self):
        invitation = ag_models.GroupInvitation.objects.validate_and_create(
            recipients=self.to_invite,
            sender=self.sender,
            project=self.project)

        invitation.recipient_accept(self.to_invite[0])

        self.assertCountEqual(
            self.to_invite_usernames[:1], invitation.recipients_who_accepted)
        self.assertFalse(invitation.all_recipients_accepted)

    def test_all_members_accepted(self):
        invitation = ag_models.GroupInvitation.objects.validate_and_create(
            recipients=self.to_invite,
            sender=self.sender,
            project=self.project)

        for recipient in self.to_invite:
            invitation.recipient_accept(recipient)

        self.assertCountEqual(
            self.to_invite_usernames, invitation.recipients_who_accepted)
        self.assertTrue(invitation.all_recipients_accepted)


class GroupInvitationMembersTestCase(_SetUp, UnitTestBase):
    def test_exception_on_no_recipients(self):
        self.project.min_group_size = 1
        self.project.save()

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                recipients=[],
                sender=self.sender,
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)

    def test_exception_on_too_few_recipients(self):
        self.project.min_group_size = 3
        self.project.save()

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                recipients=self.to_invite[:1],
                sender=self.sender,
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)

    def test_exception_on_too_many_recipients(self):
        self.to_invite.append(obj_build.create_dummy_user())
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                recipients=self.to_invite,
                sender=self.sender,
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)

    def test_exception_on_recipient_already_in_another_group(self):
        ag_models.Group.objects.validate_and_create(
            project=self.project,
            members=self.to_invite[:1])

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                recipients=self.to_invite,
                sender=self.sender,
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)

    def test_exception_on_sender_already_in_another_group(self):
        ag_models.Group.objects.validate_and_create(
            project=self.project,
            members=[self.sender])

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                recipients=self.to_invite,
                sender=self.sender,
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)

    def test_exception_on_some_recipients_not_enrolled(self):
        self.to_invite[1].courses_is_enrolled_in.remove(
            self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                recipients=self.to_invite,
                sender=self.sender,
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)

    def test_valid_creator_and_recipient_allowed_domain(self):
        self.project.course.validate_and_update(allowed_guest_domain='@llama.edu')

        self.project.guests_can_submit = True
        self.project.save()

        sender = obj_build.make_allowed_domain_guest_user(self.project.course)
        recipient = obj_build.make_allowed_domain_guest_user(self.project.course)

        ag_models.GroupInvitation.objects.validate_and_create(
            recipients=[recipient],
            sender=sender,
            project=self.project)

    def test_exception_sender_allowed_guest_recipient_wrong_domain(self):
        self.project.course.validate_and_update(allowed_guest_domain='@llama.edu')

        self.project.guests_can_submit = True
        self.project.save()

        sender = obj_build.make_allowed_domain_guest_user(self.project.course)
        recipient = obj_build.make_user()

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                recipients=[recipient],
                sender=sender,
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)

    def test_exception_sender_wrong_domain_recipient_allowed_guest(self):
        self.project.course.validate_and_update(allowed_guest_domain='@llama.edu')

        self.project.guests_can_submit = True
        self.project.save()

        sender = obj_build.make_user()
        recipient = obj_build.make_allowed_domain_guest_user(self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                recipients=[recipient],
                sender=sender,
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)

    def test_exception_sender_and_recipient_wrong_domain(self):
        self.project.course.validate_and_update(allowed_guest_domain='@llama.edu')

        self.project.guests_can_submit = True
        self.project.save()

        sender = obj_build.make_user()
        recipient = obj_build.make_user()

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                recipients=[recipient],
                sender=sender,
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)

    def test_exception_on_sender_not_enrolled_but_recipients_are(self):
        self.project.course.validate_and_update(allowed_guest_domain='@llama.edu')

        self.sender.courses_is_enrolled_in.remove(
            self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                recipients=self.to_invite,
                sender=self.sender,
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)

    def test_no_exception_recipients_and_sender_all_staff_members(self):
        for user in itertools.chain([self.sender], self.to_invite):
            user.courses_is_enrolled_in.remove(self.project.course)
            user.courses_is_staff_for.add(self.project.course)
            self.assertTrue(self.project.course.is_staff(user))

        ag_models.GroupInvitation.objects.validate_and_create(
            recipients=self.to_invite,
            sender=self.sender,
            project=self.project)

    def test_exception_all_recipients_not_enrolled_and_unenrolled_not_allowed(self):
        self.project.save()
        for user in itertools.chain([self.sender], self.to_invite):
            user.courses_is_enrolled_in.remove(self.project.course)
            self.assertFalse(self.project.course.is_student(user))

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                recipients=self.to_invite,
                sender=self.sender,
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)

    def test_no_exception_on_all_recipients_not_enrolled_and_unenrolled_allowed(self):
        self.project.guests_can_submit = True
        self.project.save()
        for user in itertools.chain([self.sender], self.to_invite):
            user.courses_is_enrolled_in.remove(self.project.course)
            self.assertFalse(self.project.course.is_student(user))

        ag_models.GroupInvitation.objects.validate_and_create(
            recipients=self.to_invite,
            sender=self.sender,
            project=self.project)

    def test_exception_recipients_mix_of_enrolled_and_staff(self):
        self.to_invite[0].courses_is_enrolled_in.remove(
            self.project.course)

        self.to_invite[0].courses_is_staff_for.add(self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                recipients=self.to_invite,
                sender=self.sender,
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)

    def test_exception_sender_staff_recipients_enrolled(self):
        self.sender.courses_is_enrolled_in.remove(
            self.project.course)
        self.sender.courses_is_staff_for.add(
            self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                recipients=self.to_invite,
                sender=self.sender,
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)

    def test_exception_sender_staff_recipients_not_enrolled(self):
        self.project.guests_can_submit = True
        self.project.save()

        self.sender.courses_is_enrolled_in.remove(
            self.project.course)
        self.sender.courses_is_staff_for.add(
            self.project.course)

        for user in self.to_invite:
            user.courses_is_enrolled_in.remove(self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                recipients=self.to_invite,
                sender=self.sender,
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)

    def test_exception_sender_enrolled_recipients_staff(self):
        for user in self.to_invite:
            user.courses_is_enrolled_in.remove(self.project.course)
            user.courses_is_staff_for.add(self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                recipients=self.to_invite,
                sender=self.sender,
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)

    def test_exception_sender_not_enrolled_recipients_enrolled(self):
        self.project.guests_can_submit = True
        self.project.save()

        self.sender.courses_is_enrolled_in.remove(
            self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                recipients=self.to_invite,
                sender=self.sender,
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)

    def test_exception_sender_not_enrolled_recipients_staff(self):
        self.project.guests_can_submit = True
        self.project.save()

        self.sender.courses_is_enrolled_in.remove(self.project.course)

        for user in self.to_invite:
            user.courses_is_enrolled_in.remove(self.project.course)
            user.courses_is_staff_for.add(self.project.course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                recipients=self.to_invite,
                sender=self.sender,
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)

    def test_exception_recipients_includes_sender(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                sender=self.sender,
                recipients=[self.sender],
                project=self.project)

        self.assertTrue('recipients' in cm.exception.message_dict)


class PendingInvitationRestrictionsTestCase(_SetUp, UnitTestBase):
    def test_invalid_invitation_create_user_has_pending_invite_sent(self):
        ag_models.GroupInvitation.objects.validate_and_create(
            recipients=self.to_invite,
            sender=self.sender,
            project=self.project)

        other_recipients = obj_build.create_dummy_users(len(self.to_invite))
        self.project.course.students.add(*other_recipients)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                sender=self.sender,
                recipients=other_recipients,
                project=self.project)

        self.assertIn('pending_invitation', cm.exception.message_dict)

    def test_invalid_invitation_create_user_has_pending_invite_received(self):
        ag_models.GroupInvitation.objects.validate_and_create(
            sender=self.sender,
            recipients=self.to_invite,
            project=self.project)

        creator = self.to_invite[0]
        other_recipients = obj_build.create_dummy_users(len(self.to_invite))
        self.project.course.students.add(*other_recipients)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.GroupInvitation.objects.validate_and_create(
                sender=creator, recipients=other_recipients,
                project=self.project)

        self.assertIn('pending_invitation', cm.exception.message_dict)

    def test_valid_invitations_across_projects(self):
        project2 = ag_models.Project.objects.validate_and_create(
            course=self.project.course, max_group_size=4,
            name='project2')

        ag_models.GroupInvitation.objects.validate_and_create(
            sender=self.sender,
            recipients=self.to_invite,
            project=self.project)

        # Same creator (and recipients), different project
        ag_models.GroupInvitation.objects.validate_and_create(
            sender=self.sender,
            recipients=self.to_invite,
            project=project2)

        project3 = ag_models.Project.objects.validate_and_create(
            course=self.project.course, max_group_size=4,
            name='project3')

        # Creator has pending invites received on different project
        ag_models.GroupInvitation.objects.validate_and_create(
            sender=self.to_invite[0],
            recipients=self.to_invite[1:],
            project=project3)
