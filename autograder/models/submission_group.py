import os

from django.db import models, transaction
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from autograder.models import Project
from autograder.models.utils import ModelValidatableOnSave

import autograder.shared.utilities as ut


class _SubmissionGroupManager(models.Manager):
    @transaction.atomic
    def create_group(self, members, project, extended_due_date=None):
        group = super().create(
            project=project, extended_due_date=extended_due_date)
        group.members.add(*members)

        group.clean(_first_save=True)
        group.save()

        return group

    def create(self, **kwargs):
        raise NotImplementedError(
            "The create() method is not supported for SubmissionGroup. "
            "Please use create_group() instead.")


class SubmissionGroup(ModelValidatableOnSave):
    """
    This class represents a group of students that can submit
    to a particular project.

    IMPORTANT:
        - Do NOT use SubmissionGroup.objects.create() to create
        new groups.
        - Do NOT use a normal constructor followed by a call to save()
        to create new groups.

        Always use SubmissionGroup.objects.create_group(). This
        function properly handles initialization and validation of the
        members field.

    Fields:
        members -- The Users that belong to this submission group.
            (A many-to-many relationship with User.)
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

    Overridden methods:
        clean()
        save()
    """
    # Custom manager so that we can pass a list of Users to the create()
    # method.
    objects = _SubmissionGroupManager()

    # -------------------------------------------------------------------------

    members = models.ManyToManyField(User, related_name='submission_groups')
    project = models.ForeignKey(Project)
    extended_due_date = models.DateTimeField(
        null=True, default=None, blank=True)

    # -------------------------------------------------------------------------

    def save(self, *args, **kwargs):
        # if not self.pk:
        #     raise NotImplementedError(
        #         'Do not use the save() method when saving a '
        #         'submission_group for the first time. '
        #         'Please use SubmissionGroup.objects.create_group to '
        #         'create new submission groups.')

        super().save(*args, **kwargs)

        submission_group_dir = ut.get_student_submission_group_dir(self)

        if not os.path.isdir(submission_group_dir):
            os.makedirs(submission_group_dir)

    def clean(self, _first_save=False):
        # Note: The extra field _first_save is used by the custom
        # manager object so that this function does certain checks
        # only when object is ready to be saved to the database.
        if not self.pk and not _first_save:
            return

        num_members = self.members.count()
        if num_members < 1:
            raise ValidationError(
                "SubmissionGroups must have at least one member")

        if num_members > self.project.max_group_size:
            raise ValidationError(
                "Tried to add {} members, but the max "
                "for project '{}' is {}".format(
                    num_members, self.project.name,
                    self.project.max_group_size))

        members = self.members.all()
        self._clean_group_members_for_enrollment(members)

        # This check a bit strange and worth explaining:
        # We need to make sure that none of the members of this group
        # are already members of another group (for the associated project).
        # However, we know that this function won't run this check until
        # the object has been fully written to the database.
        # That means that when we query for duplicate submission groups,
        # *this submission group* is already recorded.
        #
        # Therefore, we need to ignore this submission group when
        # checking to see if a user is already part of a group.
        for member in members:
            current_memberships = member.submission_groups.filter(
                project=self.project)
            if current_memberships.count() > 1:
                raise ValidationError(
                    "User {} is already part of a submission "
                    "group for project '{}'".format(
                        member.username, self.project.name))

    def _clean_group_members_for_enrollment(self, members):
        semester = self.project.semester
        num_enrolled = ut.count_if(
            members, lambda member: semester.is_enrolled_student(member))

        num_staff = ut.count_if(
            members, lambda member: semester.is_semester_staff(member))

        if num_staff:
            if num_staff != len(members):
                raise ValidationError(
                    "Groups with any staff members "
                    "must consist of only staff members")
            return

        if not self.project.allow_submissions_from_non_enrolled_students:
            if not num_enrolled or num_enrolled != len(members):
                raise ValidationError(
                    "This project only accepts submissions "
                    "from enrolled students.")
            return

        if num_enrolled and num_enrolled != len(members):
            raise ValidationError(
                "Non-enrolled students can only be in "
                "groups with other non-enrolled students.")
