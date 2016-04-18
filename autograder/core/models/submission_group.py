import os
import itertools

from django.db import models, transaction
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from autograder.core.models import Project
# from autograder.core.models.utils import (
#     ModelValidatableOnSave, ManagerWithValidateOnCreate)
from . import ag_model_base

from autograder.utilities import fields as ag_fields

import autograder.core.shared.utilities as ut


class SubmissionGroupInvitationManager(ag_model_base.AutograderModelManager):
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
            invited_usernames = kwargs.pop('invited_users', None)
            invitation_creator_name = kwargs.pop('invitation_creator')

            if not invited_usernames:
                raise ValidationError(
                    {'invited_users':
                     'Group invitations must invite at least one user'})

            invited_users = [
                User.objects.get_or_create(username=username)[0]
                for username in invited_usernames
            ]
            invitation_creator = User.objects.get(
                username=invitation_creator_name)

            # Lock all users at once to prevent deadlock
            User.objects.select_for_update().filter(
                pk__in=(user.pk for user in itertools.chain(
                    invited_users, [invitation_creator])))

            verify_users_can_be_in_group(
                tuple(itertools.chain(invited_users, (invitation_creator,))),
                kwargs['project'], 'invited_users')

            invitation = self.model(
                invitation_creator=invitation_creator, **kwargs)
            invitation.save()
            invitation.invited_users.add(*invited_users)
            invitation.full_clean()
            return invitation


class SubmissionGroupInvitation(ag_model_base.AutograderModel):
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
        if username == self.invitation_creator.username:
            return

        if username in self.invitees_who_accepted:
            return

        self._invitees_who_accepted.append(username)
        self.save()

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class SubmissionGroupManager(ag_model_base.AutograderModelManager):
    # TODO: rename check_project_group_limits to check_project_group_size_limits
    def validate_and_create(self, check_project_group_limits=True, **kwargs):
        """
        Additional arguments:
            check_project_group_limits -- When False, validation of whether
                the number of users is within the specified project limits
                will NOT be run.
                Default value: True

        The 'members' argument to this function should be a
        list of usernames, NOT Users.

        This function is concurrency-safe with other attempts
        to create SubmissionGroups.
        """
        with transaction.atomic():
            users = _get_and_lock_users(kwargs.pop('members'))
            verify_users_can_be_in_group(
                users, kwargs['project'], 'members',
                check_project_group_limits=check_project_group_limits)

            group = self.model(**kwargs)
            group.save()
            group.members.add(*users)
            group.full_clean()
            return group


