from django.contrib.auth.models import User
from django.core import exceptions
from typing import Iterable

from autograder import utils

from ..project import Project


def verify_users_have_same_enrollment_status(users: Iterable[User], project: Project,
                                             error_dict_field_name: str):
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
        - staff members/course admins
        - enrolled students
        - non-enrolled students with allowed domain usernames
            AND the project must allow submissions from guests

    If these conditions are not met, then ValidationError will be raised.
    """
    users = tuple(users)

    num_enrolled = utils.count_if(
        users, lambda member: project.course.is_student(member))
    num_staff = utils.count_if(
        users, lambda member: project.course.is_staff(member))

    # Note: yes, the nested ifs are necessary
    if num_staff:
        if num_staff != len(users):
            raise exceptions.ValidationError({
                error_dict_field_name: (
                    "Groups with any staff users "
                    "must consist of only staff users")})
    elif num_enrolled:
        if num_enrolled != len(users):
            raise exceptions.ValidationError({
                error_dict_field_name: (
                    "Non-enrolled students can only be in "
                    "groups with other non-enrolled students.")})
    elif not project.guests_can_submit:
        # At this point, there are only guests in the group
        raise exceptions.ValidationError({
            error_dict_field_name: (
                "This project only accepts submissions "
                "from enrolled students.")})
    else:
        # At this point, there are only guests in the group
        # and guests can submit
        num_allowed_guests = utils.count_if(
            users, lambda member: project.course.is_allowed_guest(member))
        if num_allowed_guests != len(users):
            raise exceptions.ValidationError({
                error_dict_field_name: (
                    f"Guest users must be in the '{project.course.allowed_guest_domain}' domain."
                )
            })


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
        raise exceptions.ValidationError({
            error_dict_field_name: (
                "Tried to add {} members, but the minimum "
                "for project '{}' is {}".format(
                    num_members, project.name,
                    project.min_group_size))})

    if num_members > project.max_group_size:
        raise exceptions.ValidationError({
            error_dict_field_name: (
                "Tried to add {} members, but the max "
                "for project '{}' is {}".format(
                    num_members, project.name,
                    project.max_group_size))})


def verify_at_least_one_user_in_group(users, project, error_dict_field_name):
    users = tuple(users)
    if len(users) < 1:
        raise exceptions.ValidationError({
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
            raise exceptions.ValidationError({
                error_dict_field_name: (
                    "User {} is already part of a submission "
                    "group for project '{}'".format(
                        member, project.name))})


def verify_users_can_be_in_group(users, project, error_dict_field_name,
                                 group_to_ignore=None,
                                 check_group_size_limits=True):
    """
    A shortcut for calling the above 4 "verify_" functions.
    """
    verify_users_have_same_enrollment_status(
        users, project, error_dict_field_name)
    if check_group_size_limits:
        verify_group_size_allowed_by_project(
            users, project, error_dict_field_name)
    verify_at_least_one_user_in_group(users, project, error_dict_field_name)
    verify_users_not_in_other_group(
        users, project, error_dict_field_name, group_to_ignore=group_to_ignore)
