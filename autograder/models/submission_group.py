from django.db import models, transaction
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from autograder.models import Project

from autograder.models.model_utils import ModelValidatableOnSave


class _SubmissionGroupManager(models.Manager):
    @transaction.atomic
    def create_group(self, members, project, extended_due_date=None):
        group = self.create(
            project=project, extended_due_date=extended_due_date)
        group.members.add(*members)

        group.clean(_first_save=True)

        return group


class SubmissionGroup(ModelValidatableOnSave):
    """
    This class represents a group of students that can submit
    to a particular project.

    IMPORTANT: Do NOT use SubmissionGroup.objects.create() to create
        new groups. Always use SubmissionGroup.objects.create_group(). This
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
    # -------------------------------------------------------------------------

    # The extra field _first_save is used by the custom manager object
    # so that this function only does certain checks once object is ready
    # to be saved to the database.
    def clean(self, _first_save=False):
        if not self.pk and not _first_save:
            return

        num_members = self.members.count()
        if num_members < 1:
            raise ValidationError(
                "SubmissionGroups must have at least one member")

        if num_members > self.project.max_group_size:
            raise ValidationError(
                "Tried to add {} members, but the max "
                "for project {} is {}".format(
                    num_members, self.project.name,
                    self.project.max_group_size))

        # This check a bit strange and worth explaining:
        # We need to make sure that none of the members of this group
        # are already members of another group (for the associated project).
        # However, we know that this function won't run this check until
        # the object has been fully written to the database.
        # That means that when we query for duplicate submission groups,
        # *this submission group* is already recorded.
        # Therefore, we need to ignore this submission group when
        # checking to see if a user is already part of a group.
        for member in self.members.all():
            current_memberships = member.submission_groups.filter(
                project=self.project)
            if current_memberships.count() > 1:
                raise ValidationError(
                    "User {} is already part of a submission "
                    "group for project {}".format(
                        member.username, self.project.name))
