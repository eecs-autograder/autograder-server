import os

from django.db import models, transaction, connection
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError

from autograder.core.models import Project
from autograder.core.models.utils import (
    ModelValidatableOnSave, ManagerWithValidateOnCreate)

import autograder.core.shared.utilities as ut


class SubmissionGroupManager(ManagerWithValidateOnCreate):
    def validate_and_create(self, **kwargs):
        """
        Overridden for thread-safety with other attempts to create
        SubmissionGroups.
        """
        with transaction.atomic(), connection.cursor() as c:
            c.execute('LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE'.format(
                SubmissionGroup.objects.model._meta.db_table))

            return super().validate_and_create(**kwargs)


class SubmissionGroup(ModelValidatableOnSave):
    """
    This class represents a group of students that can submit
    to a particular project.

    Fields:
        members -- The names of Users that belong to this submission group.
            This list must contain at least one member and no
            more than project.max_group_size members.
            A User can only be a member of one submission group per project.
            This field is READ ONLY.
            This field is REQUIRED.
            IMPORTANT: This field cannot be queried over directly. Use the
                provided static methods instead.

        project -- The project that this SubmissionGroup belongs to.
            This field is REQUIRED.

        extended_due_date -- When this field is set, it indicates
            that members of this submission group can submit until
            this specified date, overriding the project closing time.
            Default value: None

        num_submissions_with_full_feedback -- TODO

    Static methods:
        get_groups_for_user()
        get_group()

    Overridden methods:
        clean()
        save()
    """
    objects = SubmissionGroupManager()

    # -------------------------------------------------------------------------

    @staticmethod
    def get_groups_for_user(username):
        """
        Returns a queryset of all SubmissionGroups that the user
        with the given username is a member of.
        """
        return SubmissionGroup.objects.filter(_members__contains=[username])

    # @staticmethod
    # def get_project_group_for_user(username, project):
    #     """
    #     Returns the SubmissionGroup that the user belongs to for the
    #     given project. Raises ObjectDoesNotExist if no such SubmissionGroup
    #     exists.
    #     """
    #     return SubmissionGroup.objects.get(
    #         _members__contains=[username], project=project)

    @staticmethod
    def get_group(usernames, project):
        """
        Returns the SubmissionGroup that contains the specified users for
        the given project.
        Raises ObjectDoesNotExist if no such SubmissionGroup
        exists.
        """
        return SubmissionGroup.objects.get(
            _members__contains=usernames, project=project)

    # -------------------------------------------------------------------------

    @property
    def members(self):
        return tuple(self._members)

    _members = ArrayField(models.CharField(max_length=30))
    project = models.ForeignKey(Project, related_name="submission_groups")
    extended_due_date = models.DateTimeField(
        null=True, default=None, blank=True)

    # -------------------------------------------------------------------------

    def __init__(self, *args, **kwargs):
        members = kwargs.pop('members', None)
        if members is None:  # and '_members' in kwargs:
            # __init__ is being called by the actual database
            return super().__init__(*args, **kwargs)

        # __init__ is being called by the user
        return super().__init__(*args, _members=members, **kwargs)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        submission_group_dir = ut.get_student_submission_group_dir(self)

        if not os.path.isdir(submission_group_dir):
            os.makedirs(submission_group_dir)

    def clean(self):
        if self.pk:
            return

        num_members = len(self._members)
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

        self._clean_group_members_for_enrollment(self._members)

        for member in self._members:
            current_memberships = SubmissionGroup.objects.filter(
                project=self.project, _members__contains=[member])

            if current_memberships.count():
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
