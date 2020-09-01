import datetime
import enum
import os

from django.core import exceptions, validators
from django.db import models
from timezone_field import TimeZoneField

import autograder.core.fields as ag_fields
import autograder.core.utils as core_ut

from ..ag_model_base import (AutograderModel, DictSerializableMixin,
                             make_max_value_validator,
                             make_min_value_validator)
from ..course import Course


class UltimateSubmissionPolicy(enum.Enum):
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


class EarlySubmissionBonus(DictSerializableMixin):
    """
    Contains options for applying an early submission bonus.
    """
    def __init__(self,
                 per_num_hours: int = 24,
                 percent_bonus: int = 0,
                 max_percent_bonus: int = 10,
                 use_hard_deadline: bool = False):
        self.per_num_hours = per_num_hours
        self.percent_bonus = percent_bonus
        self.max_percent_bonus = max_percent_bonus
        self.use_hard_deadline = use_hard_deadline

    SERIALIZABLE_FIELDS = [
        'per_num_hours',
        'percent_bonus',
        'max_percent_bonus',
        'use_hard_deadline',
    ]

    FIELD_DESCRIPTIONS = {
        'per_num_hours': (
            'The number of hours early a final graded submission must '
            'have been made in order to receive the bonus.\n'
            'For example, if this value is 6 hours and percent_bonus '
            'is 5%, then students will receive a 5% bonus for submitting '
            '6 hours early, a 10% bonus for submitting 12 hours early, etc.\n'
            'This value must be >= 1.'
        ),
        'percent_bonus': (
            'An integer between 0 and 100 representing the percentage '
            'of the total points awarded that should be added as a bonus.'
        ),
        'max_percent_bonus': 'The maximum bonus percentage to award. Must be >= 0.',
        'use_hard_deadline': (
            'By default, bonuses are calculated relative to the '
            'soft deadline. When this field is true, the calculations will'
            'use the hard deadline instead.\n'
            "If this value is true, the project's (hard) closing time must not be null."
        ),
    }

    FIELD_VALIDATORS = {
        'per_num_hours': [make_min_value_validator(1)],
        'percent_bonus': [
            make_min_value_validator(0),
            make_max_value_validator(100),
        ],
        'max_percent_bonus': [make_min_value_validator(0)],
    }


class LateSubmissionPenalty(DictSerializableMixin):
    """
    Contains options for applying a late submission penalty.
    """
    def __init__(self,
                 per_num_hours: int = 24,
                 percent_penalty: int = 0,
                 max_percent_penalty: int = 100):
        self.per_num_hours = per_num_hours
        self.percent_penalty = percent_penalty
        self.max_percent_penalty = max_percent_penalty

    SERIALIZABLE_FIELDS = [
        'per_num_hours',
        'percent_penalty',
        'max_percent_penalty',
    ]

    FIELD_DESCRIPTIONS = {
        'per_num_hours': (
            'Unlike early submission bonuses, late submission penalties '
            'start being applied as soon as the soft deadline passes.\n'
            'This value is the frequency with which to increase the '
            'percentage deducted.\n'
            'For example, if this value is 6 and percent_penalty is 2%, '
            'then a submission that is 5h59m late or less will receive a '
            '2% deduction, a submission that between 6h and 11h59m late will '
            'receive a 4% deduction, etc.\n'
            'This value must be >= 1.'
        ),
        'percent_penalty': (
            'An integer between 0 and 100 representing the percentage '
            'of the total points awarded that should be deducted.'
        ),
        'max_percent_penalty': 'The maximum percentage to deduct. Must be >= 0.'
    }

    FIELD_VALIDATORS = {
        'per_num_hours': [make_min_value_validator(1)],
        'percent_penalty': [
            make_min_value_validator(0),
            make_max_value_validator(100),
        ],
        'max_percent_penalty': [make_min_value_validator(0)],
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
    class Meta:
        unique_together = ('name', 'course')

    name = ag_fields.ShortStringField(
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

    use_early_submission_bonus = models.BooleanField(
        default=False,
        help_text="""Whether to apply an early submission bonus to students'
            final graded submissions. If this value is true, then
            ultimate_submission_policy must be "most_recent".
        """)

    early_submission_bonus = ag_fields.ValidatedJSONField(
        EarlySubmissionBonus, default=EarlySubmissionBonus)

    use_late_submission_penalty = models.BooleanField(
        default=False,
        help_text="""Whether to apply a late submission penalty to students'
            final graded submissions. If this value is true, then
            ultimate_submission_policy must be "most_recent" and
            "allow_late_days" must be false.
        """)

    late_submission_penalty = ag_fields.ValidatedJSONField(
        LateSubmissionPenalty, default=LateSubmissionPenalty)

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

    ultimate_submission_policy = ag_fields.EnumField(
        UltimateSubmissionPolicy,
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

    def save(self, *args, **kwargs):
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

    def clean(self):
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

        if self.use_early_submission_bonus:
            if (self.early_submission_bonus.use_hard_deadline
                    and self.closing_time is None):
                raise exceptions.ValidationError({
                    'closing_time': (
                        'Hard closing time must not be null when '
                        'an early submission bonus uses the hard closing time.'
                    )
                })

        if self.use_late_submission_penalty and self.allow_late_days:
            raise exceptions.ValidationError({
                'allow_late_days': (
                    'Late day tokens cannot be used in projects that apply a '
                    'late submission penalty.'
                )
            })

        if ((self.use_early_submission_bonus or self.use_late_submission_penalty)
                and self.ultimate_submission_policy != UltimateSubmissionPolicy.most_recent):
            raise exceptions.ValidationError({
                'ultimate_submission_policy': (
                    'Final graded submission policy must be "most recent" when using '
                    'an early submission bonus or late submission penalty.'
                )
            })

        if (self.use_late_submission_penalty
                and self.use_early_submission_bonus
                and self.early_submission_bonus.use_hard_deadline):
            raise exceptions.ValidationError({
                'early_submission_bonus':
                    'Early submission bonuses cannot be calculated using the hard deadline '
                    'when a late submission penalty is also in use.'
            })

    @property
    def has_handgrading_rubric(self) -> bool:
        """
        Whether this project has a handgrading rubric.
        """
        return hasattr(self, 'handgrading_rubric')

    def to_dict(self):
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
