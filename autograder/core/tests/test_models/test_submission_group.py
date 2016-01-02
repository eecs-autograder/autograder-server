import os
import datetime
import itertools

from django.core.exceptions import ValidationError, ObjectDoesNotExist
# from django.db import connection, transaction
from django.contrib.auth.models import User
from django.utils import timezone

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from autograder.core.models import (
    Project, Semester, Course, SubmissionGroup, SubmissionGroupInvitation)

import autograder.core.shared.utilities as ut
import autograder.core.tests.dummy_object_utils as obj_ut


class SubmissionGroupInvitationTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.to_invite = obj_ut.create_dummy_users(3)
        self.to_invite_usernames = [user.username for user in self.to_invite]

        self.invitation_creator = obj_ut.create_dummy_user()
        self.invitation_creator_username = self.invitation_creator.username

        self.project = obj_ut.build_project(
            project_kwargs={'min_group_size': 1, 'max_group_size': 4},
            semester_kwargs={
                'enrolled_students': list(itertools.chain(
                    [self.invitation_creator], self.to_invite))})

        # print(self.project.semester.enrolled_students.all())

    def test_valid_initialization(self):
        invitation = SubmissionGroupInvitation.objects.validate_and_create(
            invited_users=self.to_invite_usernames,
            invitation_creator=self.invitation_creator,
            project=self.project)

        loaded = SubmissionGroupInvitation.objects.get(pk=invitation.pk)
        self.assertEqual(self.invitation_creator_username,
                         loaded.invitation_creator.username)
        self.assertEqual(
            self.invitation_creator, loaded.invitation_creator)

        self.assertCountEqual(self.to_invite, loaded.invited_users.all())
        self.assertCountEqual(
            self.to_invite_usernames, loaded.invited_usernames)
        self.assertEqual(self.project, loaded.project)

    def test_invite_users_that_do_not_exist_yet(self):
        new_usernames = ['joe', 'bob', 'steve']

        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.save()

        self.invitation_creator.semesters_is_enrolled_in.remove(
            self.project.semester)

        for username in new_usernames:
            with self.assertRaises(ObjectDoesNotExist):
                User.objects.get(username=username)

        invitation = SubmissionGroupInvitation.objects.validate_and_create(
            invited_users=new_usernames,
            invitation_creator=self.invitation_creator,
            project=self.project)

        users = User.objects.filter(username__in=new_usernames)
        self.assertCountEqual(new_usernames, (user.username for user in users))
        loaded = SubmissionGroupInvitation.objects.get(pk=invitation.pk)

        self.assertCountEqual(users, loaded.invited_users.all())

    def test_invitee_accept(self):
        invitation = SubmissionGroupInvitation.objects.validate_and_create(
            invited_users=self.to_invite_usernames,
            invitation_creator=self.invitation_creator.username,
            project=self.project)

        invitation.invitee_accept(self.to_invite_usernames[0])

        self.assertCountEqual(
            self.to_invite_usernames[:1], invitation.invitees_who_accepted)

    def test_all_members_accepted(self):
        invitation = SubmissionGroupInvitation.objects.validate_and_create(
            invited_users=self.to_invite_usernames,
            invitation_creator=self.invitation_creator,
            project=self.project)

        for invitee in self.to_invite_usernames:
            invitation.invitee_accept(invitee)

        self.assertCountEqual(
            self.to_invite_usernames, invitation.invitees_who_accepted)
        self.assertTrue(invitation.all_invitees_accepted)

    def test_exception_on_normal_create_method(self):
        with self.assertRaises(NotImplementedError):
            SubmissionGroup.objects.create(project=self.project)

    # def test_exception_on_no_invitation_creator(self):
    #     with self.assertRaises(ValidationError) as cm:
    #         SubmissionGroupInvitation.objects.validate_and_create(
    #             invited_users=self.to_invite_usernames, project=self.project)

    #     self.assertTrue('invitation_creator' in cm.exception.message_dict)

    def test_exception_on_no_invitees(self):
        self.project.min_group_size = 1
        self.project.save()

        with self.assertRaises(ValidationError) as cm:
            SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=[],
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_on_too_few_invitees(self):
        self.project.min_group_size = 3
        self.project.save()

        with self.assertRaises(ValidationError) as cm:
            SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite_usernames[:1],
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_on_too_many_invitees(self):
        self.to_invite_usernames.append('steve')
        with self.assertRaises(ValidationError) as cm:
            SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite_usernames,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_on_invitee_already_in_another_group(self):
        SubmissionGroup.objects.validate_and_create(
            project=self.project,
            members=self.to_invite_usernames[:1])

        with self.assertRaises(ValidationError) as cm:
            SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite_usernames,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_on_invitation_creator_already_in_another_group(self):
        SubmissionGroup.objects.validate_and_create(
            project=self.project,
            members=[self.invitation_creator_username])

        with self.assertRaises(ValidationError) as cm:
            SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite_usernames,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_on_some_invitees_not_enrolled(self):
        self.to_invite[1].semesters_is_enrolled_in.remove(
            self.project.semester)

        with self.assertRaises(ValidationError) as cm:
            SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite_usernames,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_on_invitation_creator_not_enrolled_but_invitees_are(self):
        self.invitation_creator.semesters_is_enrolled_in.remove(
            self.project.semester)

        with self.assertRaises(ValidationError) as cm:
            SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite_usernames,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_no_exception_invitees_and_invitation_creator_all_staff_members(self):
        for user in itertools.chain([self.invitation_creator], self.to_invite):
            user.semesters_is_enrolled_in.remove(self.project.semester)
            user.semesters_is_staff_for.add(self.project.semester)
            self.assertTrue(self.project.semester.is_semester_staff(user))

        SubmissionGroupInvitation.objects.validate_and_create(
            invited_users=self.to_invite_usernames,
            invitation_creator=self.invitation_creator,
            project=self.project)

    def test_exception_all_invitees_not_enrolled_and_unenrolled_not_allowed(self):
        self.project.save()
        for user in itertools.chain([self.invitation_creator], self.to_invite):
            user.semesters_is_enrolled_in.remove(self.project.semester)
            self.assertFalse(self.project.semester.is_enrolled_student(user))

        with self.assertRaises(ValidationError) as cm:
            SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite_usernames,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_no_exception_on_all_invitees_not_enrolled_and_unenrolled_allowed(self):
        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.save()
        for user in itertools.chain([self.invitation_creator], self.to_invite):
            user.semesters_is_enrolled_in.remove(self.project.semester)
            self.assertFalse(self.project.semester.is_enrolled_student(user))

        SubmissionGroupInvitation.objects.validate_and_create(
            invited_users=self.to_invite_usernames,
            invitation_creator=self.invitation_creator,
            project=self.project)

    def test_exception_invitees_mix_of_enrolled_and_staff(self):
        self.to_invite[0].semesters_is_enrolled_in.remove(
            self.project.semester)

        self.to_invite[0].semesters_is_staff_for.add(self.project.semester)

        with self.assertRaises(ValidationError) as cm:
            SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite_usernames,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_invitation_creator_staff_invitees_enrolled(self):
        self.invitation_creator.semesters_is_enrolled_in.remove(
            self.project.semester)
        self.invitation_creator.semesters_is_staff_for.add(
            self.project.semester)

        with self.assertRaises(ValidationError) as cm:
            SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite_usernames,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_invitation_creator_staff_invitees_not_enrolled(self):
        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.save()

        self.invitation_creator.semesters_is_enrolled_in.remove(
            self.project.semester)
        self.invitation_creator.semesters_is_staff_for.add(
            self.project.semester)

        for user in self.to_invite:
            user.semesters_is_enrolled_in.remove(self.project.semester)

        with self.assertRaises(ValidationError) as cm:
            SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite_usernames,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_invitation_creator_enrolled_invitees_staff(self):
        for user in self.to_invite:
            user.semesters_is_enrolled_in.remove(self.project.semester)
            user.semesters_is_staff_for.add(self.project.semester)

        with self.assertRaises(ValidationError) as cm:
            SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite_usernames,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_invitation_creator_not_enrolled_invitees_enrolled(self):
        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.save()

        self.invitation_creator.semesters_is_enrolled_in.remove(
            self.project.semester)

        with self.assertRaises(ValidationError) as cm:
            SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite_usernames,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

    def test_exception_invitation_creator_not_enrolled_invitees_staff(self):
        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.save()

        self.invitation_creator.semesters_is_enrolled_in.remove(
            self.project.semester)

        for user in self.to_invite:
            user.semesters_is_enrolled_in.remove(self.project.semester)
            user.semesters_is_staff_for.add(self.project.semester)

        with self.assertRaises(ValidationError) as cm:
            SubmissionGroupInvitation.objects.validate_and_create(
                invited_users=self.to_invite_usernames,
                invitation_creator=self.invitation_creator,
                project=self.project)

        self.assertTrue('invited_users' in cm.exception.message_dict)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class SubmissionGroupTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = Course.objects.validate_and_create(name='eecs280')
        self.semester = Semester.objects.validate_and_create(
            name='f15', course=self.course)

        self.project = Project.objects.validate_and_create(
            name='my_project', semester=self.semester, max_group_size=2)

        self.enrolled_group = obj_ut.create_dummy_users(2)
        self.semester.add_enrolled_students(*self.enrolled_group)

        self.staff_group = obj_ut.create_dummy_users(2)
        self.semester.add_semester_staff(*self.staff_group)

        self.non_enrolled_group = obj_ut.create_dummy_users(2)

    # -------------------------------------------------------------------------

    def test_valid_initialization_with_defaults(self):
        group = SubmissionGroup.objects.validate_and_create(
            members=(user.username for user in self.enrolled_group),
            project=self.project)

        loaded_group = SubmissionGroup.objects.get(
            pk=group.pk)

        self.assertEqual(group, loaded_group)
        self.assertIsNone(loaded_group.extended_due_date)
        self.assertCountEqual(
            self.enrolled_group, loaded_group.members.all())
        self.assertCountEqual(
            (user.username for user in self.enrolled_group),
            loaded_group.member_names)
        self.assertEqual(self.project, loaded_group.project)

        self.assertTrue(
            os.path.isdir(ut.get_student_submission_group_dir(loaded_group)))

    def test_valid_initialization_no_defaults(self):
        extended_due_date = timezone.now() + datetime.timedelta(days=1)
        group = SubmissionGroup.objects.validate_and_create(
            members=(user.username for user in self.enrolled_group),
            project=self.project,
            extended_due_date=extended_due_date)

        loaded_group = SubmissionGroup.objects.get(pk=group.pk)

        self.assertEqual(group, loaded_group)
        self.assertEqual(loaded_group.extended_due_date, extended_due_date)
        self.assertCountEqual(
            self.enrolled_group, loaded_group.members.all())
        self.assertEqual(self.project, loaded_group.project)

    def test_valid_member_of_multiple_groups_for_different_projects(self):
        other_project = Project.objects.validate_and_create(
            name='project spam', semester=self.semester, max_group_size=2)

        repeated_user = self.enrolled_group[0]

        first_group = SubmissionGroup.objects.validate_and_create(
            members=(user.username for user in self.enrolled_group),
            project=self.project)

        second_group = SubmissionGroup.objects.validate_and_create(
            members=[repeated_user.username], project=other_project)

        loaded_first_group = SubmissionGroup.objects.get(pk=first_group.pk)
        self.assertEqual(first_group, loaded_first_group)
        self.assertCountEqual(
            self.enrolled_group, loaded_first_group.members.all())
        self.assertEqual(self.project, loaded_first_group.project)

        loaded_second_group = SubmissionGroup.objects.get(pk=second_group.pk)
        self.assertEqual(second_group, loaded_second_group)
        self.assertCountEqual(
            [repeated_user], loaded_second_group.members.all())
        self.assertEqual(other_project, loaded_second_group.project)

        groups = list(repeated_user.groups_is_member_of.all())
        self.assertCountEqual([first_group, second_group], groups)

    def test_valid_override_group_max_size(self):
        self.enrolled_group += obj_ut.create_dummy_users(3)
        self.project.semester.enrolled_students.add(*self.enrolled_group)
        group = SubmissionGroup.objects.validate_and_create(
            members=(user.username for user in self.enrolled_group),
            project=self.project,
            check_project_group_limits=False)

        loaded_group = SubmissionGroup.objects.get(pk=group.pk)

        self.assertEqual(group, loaded_group)
        self.assertCountEqual(
            self.enrolled_group, loaded_group.members.all())

    def test_valid_override_group_min_size(self):
        self.project.min_group_size = 10
        self.project.max_group_size = 10
        self.project.validate_and_save()
        group = SubmissionGroup.objects.validate_and_create(
            members=(user.username for user in self.enrolled_group),
            project=self.project,
            check_project_group_limits=False)

        loaded_group = SubmissionGroup.objects.get(pk=group.pk)

        self.assertEqual(group, loaded_group)
        self.assertCountEqual(
            self.enrolled_group, loaded_group.members.all())

    def test_error_create_empty_group_with_override_size(self):
        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.validate_and_create(
                members=[], project=self.project)

    def test_normal_update_group(self):
        group = SubmissionGroup.objects.validate_and_create(
            members=(user.username for user in self.enrolled_group),
            project=self.project)

        new_members = obj_ut.create_dummy_users(2)
        self.project.semester.enrolled_students.add(*new_members)

        group.update_group((user.username for user in new_members))

        loaded_group = SubmissionGroup.objects.get(pk=group.pk)
        self.assertCountEqual(
            new_members, loaded_group.members.all())

    def test_update_group_error_too_many_members(self):
        group = SubmissionGroup.objects.validate_and_create(
            members=(user.username for user in self.enrolled_group),
            project=self.project)

        new_members = obj_ut.create_dummy_users(5)
        self.project.semester.enrolled_students.add(*new_members)

        with self.assertRaises(ValidationError) as cm:
            group.update_group((user.username for user in new_members))

        self.assertTrue('members' in cm.exception.message_dict)

    def test_update_group_error_too_few_members(self):
        group = SubmissionGroup.objects.validate_and_create(
            members=(user.username for user in self.enrolled_group),
            project=self.project)

        new_members = obj_ut.create_dummy_users(2)
        self.project.semester.enrolled_students.add(*new_members)

        self.project.min_group_size = 10
        self.project.max_group_size = 10
        self.project.validate_and_save()

        with self.assertRaises(ValidationError) as cm:
            group.update_group((user.username for user in new_members))

        self.assertTrue('members' in cm.exception.message_dict)

    def test_update_group_override_min_size(self):
        group = SubmissionGroup.objects.validate_and_create(
            members=(user.username for user in self.enrolled_group),
            project=self.project)

        self.project.min_group_size = 10
        self.project.max_group_size = 10
        self.project.validate_and_save()

        new_members = obj_ut.create_dummy_users(2)
        self.project.semester.enrolled_students.add(*new_members)
        group.update_group((user.username for user in new_members),
                           check_project_group_limits=False)

        loaded_group = SubmissionGroup.objects.get(pk=group.pk)

        self.assertEqual(group, loaded_group)
        self.assertCountEqual(new_members, loaded_group.members.all())

    def test_update_group_override_max_size(self):
        group = SubmissionGroup.objects.validate_and_create(
            members=(user.username for user in self.enrolled_group),
            project=self.project)

        new_members = obj_ut.create_dummy_users(5)
        self.project.semester.enrolled_students.add(*new_members)

        group.update_group((user.username for user in new_members),
                           check_project_group_limits=False)

        loaded_group = SubmissionGroup.objects.get(pk=group.pk)

        self.assertEqual(group, loaded_group)
        self.assertCountEqual(new_members, loaded_group.members.all())

    def test_error_update_empty_group_with_override_size(self):
        group = SubmissionGroup.objects.validate_and_create(
            members=(user.username for user in self.enrolled_group),
            project=self.project)

        with self.assertRaises(ValidationError):
            group.update_group([], check_project_group_limits=False)

    def test_exception_on_normal_create_method(self):
        with self.assertRaises(NotImplementedError):
            SubmissionGroup.objects.create(project=self.project)

    def test_exception_on_too_few_group_members(self):
        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.validate_and_create(
                members=[], project=self.project)

        self.assertEqual([], list(SubmissionGroup.objects.all()))

        self.project.min_group_size = 2
        self.project.validate_and_save()
        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.validate_and_create(
                members=self.enrolled_group[0:1],
                project=self.project)

        self.assertEqual([], list(SubmissionGroup.objects.all()))

    def test_exception_on_too_many_group_members(self):
        self.project.save()

        new_user = obj_ut.create_dummy_user()
        self.semester.add_enrolled_students(new_user)
        self.enrolled_group.append(new_user)

        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.validate_and_create(
                members=self.enrolled_group, project=self.project)

        self.assertEqual([], list(SubmissionGroup.objects.all()))

    def test_exception_on_group_member_already_in_another_group(self):
        group = SubmissionGroup.objects.validate_and_create(
            members=self.enrolled_group[0:1], project=self.project)

        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.validate_and_create(
                members=self.enrolled_group, project=self.project)

        self.assertEqual([group], list(SubmissionGroup.objects.all()))

    def test_exception_on_some_members_not_enrolled(self):
        mixed_group = self.enrolled_group[0:1] + [obj_ut.create_dummy_user()]
        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.validate_and_create(
                members=mixed_group, project=self.project)

        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.save()

        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.validate_and_create(
                members=mixed_group, project=self.project)

    def test_no_exception_group_of_staff_members(self):
        group = SubmissionGroup.objects.validate_and_create(
            members=self.staff_group, project=self.project)

        loaded_group = SubmissionGroup.objects.get(pk=group.pk)

        self.assertEqual(group, loaded_group)
        self.assertCountEqual(
            self.staff_group, loaded_group.members.all())
        self.assertEqual(self.project, loaded_group.project)

    def test_exception_all_members_not_enrolled_and_unenrolled_not_allowed(self):
        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.validate_and_create(
                members=self.non_enrolled_group, project=self.project)

    def test_no_exception_on_all_members_not_enrolled_and_unenrolled_allowed(self):
        self.project.allow_submissions_from_non_enrolled_students = True
        self.project.save()

        group = SubmissionGroup.objects.validate_and_create(
            members=self.non_enrolled_group, project=self.project)

        loaded_group = SubmissionGroup.objects.get(pk=group.pk)

        self.assertEqual(group, loaded_group)
        self.assertCountEqual(
            self.non_enrolled_group, loaded_group.members.all())
        self.assertEqual(self.project, loaded_group.project)

    def test_exception_group_mix_of_enrolled_and_staff(self):
        self.project.max_group_size = 5
        self.project.save()
        with self.assertRaises(ValidationError):
            SubmissionGroup.objects.validate_and_create(
                members=self.staff_group + self.enrolled_group,
                project=self.project)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