class SubmissionGroup(ag_model_base.AutograderModel):
    """
    This class represents a group of students that can submit
    to a particular project.

    Fields:
        members -- The Users that belong to this submission group.
            This list must contain at least one member and no
            more than project.max_group_size members.
            A User can only be a member of one submission group per project.
            This field is REQUIRED.

            IMPORTANT: Updating this field manually is NOT concurrency-safe
                and does NOT perform any validation.
                To update this field when these things are important,
                use self.update_group instead.


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
        return tuple(user.username for user in self.members.all())

    # -------------------------------------------------------------------------

    @staticmethod
    def get_group(user, project):
        """
        Returns the SubmissionGroup that contains the specified user for
        the given project.
        Raises ObjectDoesNotExist if no such SubmissionGroup
        exists.
        """
        return user.groups_is_member_of.get(project=project)

    # -------------------------------------------------------------------------

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        submission_group_dir = ut.get_student_submission_group_dir(self)

        if not os.path.isdir(submission_group_dir):
            os.makedirs(submission_group_dir)

    def update_group(self, new_usernames, check_project_group_limits=True):
        """
        Parameters:
            new_usernames -- The an iterable of the names of
                the new members of this group.

            check_project_group_limits -- When False, validation of
                whether the group size is within specified project limits
                will NOT be performed. Defaults to True.

        Overwrites the current members of this group and replaces them
        with the users listed in new_usernames. This function is
        concurrency-safe and performs validation on the specified members.
        """
        with transaction.atomic():
            users = _get_and_lock_users(new_usernames)
            verify_users_can_be_in_group(
                users, self.project, 'members',
                group_to_ignore=self,
                check_project_group_limits=check_project_group_limits)

            self.members.set(users)
            self.full_clean()

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


def verify_users_have_same_enrollment_status(users, project,
                                             error_dict_field_name):
    """
    Parameters:
        users -- An iterable of User objects that will potentially be
            in a group.

        project -- The project the given users want to be in a group for.

        error_dict_field_name -- The field name to use in the ValidationError
            error dictionary.

    Checks to see whether the users have the same enrollment status.
    - All users must either be:
        - staff members/course administrators
        - enrolled students
        - non-enrolled students AND the project must allow submissions
            from non-enrolled students

    If these conditions are not met, then ValidationError will be raised.
    """
    users = tuple(users)

    num_enrolled = ut.count_if(
        users, lambda member: project.semester.is_enrolled_student(member))
    num_staff = ut.count_if(
        users, lambda member: project.semester.is_semester_staff(member))

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


def verify_group_size_allowed_by_project(users, project,
                                         error_dict_field_name):
    """
    Parameters:
        users -- An iterable of User objects that will potentially be
            in a group.

        project -- The project the given users want to be in a group for.

        error_dict_field_name -- The field name to use in the ValidationError
            error dictionary.

    Checks to make sure that the number of users is between
    project.min_group_size and project.max_group_size.
    ValidationError will be raised if this condition is not met.
    """
    users = tuple(users)

    num_members = len(users)
    if num_members < project.min_group_size:
        raise ValidationError({
            error_dict_field_name: (
                "Tried to add {} members, but the minimum "
                "for project '{}' is {}".format(
                    num_members, project.name,
                    project.min_group_size))})

    if num_members > project.max_group_size:
        raise ValidationError({
            error_dict_field_name: (
                "Tried to add {} members, but the max "
                "for project '{}' is {}".format(
                    num_members, project.name,
                    project.max_group_size))})


def verify_at_least_one_user_in_group(users, project, error_dict_field_name):
    users = tuple(users)
    if len(users) < 1:
        raise ValidationError({
            error_dict_field_name: "Groups must have at least one member"})


def verify_users_not_in_other_group(users, project, error_dict_field_name,
                                    group_to_ignore=None):
    """
    Parameters:
        users -- An iterable of User objects that will potentially be
            in a group.

        project -- The project the given users want to be in a group for.

        error_dict_field_name -- The field name to use in the ValidationError
            error dictionary.

        group_to_ignore -- If this parameter is not None, then the given
            group will be ignored when checking to see if users are already
            in another group.

    Raises ValidationError if any of the given users are already in
    a SubmissionGroup other than group_to_ignore.
    """
    users = tuple(users)

    for member in users:
        query = member.groups_is_member_of.filter(project=project)
        if group_to_ignore:
            query = query.exclude(pk=group_to_ignore.pk)

        if query.exists():
            raise ValidationError({
                error_dict_field_name: (
                    "User {} is already part of a submission "
                    "group for project '{}'".format(
                        member, project.name))})


def verify_users_can_be_in_group(users, project, error_dict_field_name,
                                 group_to_ignore=None,
                                 check_project_group_limits=True):
    """
    A shortcut for calling the above 4 "verify_" functions.
    """
    verify_users_have_same_enrollment_status(
        users, project, error_dict_field_name)
    if check_project_group_limits:
        verify_group_size_allowed_by_project(
            users, project, error_dict_field_name)
    verify_at_least_one_user_in_group(users, project, error_dict_field_name)
    verify_users_not_in_other_group(
        users, project, error_dict_field_name, group_to_ignore=group_to_ignore)


# -----------------------------------------------------------------------------


def _get_and_lock_users(usernames):
    usernames = list(usernames)
    users = [
        User.objects.get_or_create(username=username)[0]
        for username in usernames]
    users = User.objects.select_for_update().filter(username__in=usernames)
    return users
