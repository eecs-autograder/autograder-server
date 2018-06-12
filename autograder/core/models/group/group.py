import os

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone

import django.contrib.postgres.fields as pg_fields
from typing import List

import autograder.core.utils as core_ut
from autograder import utils
from autograder.core import constants

from .. import ag_model_base
from ..project import Project

from ..submission import Submission

from . import verification


class GroupManager(ag_model_base.AutograderModelManager):
    def validate_and_create(self, members,
                            check_group_size_limits=True,
                            **kwargs):
        """
        New parameters:
            check_group_size_limits -- When False, validation of whether
                the number of users is within the specified project limits
                will NOT be run.
                Default value: True
        """
        with transaction.atomic():
            verification.verify_users_can_be_in_group(
                members, kwargs['project'], 'members',
                check_group_size_limits=check_group_size_limits)

            member_names = [
                user.username for user in sorted(members, key=lambda user: user.username)]
            group = self.model(_member_names=member_names, **kwargs)
            group.save()
            group.members.add(*members)
            group.full_clean()
            return group


class Group(ag_model_base.AutograderModel):
    """
    This class represents a group of students that can submit
    to a particular project.

    Related object fields:
        submissions -- The Submissions that this group has made for the
            associated Project.
    """

    class Meta:
        ordering = ('_member_names',)

    objects = GroupManager()

    members = models.ManyToManyField(
        User, related_name="groups_is_member_of",
        help_text="""The Users that belong to this submission group.
            This list must contain at least one member and no more than
            project.max_group_size members. A User can only be a member
            of one submission group per project.
            This field is REQUIRED.""")

    @property
    def member_names(self) -> List[str]:
        """A list of usernames of the group members, sorted alphabetically."""
        return self._member_names

    _member_names = pg_fields.ArrayField(
        models.CharField(max_length=constants.MAX_USERNAME_LEN),
        default=list,
        help_text="""A list of usernames of the group members, sorted alphabetically.
                     This field is updated automatically when self.members is updated
                     through self.validate_and_update""")

    project = models.ForeignKey(Project, related_name="groups",
                                on_delete=models.CASCADE)

    extended_due_date = models.DateTimeField(
        null=True, default=None, blank=True,
        help_text="""When this field is set, it indicates that members
            of this submission group can submit until this specified
            date, overriding the project closing time.
            Default value: None""")

    bonus_submissions_remaining = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="""The number of bonus submissions this group has left.
            This field is automatically initialized to self.project.num_bonus_submissions"""
    )

    @property
    def num_submissions(self) -> int:
        return self.submissions.count()

    @property
    def num_submits_towards_limit(self) -> int:
        """
        The number of submissions this group has made in the current 24
        hour period that are counted towards the daily submission limit.
        """
        # We put the filtering logic here so that we can prefetch all
        # submissions in the list groups view.
        start_datetime, end_datetime = core_ut.get_24_hour_period(
            self.project.submission_limit_reset_time,
            timezone.now().astimezone(self.project.submission_limit_reset_timezone))

        def _is_towards_limit(submission):
            return (start_datetime <= submission.timestamp < end_datetime
                    and submission.count_towards_daily_limit
                    and submission.status in Submission.GradingStatus.count_towards_limit_statuses)

        return utils.count_if(self.submissions.all(), _is_towards_limit)

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.bonus_submissions_remaining = self.project.num_bonus_submissions

        super().save(*args, **kwargs)

        group_dir = core_ut.get_student_group_dir(self)
        if not os.path.isdir(group_dir):
            os.makedirs(group_dir)

    def validate_and_update(self, check_group_size_limits=True, **kwargs):
        """
        New parameters:
            check_group_size_limits -- When False, validation of
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

            verification.verify_users_can_be_in_group(
                members, self.project, 'members',
                group_to_ignore=self,
                check_group_size_limits=check_group_size_limits)

            self.members.set(members, clear=True)
            self._member_names = [
                user.username for user in sorted(members, key=lambda user: user.username)]
            self.full_clean()
            self.save()

    SERIALIZABLE_FIELDS = (
        'pk',
        'project',
        'extended_due_date',
        'member_names',

        'bonus_submissions_remaining',

        'num_submissions',
        'num_submits_towards_limit',
    )

    EDITABLE_FIELDS = ('extended_due_date', 'bonus_submissions_remaining')
