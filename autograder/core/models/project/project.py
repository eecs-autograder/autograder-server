import os

from django.db import models
from django.core import validators
from django.core import exceptions

from ..ag_model_base import AutograderModel
from ..course import Course

import autograder.utilities.fields as ag_fields

import autograder.core.shared.utilities as ut


class Project(AutograderModel):
    """
    Represents a programming project for which students can
    submit solutions and have them evaluated.

    Related object fields:
        autograder_test_cases -- The autograder test cases that belong
            to this Project.

        student_test_suites -- The student test suites that belong to
            this Project.

        uploaded_files -- Resource files to be used in project test
            cases.

        expected_student_file_patterns -- Patterns that
            student-submitted files can or should match.
    """
    class Meta:
        unique_together = ('name', 'course')

    _DEFAULT_TO_DICT_FIELDS = [
        'name',
        'course',
        'visible_to_students',
        'closing_time',
        'disallow_student_submissions',
        'allow_submissions_from_non_enrolled_students',
        'min_group_size',
        'max_group_size',
    ]

    @classmethod
    def get_default_to_dict_fields(class_):
        return class_._DEFAULT_TO_DICT_FIELDS

    name = ag_fields.ShortStringField(
        help_text='''The name used to identify this project.
            Must be non-empty and non-null.
            Must be unique among Projects associated with
            a given course.
            This field is REQUIRED.''')

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

    disallow_student_submissions = models.BooleanField(
        default=False,
        help_text='''A hard override that will prevent
            students from submitting even if visible_to_students is
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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        project_root_dir = ut.get_project_root_dir(self)
        project_files_dir = ut.get_project_files_dir(self)
        project_submissions_dir = ut.get_project_submission_groups_dir(
            self)

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
