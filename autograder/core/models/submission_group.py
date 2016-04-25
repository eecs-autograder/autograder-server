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
    def validate_and_create(self, invitation_creator, invited_users, **kwargs):
        with transaction.atomic():
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
    """
    DEFAULT_INCLUDE_FIELDS = [
        'invitation_creator',
        'project',
        'invited_usernames',
        'invitees_who_accepted',
    ]

    invited_users = models.ManyToManyField(
        User, related_name='group_invitations_received',
        help_text="""The Users that the invitation_creator has invited
            to form a submission group together.
            This field is REQUIRED.
            This field may not be empty.""")

    invitation_creator = models.ForeignKey(
        User, related_name='group_invitations_sent',
        help_text="""The User who created this invitation.
            This field is REQUIRED.""")

    _invitees_who_accepted = ag_fields.StringArrayField(
        default=list, blank=True)

    project = models.ForeignKey(Project)

    objects = SubmissionGroupInvitationManager()

    @property
    def invited_usernames(self):
        """
        The usernames of the Users that will receive this invitation.
        """
        return (user.username for user in self.invited_users.all())

    @property
    def invitees_who_accepted(self):
        """
        A list of usernames indicating which invitees have accepted
        this invitation.
        This field is READ ONLY.
        """
        return tuple(self._invitees_who_accepted)

    @property
    def all_invitees_accepted(self):
        """
        Returns True if all invited users have accepted the invitation.
        """
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

    def to_dict(self, **kwargs):
        result = super().to_dict(**kwargs)

        if 'invitation_creator' in result:
            result['invitation_creator'] = self.invitation_creator.username

        return result

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class SubmissionGroupManager(ag_model_base.AutograderModelManager):
    # TODO: rename check_project_group_limits to check_project_group_size_limits
    def validate_and_create(self, members,
                            check_project_group_limits=True,
                            **kwargs):
        """
        New parameters:
            check_project_group_limits -- When False, validation of whether
                the number of users is within the specified project limits
                will NOT be run.
                Default value: True
        """
        with transaction.atomic():
            verify_users_can_be_in_group(
                members, kwargs['project'], 'members',
                check_project_group_limits=check_project_group_limits)

            group = self.model(**kwargs)
            group.save()
            group.members.add(*members)
            group.full_clean()
            return group


class SubmissionGroup(ag_model_base.AutograderModel):
    """
    This class represents a group of students that can submit
    to a particular project.

    Related object fields:
        submissions -- The Submissions that this group has made for the
            associated Project.
    """
    DEFAULT_INCLUDE_FIELDS = [
        'project',
        'extended_due_date',
        'member_names',
    ]

    objects = SubmissionGroupManager()

    members = models.ManyToManyField(
        User, related_name="groups_is_member_of",
        help_text="""The Users that belong to this submission group.
            This list must contain at least one member and no more than
            project.max_group_size members. A User can only be a member
            of one submission group per project.
            This field is REQUIRED.""")

    project = models.ForeignKey(Project, related_name="submission_groups")

    extended_due_date = models.DateTimeField(
        null=True, default=None, blank=True,
        help_text="""
            When this field is set, it indicates that members of this
            submission group can submit until this specified date,
            overriding the project closing time.
            Default value: None""")

    @property
    def member_names(self):
        """
        The usernames of the members of this SubmissionGroup.
        """
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

    def validate_and_update(self, check_project_group_limits=True, **kwargs):
        """
        New parameters:
            check_project_group_limits -- When False, validation of
                whether the group size is within specified project limits
                will NOT be performed. Defaults to True.

        This method is overridden to provide validation and atomicity
        when overwriting the members field.
        """
        members = kwargs.pop('members', None)
        with transaction.atomic():
            super().validate_and_update(**kwargs)
            if members is None:
                return

            verify_users_can_be_in_group(
                members, self.project, 'members',
                group_to_ignore=self,
                check_project_group_limits=check_project_group_limits)

            self.members.set(members)
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

        project -- The project the given users want to be in a group
            for.

        error_dict_field_name -- The field name to use in the
            ValidationError error dictionary.

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
        users -- An iterable of User objects that will potentially be in
            a group.

        project -- The project the given users want to be in a group
            for.

        error_dict_field_name -- The field name to use in the
            ValidationError error dictionary.

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

        project -- The project the given users want to be in a group
            for.

        error_dict_field_name -- The field name to use in the
            ValidationError error dictionary.

        group_to_ignore -- If this parameter is not None, then the given
            group will be ignored when checking to see if users are
            already in another group.

    Raises ValidationError if any of the given users are already in a
    SubmissionGroup other than group_to_ignore.
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
