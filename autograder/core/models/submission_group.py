import os
import itertools

from django.db import models, transaction, connection
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

from autograder.core.models import Project
from autograder.core.models.utils import (
    ModelValidatableOnSave, ManagerWithValidateOnCreate)

from autograder.utilities import fields as ag_fields

import autograder.core.shared.utilities as ut


class SubmissionGroupInvitationManager(ManagerWithValidateOnCreate):
    def validate_and_create(self, **kwargs):
        """
        The 'invited_users' argument to this function should be an
        iterable of usernames, NOT Users.
        the 'invitation_creator' argument to this function should be
        a username, NOT a User.

        This function is concurrency-safe with the creation of
        actual SubmissionGroups.
        """
        with transaction.atomic():
            invitation_creator = User.objects.select_for_update().get(
                username=kwargs.pop('invitation_creator'))

            invited_usernames = kwargs.pop('invited_users')
            for username in invited_usernames:
                User.objects.get_or_create(username=username)

            to_invite = User.objects.select_for_update().filter(
                username__in=invited_usernames)

            verify_users_can_be_in_group(
                tuple(itertools.chain(to_invite, (invitation_creator,))),
                kwargs['project'], 'invited_users')

            invitation = self.model(
                invitation_creator=invitation_creator, **kwargs)
            invitation.save()
            invitation.invited_users.add(*to_invite)
            invitation.full_clean()
            return invitation


class SubmissionGroupInvitation(ModelValidatableOnSave):
    """
    This class stores an invitation for a set of users to create a
    SubmissionGroup together.

    Fields:
        invited_users -- The Users that the invitation_creator has
            invited to form a submission group together.
            This field is REQUIRED.
            This field may not be empty.

        invitation_creator -- The User who created this invitation.
            This field is REQUIRED.

        invitees_who_accepted -- A list of usernames indicating which
            invitees have accepted this invitation.
            This field is READ ONLY.

        project -- The Project that this group invitation is linked to.

    Properties:
        all_members_accepted -- Returns True if all invited users have
            accepted the invitation.

        invited_usernames -- The usernames of the Users that will receive
            this invitation.

    Member functions:
        invitee_accept
    """
    invited_users = models.ManyToManyField(
        User, related_name='group_invitations_received')
    invitation_creator = models.ForeignKey(
        User, related_name='group_invitations_sent')
    _invitees_who_accepted = ag_fields.StringArrayField(
        default=list, blank=True)
    project = models.ForeignKey(Project)

    objects = SubmissionGroupInvitationManager()

    @property
    def invited_usernames(self):
        return (user.username for user in self.invited_users.all())

    @property
    def invitees_who_accepted(self):
        return tuple(self._invitees_who_accepted)

    @property
    def all_invitees_accepted(self):
        return set(self.invited_usernames) == set(self._invitees_who_accepted)

    def invitee_accept(self, username):
        """
        Marks the user with the given name as having accepted the group
        invitation.
        """
        if username in self.invitees_who_accepted:
            return

        self._invitees_who_accepted.append(username)
        self.save()

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class SubmissionGroupManager(ManagerWithValidateOnCreate):
    def validate_and_create(self, **kwargs):
        """
        The 'members' argument to this function should be a
        list of usernames, NOT Users.

        This function is concurrency-safe with other attempts
        to create SubmissionGroups.
        """
        with transaction.atomic():
            users = User.objects.select_for_update().filter(
                username__in=kwargs.pop('members')).all()
        # with transaction.atomic(), connection.cursor() as c:
        #     c.execute('LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE'.format(
        #         SubmissionGroup.objects.model._meta.db_table))

            group = self.model(**kwargs)
            group.save()
            group.members.add(*users)
            group.full_clean()
            return group