# class GroupQueryFunctionTests(TemporaryFilesystemTestCase):
#     def setUp(self):
#         super().setUp()

#         self.course = Course.objects.validate_and_create(name='eecs280')
#         self.semester = Semester.objects.validate_and_create(
#             name='f15', course=self.course)

#         self.project = Project.objects.validate_and_create(
#             name='my_project', semester=self.semester, max_group_size=5,
#             allow_submissions_from_non_enrolled_students=True)

#     def test_get_single_member_group(self):
#         group = SubmissionGroup.objects.validate_and_create(
#             members=['jameslp@umich.edu'], project=self.project)

#         self.assertEqual(
#             group,
#             SubmissionGroup.get_group(['jameslp@umich.edu'], self.project))

#     def test_get_multiple_member_group_exact(self):
#         members = [
#             'jameslp@umich.edu', 'awdeorio@umich.edu', 'jsatonik@umich.edu'
#         ]
#         group = SubmissionGroup.objects.validate_and_create(
#             members=members, project=self.project)

#         lookup = [
#             'jsatonik@umich.edu', 'jameslp@umich.edu', 'awdeorio@umich.edu'
#         ]
#         self.assertEqual(
#             group, SubmissionGroup.get_group(lookup, self.project))

#     def test_get_multiple_member_group_subset(self):
#         members = [
#             'jameslp@umich.edu', 'awdeorio@umich.edu', 'jsatonik@umich.edu'
#         ]
#         group = SubmissionGroup.objects.validate_and_create(
#             members=members, project=self.project)

#         lookup = [
#             'jsatonik@umich.edu', 'awdeorio@umich.edu'
#         ]
#         self.assertEqual(
#             group, SubmissionGroup.get_group(lookup, self.project))

#     def test_not_found_no_match(self):
#         members = [
#             'jameslp@umich.edu', 'awdeorio@umich.edu', 'jsatonik@umich.edu'
#         ]
#         SubmissionGroup.objects.validate_and_create(
#             members=members, project=self.project)

#         lookup = ['jjuett@umich.edu']
#         with self.assertRaises(ObjectDoesNotExist):
#             SubmissionGroup.get_group(lookup, self.project)

#     def test_not_found_partial_match(self):
#         members = [
#             'jameslp@umich.edu', 'awdeorio@umich.edu', 'jsatonik@umich.edu'
#         ]
#         SubmissionGroup.objects.validate_and_create(
#             members=members, project=self.project)

#         lookup = [
#             'jsatonik@umich.edu', 'jjuett@umich.edu'
#         ]
#         with self.assertRaises(ObjectDoesNotExist):
#             SubmissionGroup.get_group(lookup, self.project)
