import os
import datetime

from django.db import models
from django.core import validators
from django.core import exceptions

from ..ag_model_base import AutograderModel
from ..course import Course

import autograder.core.utils as core_ut
import autograder.core.fields as ag_fields


class Project(AutograderModel):
    """
    Represents a programming project for which students can
    submit solutions and have them evaluated.

    Related object fields:
        autograder_test_cases -- The autograder test cases that belong
            to this Project.

        uploaded_files -- Resource files to be used in project test
            cases.

        expected_student_file_patterns -- Patterns that
            student-submitted files can or should match.

        submission_groups -- The submission groups registered for this
            Project.

        submission_group_invitations -- The pending submission group
            invitations belonging to this Project.
    """
    class Meta:
        unique_together = ('name', 'course')

    _DEFAULT_TO_DICT_FIELDS = frozenset([
        'name',
        'course',
        'visible_to_students',
        'closing_time',
        'soft_closing_time',
        'disallow_student_submissions',
        'allow_submissions_from_non_enrolled_students',
        'min_group_size',
        'max_group_size',

        'submission_limit_per_day',
        'allow_submissions_past_limit',
        'submission_limit_reset_time',

        'ultimate_submission_selection_method',
        'hide_ultimate_submission_fdbk',
    ])

    @classmethod
    def get_default_to_dict_fields(class_):
        return class_._DEFAULT_TO_DICT_FIELDS

    _EDITABLE_FIELDS = frozenset([
        'name',
        'visible_to_students',
        'closing_time',
        'soft_closing_time',
        'disallow_student_submissions',
        'allow_submissions_from_non_enrolled_students',
        'min_group_size',
        'max_group_size',

        'submission_limit_per_day',
        'allow_submissions_past_limit',
        'submission_limit_reset_time',

        'ultimate_submission_selection_method',
        'hide_ultimate_submission_fdbk',
    ])

    @classmethod
    def get_editable_fields(class_):
        return class_._EDITABLE_FIELDS

    name = ag_fields.ShortStringField(
        help_text='''The name used to identify this project.
            Must be non-empty and non-null.
            Must be unique among Projects associated with
            a given course.
            This field is REQUIRED.''')

    # -------------------------------------------------------------------------

    class UltimateSubmissionSelectionMethod:
        '''
        This class contains options for choosing which submissions are
        used for final grading. AG test cases also have a feedback
        option that will only be used for ultimate submissions.
        '''
        # The submission that was made most recently
        most_recent = 'most_recent'

        # The submission for which the student sees the highest basic
        # score. The basic score is the total score using the normal
        # feedback config for each test case.
        best_basic_score = 'best_basic_score'

        values = [most_recent, best_basic_score]

    # -------------------------------------------------------------------------

    course = models.ForeignKey(
        Course, related_name='projects',
        help_text='''The Course this project belongs to.
            This field is REQUIRED.''')

    visible_to_students = models.BooleanField(
        default=False,
        help_text='''Whether information about this Project can
            be viewed by students.''')

    closing_time = models.DateTimeField(
        default=None, null=True, blank=True,
        help_text='''The date and time that this project should stop
            accepting submissions.
            A value of None indicates that this project should
            stay open.''')

    soft_closing_time = models.DateTimeField(
        default=None, null=True, blank=True,
        help_text='''The date and time that should be displayed as the
            due date for this project. Unlike closing_time,
            soft_closing_time does not affect whether submissions are
            actually accepted.
            If not None and closing_time is not None, this value must be
            less than (before) closing_time.''')

    disallow_student_submissions = models.BooleanField(
        default=False,
        help_text='''A hard override that indicates that students should
            be prevented from submitting even if visible_to_students is
            True and it is before closing_time.''')

    allow_submissions_from_non_enrolled_students = models.BooleanField(
        default=False,
        help_text='''By default, only admins, staff members, and enrolled
            students for a given Course can submit to its Projects.
            When this field is set to True, submissions will be accepted
            from any authenticated Users, with the following caveats:
                - In order to view the Project, non-enrolled students
                must be given a direct link to a page where it can
                be viewed.
                - When group work is allowed, non-enrolled students can
                only be in groups with other non-enrolled students.''')

    min_group_size = models.IntegerField(
        default=1, validators=[validators.MinValueValidator(1)],
        help_text='''The minimum number of students that can work in a
            group on this project.
            Must be >= 1.
            Must be <= max_group_size.''')

    max_group_size = models.IntegerField(
        default=1, validators=[validators.MinValueValidator(1)],
        help_text='''The maximum number of students that can work in a
            group on this project.
            Must be >= 1.
            Must be >= min_group_size.''')

    submission_limit_per_day = models.IntegerField(
        default=None, null=True, blank=True,
        validators=[validators.MinValueValidator(1)],
        help_text='''The number of submissions each group is allowed per
            day before either reducing feedback or preventing further
            submissions. A value of None indicates no limit.''')

    allow_submissions_past_limit = models.BooleanField(
        default=True, blank=True,
        help_text='''Whether to allow additional submissions after a
            group has submitted submission_limit_per_day times.''')

    submission_limit_reset_time = models.TimeField(
        default=datetime.time,
        help_text='''The time that marks the beginning and end of the 24
            hour period during which submissions should be counted
            towards the daily limit. This value assumes use of the UTC
            timezone. Defaults to 0:0:0. ''')

    ultimate_submission_selection_method = ag_fields.ShortStringField(
        choices=zip(UltimateSubmissionSelectionMethod.values,
                    UltimateSubmissionSelectionMethod.values),
        default=UltimateSubmissionSelectionMethod.most_recent,
        blank=True,
        help_text='''The "ultimate" submission for a group is the one
            that will be used for final grading. This field specifies
            how the ultimate submission should be determined.''')

    hide_ultimate_submission_fdbk = models.BooleanField(
        default=True, blank=True,
        help_text='''A hard override that indicates that ultimate
            submission feedback should not be shown, even if the
            appropriate criteria are met.''')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        project_root_dir = core_ut.get_project_root_dir(self)
        project_files_dir = core_ut.get_project_files_dir(self)
        project_submissions_dir = core_ut.get_project_submission_groups_dir(self)

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

        if self.closing_time is not None and self.soft_closing_time is not None:
            if self.closing_time < self.soft_closing_time:
                raise exceptions.ValidationError(
                    {'soft_closing_time': (
                        'Soft closing time must be before hard closing time')})