class SubmissionGroup(ModelValidatableOnSave):
    """
    This class represents a group of students that can submit
    to a particular project.

    Fields:
        members -- The Users that belong to this submission group.
            This list must contain at least one member and no
            more than project.max_group_size members.
            A User can only be a member of one submission group per project.
            This field is REQUIRED.

        project -- The project that this SubmissionGroup belongs to.
            This field is REQUIRED.

        extended_due_date -- When this field is set, it indicates
            that members of this submission group can submit until
            this specified date, overriding the project closing time.
            Default value: None

        num_submissions_with_full_feedback -- TODO

    Related object fields:
        submissions -- The Submissions that this group has made for the
            associated Project.

    Properties:
        member_names -- The usernames of the members of this SubmissionGroup.

    Static methods:
        get_group()

    Overridden methods:
        clean()
        save()
    """
    objects = SubmissionGroupManager()

    members = models.ManyToManyField(User, related_name="groups_is_member_of")
    project = models.ForeignKey(Project, related_name="submission_groups")
    extended_due_date = models.DateTimeField(
        null=True, default=None, blank=True)

    @property
    def member_names(self):
        return tuple(self._members)

    # -------------------------------------------------------------------------

    # # TODO: phase out
    # @staticmethod
    # def get_group(user, project):
    #     """
    #     Returns the SubmissionGroup that contains the specified user for
    #     the given project.
    #     Raises ObjectDoesNotExist if no such SubmissionGroup
    #     exists.
    #     """
    #     return user.groups_is_member_of.get(project=project)

    # -------------------------------------------------------------------------

    # def __init__(self, *args, **kwargs):
    #     members = kwargs.pop('members', None)
    #     if members is None:  # and '_members' in kwargs:
    #         # __init__ is being called by the actual database
    #         return super().__init__(*args, **kwargs)

    #     # __init__ is being called by the user
    #     return super().__init__(*args, _members=members, **kwargs)

    # TODO: atomic, concurrency-safe member function that updates group
    # members

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        submission_group_dir = ut.get_student_submission_group_dir(self)

        if not os.path.isdir(submission_group_dir):
            os.makedirs(submission_group_dir)

    def clean(self):
        num_members = self.members.count()
        if num_members < self.project.min_group_size:
            raise ValidationError({
                'members': (
                    "Tried to add {} members, but the minimum "
                    "for project '{}' is {}".format(
                        num_members, self.project.name,
                        self.project.min_group_size))})

        if num_members < 1:
            raise ValidationError({
                'members': "Groups must have at least one member"})

        if num_members > self.project.max_group_size:
            raise ValidationError({
                'members': (
                    "Tried to add {} members, but the max "
                    "for project '{}' is {}".format(
                        num_members, self.project.name,
                        self.project.max_group_size))})

        self._clean_group_members_for_enrollment(self.members.all())

        for member in self.members.all():
            # current_memberships =
            # SubmissionGroup.objects.filter(
            #     project=self.project, _members__contains=[member])
            if member.groups_is_member_of.filter(
                    project=self.project).exclude(pk=self.pk).exists():
                raise ValidationError({
                    'members': (
                        "User {} is already part of a submission "
                        "group for project '{}'".format(
                            member, self.project.name))})

    def _clean_group_members_for_enrollment(self, members):
        semester = self.project.semester
        num_enrolled = ut.count_if(
            members, lambda member: semester.is_enrolled_student(member))

        num_staff = ut.count_if(
            members, lambda member: semester.is_semester_staff(member))

        if num_staff:
            if num_staff != len(members):
                raise ValidationError({
                    'members': (
                        "Groups with any staff members "
                        "must consist of only staff members")})
            return

        if not self.project.allow_submissions_from_non_enrolled_students:
            if not num_enrolled or num_enrolled != len(members):
                raise ValidationError({
                    'members': (
                        "This project only accepts submissions "
                        "from enrolled students.")})
            return

        if num_enrolled and num_enrolled != len(members):
            raise ValidationError({
                'members': (
                    "Non-enrolled students can only be in "
                    "groups with other non-enrolled students.")})

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


def verify_users_can_be_in_group(users, project, error_dict_field_name):
    """
    Parameters:
        users -- A container of User objects that will potentially be
            in a group.

        project -- The project the given users want to be in a group for.

        error_dict_field_name -- The field name to use in the ValidationError
            error dictionary.

    Checks to see whether the given users can be in a group together.
    - All users must either be:
        - staff members/course administrators
        - enrolled students
        - non-enrolled students AND the project must allow submissions
            from non-enrolled students
    - None of the users may already be in a SubmissionGroup for the
        specified project.
    - The size of the group must be within the limits set by the project.

    If these conditions are not met, then ValidationError will be thrown.
    """
    semester = project.semester

    num_members = len(users)
    if num_members < project.min_group_size:
        raise ValidationError({
            error_dict_field_name: (
                "Tried to add {} members, but the minimum "
                "for project '{}' is {}".format(
                    num_members, project.name,
                    project.min_group_size))})

    if num_members < 1:
        raise ValidationError({
            error_dict_field_name: "Groups must have at least one member"})

    if num_members > project.max_group_size:
        raise ValidationError({
            error_dict_field_name: (
                "Tried to add {} members, but the max "
                "for project '{}' is {}".format(
                    num_members, project.name,
                    project.max_group_size))})

    for member in users:
        if member.groups_is_member_of.filter(
                project=project).exists():
            raise ValidationError({
                error_dict_field_name: (
                    "User {} is already part of a submission "
                    "group for project '{}'".format(
                        member, project.name))})

    num_enrolled = ut.count_if(
        users, lambda member: semester.is_enrolled_student(member))
    num_staff = ut.count_if(
        users, lambda member: semester.is_semester_staff(member))

    if num_staff:
        if num_staff != len(users):
            raise ValidationError({
                error_dict_field_name: (
                    "Groups with any staff users "
                    "must consist of only staff users")})
        return

    if not project.allow_submissions_from_non_enrolled_students:
        if not num_enrolled or num_enrolled != len(users):
            raise ValidationError({
                error_dict_field_name: (
                    "This project only accepts submissions "
                    "from enrolled students.")})
        return

    if num_enrolled and num_enrolled != len(users):
        raise ValidationError({
            error_dict_field_name: (
                "Non-enrolled students can only be in "
                "groups with other non-enrolled students.")})
