import os

from django.contrib.auth.models import User
from django.db import models, transaction
from django.utils import timezone

from .. import ag_model_base
from .. project import Project
import autograder.core.shared.utilities as ut

from . import verification


class SubmissionGroupManager(ag_model_base.AutograderModelManager):
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
    _DEFAULT_TO_DICT_FIELDS = [
        'project',
        'extended_due_date',
        'member_names',

        'num_submits_towards_limit',
    ]

    @classmethod
    def get_default_to_dict_fields(class_):
        return class_._DEFAULT_TO_DICT_FIELDS

    @classmethod
    def get_editable_fields(class_):
        return ['extended_due_date']

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
        help_text="""When this field is set, it indicates that members
            of this submission group can submit until this specified
            date, overriding the project closing time. Default value:
            None""")

    @property
    def member_names(self):
        """
        The usernames of the members of this SubmissionGroup.
        """
        return list(user.username for user in self.members.all())

    @property
    def num_submits_towards_limit(self):
        '''
        The number of submissions this group has made in the current 24
        hour period that are counted towards the daily submission limit.
        '''
        start_datetime, end_datetime = ut.get_24_hour_period(
            self.project.submission_limit_reset_time, timezone.now())
        return self.submissions.filter(
            timestamp__gte=start_datetime,
            timestamp__lt=end_datetime,
            count_towards_daily_limit=True
        ).count()

    @property
    def submission_with_best_basic_score(self):
        '''
        The Submission belonging to this group that has the highest
        score, as calculated using the normal feedback configuration
        for each test case.
        In the event of a tie, returns the more recent submission.
        '''
        # Submissions are ordered by pk, descending, so the max function
        # will automatically return the more recent one in the event of
        # a tie.
        return max(self.submissions.all(), key=lambda sub: sub.basic_score)

    @property
    def ultimate_submission(self):
        if (self.project.ultimate_submission_selection_method ==
                Project.UltimateSubmissionSelectionMethod.most_recent):
            return self.submissions.first()

        if (self.project.ultimate_submission_selection_method ==
                Project.UltimateSubmissionSelectionMethod.best_basic_score):
            return self.submission_with_best_basic_score

        raise Exception('Invalid ultimate submission selection method ' +
                        self.project.ultimate_submission_selection_method)

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

            self.members.set(members)
            self.full_clean()
