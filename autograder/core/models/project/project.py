from __future__ import annotations

import datetime
import os
from typing import Any, Dict, Optional

from django.contrib.postgres.fields import ArrayField
from django.core import exceptions, validators
from django.db import models
from timezone_field import TimeZoneField  # type: ignore

import autograder.core.fields as ag_fields
import autograder.core.utils as core_ut
from autograder.core.constants import MAX_CHAR_FIELD_LEN
from autograder.django_enum import TextChoices

from ..ag_model_base import (
    AutograderModel, AutograderModelManager, DictSerializable, make_min_value_validator
)
from ..course import Course


class UltimateSubmissionPolicy(TextChoices):
    """
    This class contains options for choosing which submissions are
    used for final grading. AG test cases also have a feedback
    option that will only be used for ultimate submissions.
    """
    # The submission that was made most recently
    most_recent = 'most_recent'

    # The submission with the highest score, using "normal"
    # feedback settings to compute scores.
    best_with_normal_fdbk = 'best_basic_score'

    # The submission with the highest score. The score used
    # for comparison is computed using maximum feedback
    # settings.
    best = 'best'


def _max_num_applications_validator(value: object | None) -> None:
    if object is None:
        return

    return make_min_value_validator(1)(value)


class EarlySubmissionBonus(DictSerializable):
    """
    Contains data describing how to apply an early submission bonus to
    a group's most recent submission.
    """
    def __init__(
        self,
        *,
        num_hours_early: int,
        percent_bonus: int,
        use_soft_deadline: bool,
        max_num_applications: Optional[int],
    ):
        self.num_hours_early = num_hours_early
        self.percent_bonus = percent_bonus
        self.use_soft_deadline = use_soft_deadline
        self.max_num_applications = max_num_applications

    FIELD_VALIDATORS = {
        'num_hours_early': [make_min_value_validator(1)],
        'percent_bonus': [make_min_value_validator(0)],
        'max_num_applications': [_max_num_applications_validator],
    }

    FIELD_DESCRIPTIONS = {
        'num_hours_early': """The number of hours before the deadline
            a group's most recent submission must be to receive the bonus.""",
        'percent_bonus': """The bonus to be applied to the submission score, e.g.,
            if 'percent_bonus' is 10, we would compute "score * 1.10".
        """,
        'use_soft_deadline': """"When true, the number of hours early will be computed
            relative to the project's soft deadline. When false, the computation will
            use the project's hard deadline.
        """,
        'max_num_applications': """The maximum number of times to apply this bonus.
            When this field is null, there is no limit on how many times this bonus
            can be applied. For example, if 'num_hours_early' is 4 and the submission
            in question is 13 hours early, the bonus will be applied three times. If we
            set 'max_num_applications' to 2 in this same example, the bonus would
            only be applied twice.
        """.strip()  # For docs formatting
        + """\n\nMultiple applications of the bonus are applied additively. That is,
            if 'percent_bonus' is 5 and the bonus is to be applied twice, we would
            apply a single 10% bonus.
        """,
    }


class LateSubmissionPenalty(DictSerializable):
    """
    Contains data describing how to apply a late submission penalty to
    a group's most recent submission.

    Note that late submission penalties can only be computed relative to
    a soft deadline. However, it is still possible to use a hard deadline
    to prevent submissions after a given point in time.
    """
    def __init__(
        self,
        *,
        num_hours_late: int,
        round_up_to_num_hours_late: bool,
        percent_penalty: int,
        max_num_applications: Optional[int],
    ):
        self.num_hours_late = num_hours_late
        self.percent_penalty = percent_penalty
        self.round_up_to_num_hours_late = round_up_to_num_hours_late
        self.max_num_applications = max_num_applications

    FIELD_VALIDATORS = {
        'num_hours_late': [make_min_value_validator(1)],
        'percent_penalty': [make_min_value_validator(0)],
        'max_num_applications': [_max_num_applications_validator],
    }

    FIELD_DESCRIPTIONS = {
        'num_hours_late': """The number of hours before the deadline
            a group's most recent submission must be to receive the penalty.""",
        'percent_penalty': """The penalty to be applied to the submission score, e.g.,
            if 'percent_penalty' is 10, we would compute "score * 0.9".
        """,
        'round_up_to_num_hours_late': """"When true, the number of hours past
            the deadline will be rounded up to the nearest multiple of 'num_hours_late'.
            For example, if 'num_hours_late' is 1 and the submission in question
            is 30 minutes late, the penalty would be applied once if this field is
            true and zero times if this field is false.
        """,
        'max_num_applications': """The maximum number of times to apply this penalty.
            When this field is null, there is no limit on how many times this penalty
            can be applied. For example, if 'num_hours_late' is 4 and the submission
            in question is 13 hours late, the penalty will be applied three times. If we
            set 'max_num_applications' to 2 in this same example, the penalty would
            only be applied twice.
        """.strip()  # For docs formatting
        + """\n\nMultiple applications of the penalty are applied additively. That is,
            if 'percent_penalty' is 5 and the penalty is to be applied twice, we would
            apply a single 10% penalty.
        """,
    }


class Project(AutograderModel):
    """
    Represents a programming project for which students can
    submit solutions and have them evaluated.

    Related object fields:
        instructor_files -- Resource files to be used in project test
            cases. In the API, this field is hidden from non-staff.

        expected_student_files -- Patterns that
            student-submitted files can or should match.

        groups -- The submission groups registered for this
            Project.

        group_invitations -- The pending submission group
            invitations belonging to this Project.
    """
    objects = AutograderModelManager['Project']()

    class Meta:
        unique_together = ('name', 'course')

    name = models.CharField(
        max_length=MAX_CHAR_FIELD_LEN,
        help_text="""The name used to identify this project.
            Must be non-empty and non-null.
            Must be unique among Projects associated with
            a given course.
            This field is REQUIRED.""")

    course = models.ForeignKey(
        Course, related_name='projects',
        on_delete=models.CASCADE,
        help_text="""The Course this project belongs to.
            This field is REQUIRED.""")

    visible_to_students = models.BooleanField(
        default=False,
        help_text="""Whether information about this Project can
            be viewed by students.""")

    closing_time = models.DateTimeField(
        default=None, null=True, blank=True,
        help_text="""The date and time that this project should stop
            accepting submissions.
            A value of None indicates that this project should
            stay open.
            In the API, this field is hidden from non-admins.""")

    soft_closing_time = models.DateTimeField(
        default=None, null=True, blank=True,
        help_text="""The date and time that should be displayed as the
            due date for this project. Unlike closing_time,
            soft_closing_time does not affect whether submissions are
            actually accepted.
            If not None and closing_time is not None, this value must be
            less than (before) closing_time.""")

    disallow_student_submissions = models.BooleanField(
        default=False,
        help_text="""A hard override that indicates that students should
            be prevented from submitting even if visible_to_students is
            True and it is before closing_time.""")

    disallow_group_registration = models.BooleanField(
        default=False,
        help_text="""A hard override that indicates that students should
            not be able to send, accept, or reject group
            invitations.""")

    guests_can_submit = models.BooleanField(
        default=False,
        help_text="""By default, only admins, staff, and students
            for a given Course can view and submit to its Projects.
            When True, submissions will be accepted from guests
            with the following caveats:
                - Guests must be given a direct link to the project.
                - When group work is allowed, guests can
                only be in groups with other guests.""")

    min_group_size = models.IntegerField(
        default=1, validators=[validators.MinValueValidator(1)],
        help_text="""The minimum number of students that can work in a
            group on this project.
            Must be >= 1.
            Must be <= max_group_size.""")

    max_group_size = models.IntegerField(
        default=1, validators=[validators.MinValueValidator(1)],
        help_text="""The maximum number of students that can work in a
            group on this project.
            Must be >= 1.
            Must be >= min_group_size.""")

    submission_limit_per_day = models.IntegerField(
        default=None, null=True, blank=True,
        validators=[validators.MinValueValidator(1)],
        help_text="""The number of submissions each group is allowed per
            day before either reducing feedback or preventing further
            submissions. A value of None indicates no limit.""")

    groups_combine_daily_submissions = models.BooleanField(
        default=False, blank=True,
        help_text="""If True, group members can "pool" their daily submissions.
            For example, if submission_limit_per_day is 3,
            a group with 2 members would get 6 submissions per day.""")

    allow_submissions_past_limit = models.BooleanField(
        default=True, blank=True,
        help_text="""Whether to allow additional submissions after a
            group has submitted submission_limit_per_day times.""")

    submission_limit_reset_time = models.TimeField(
        default=datetime.time,
        help_text="""The time that marks the beginning and end of the 24
            hour period during which submissions should be counted
            towards the daily limit. Defaults to 00:00:00.""")

    submission_limit_reset_timezone = TimeZoneField(
        default='UTC',
        help_text="""The timezone to use when computing how many
            submissions a group has made in a 24 hour period.""")

    num_bonus_submissions = models.IntegerField(
        default=0, validators=[validators.MinValueValidator(0)])

    total_submission_limit = models.IntegerField(
        default=None, blank=True, null=True,
        validators=[validators.MinValueValidator(1)],
        help_text="""The maximum number of times a Group can submit to
            this Project EVER.""")

    allow_late_days = models.BooleanField(
        default=False,
        help_text="""Whether to allow the use of late days for submitting
            past the deadline.""")

    early_submission_bonuses = ArrayField(
        ag_fields.ValidatedJSONField(EarlySubmissionBonus),
        blank=True, default=list,
        help_text="""A list of objects describing this project's early
            submission bonus policy. The bonuses computed from this list
            are applied additively, i.e., if there is one entry that grants
            a 5% bonus for being 4 hours early and another that grants a 3%
            bonus for being 8 hours early, a submission that is 8 hours early
            will receive an 8% bonus.
        """
    )

    late_submission_penalties = ArrayField(
        ag_fields.ValidatedJSONField(LateSubmissionPenalty),
        blank=True, default=list,
        help_text="""A list of objects describing this project's late
            submission penalty policy. The penalties computed from this list
            are applied additively, i.e., if there is one entry that applies
            a 5% penalty for being 4 hours late and another that applies a 3%
            penalty for being 8 hours late, a submission that is 8 hours late
            will receive an 8% penalty.
        """
    )

    ultimate_submission_policy = models.TextField(
        choices=UltimateSubmissionPolicy.choices,
        default=UltimateSubmissionPolicy.most_recent,
        blank=True,
        help_text="""The "ultimate" submission for a group is the one
            that will be used for final grading. This field specifies
            how the ultimate submission should be determined.""")

    hide_ultimate_submission_fdbk = models.BooleanField(
        default=True, blank=True,
        help_text="""A hard override that indicates that ultimate
            submission feedback should not be shown, even if the
            appropriate criteria are met.""")

    send_email_on_submission_received = models.BooleanField(
        default=False, blank=True,
        help_text="""If True, users will receive a confirmation email
            every time a submission of theirs is recorded in the
            database."""
    )

    send_email_on_non_deferred_tests_finished = models.BooleanField(
        default=False, blank=True,
        help_text="""If True, users will receive a confirmation email
            once all non-deferred test cases for their submission are
            finished grading."""
    )

    use_honor_pledge = models.BooleanField(
        default=False, blank=True,
        help_text="""If True, then the frontend website should require
            students to acknowledge an honor pledge. The text of the
            honor pledge is stored in honor_pledge_text."""
    )

    honor_pledge_text = models.TextField(
        blank=True,
        help_text="""The text of the honor pledge to display."""
    )

    def save(self, *args: Any, **kwargs: Any) -> None:
        super().save(*args, **kwargs)

        project_root_dir = core_ut.get_project_root_dir(self)
        project_files_dir = core_ut.get_project_files_dir(self)
        project_submissions_dir = core_ut.get_project_groups_dir(self)

        if not os.path.isdir(project_root_dir):
            # Since the database is in charge of validating the
            # uniqueness of this project, we can assume at this point
            # that creating the project directories will succeed.
            # If for some reason it fails, this will be considered a
            # more severe error, and the OSError thrown by os.makedirs
            # will be handled at a higher level.

            os.makedirs(project_root_dir)
            os.mkdir(project_files_dir)
            os.mkdir(project_submissions_dir)

    def clean(self) -> None:
        super().clean()

        if self.max_group_size < self.min_group_size:
            raise exceptions.ValidationError(
                {'max_group_size': ('Maximum group size must be greater than '
                                    'or equal to minimum group size')})

        if self.closing_time is not None:
            self.closing_time = self.closing_time.replace(second=0, microsecond=0)
        if self.soft_closing_time is not None:
            self.soft_closing_time = self.soft_closing_time.replace(second=0, microsecond=0)

        if self.closing_time is not None and self.soft_closing_time is not None:
            if self.closing_time < self.soft_closing_time:
                raise exceptions.ValidationError(
                    {'soft_closing_time': (
                        'Soft closing time must be before hard closing time')})

        # FIXME make sure closing times are not null when early/late bonuses are used

    @property
    def has_handgrading_rubric(self) -> bool:
        """
        Whether this project has a handgrading rubric.
        """
        return hasattr(self, 'handgrading_rubric')

    def to_dict(self) -> Dict[str, object]:
        result = super().to_dict()
        result['submission_limit_reset_timezone'] = (
            self.submission_limit_reset_timezone.tzname(None))
        return result

    SERIALIZABLE_FIELDS = (
        'pk',
        'name',
        'last_modified',
        'course',
        'visible_to_students',
        'closing_time',
        'soft_closing_time',
        'disallow_student_submissions',
        'disallow_group_registration',
        'guests_can_submit',
        'min_group_size',
        'max_group_size',

        'submission_limit_per_day',
        'allow_submissions_past_limit',
        'groups_combine_daily_submissions',
        'submission_limit_reset_time',
        'submission_limit_reset_timezone',

        'num_bonus_submissions',

        'total_submission_limit',

        'allow_late_days',
        'early_submission_bonuses',
        'late_submission_penalties',

        'ultimate_submission_policy',
        'hide_ultimate_submission_fdbk',

        'instructor_files',
        'expected_student_files',

        'has_handgrading_rubric',

        'send_email_on_submission_received',
        'send_email_on_non_deferred_tests_finished',

        'use_honor_pledge',
        'honor_pledge_text',
    )

    SERIALIZE_RELATED = (
        'instructor_files',
        'expected_student_files',
    )

    EDITABLE_FIELDS = (
        'name',
        'visible_to_students',
        'closing_time',
        'soft_closing_time',
        'disallow_student_submissions',
        'disallow_group_registration',
        'guests_can_submit',
        'min_group_size',
        'max_group_size',

        'submission_limit_per_day',
        'allow_submissions_past_limit',
        'groups_combine_daily_submissions',
        'submission_limit_reset_time',
        'submission_limit_reset_timezone',

        'num_bonus_submissions',

        'total_submission_limit',

        'allow_late_days',

        'ultimate_submission_policy',
        'hide_ultimate_submission_fdbk',

        'send_email_on_submission_received',
        'send_email_on_non_deferred_tests_finished',

        'use_honor_pledge',
        'honor_pledge_text',
    )
