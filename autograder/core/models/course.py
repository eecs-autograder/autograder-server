import enum
import os

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.core import validators
from django.contrib.auth.models import User
from django.db.models import Case, When, Value

from .ag_model_base import AutograderModel

import autograder.core.fields as ag_fields
import autograder.core.utils as core_ut


class Semester(enum.Enum):
    fall = 'Fall'
    winter = 'Winter'
    spring = 'Spring'
    summer = 'Summer'


class Course(AutograderModel):
    """
    Represents a programming course for which students will be submitting
    code to an autograder.

    Related object fields:
        projects -- The group of Projects that belong to this Course.
    """

    class Meta:
        unique_together = ('name', 'semester', 'year')
        ordering = (
            'name',
            Case(
                When(semester=Semester.fall, then=Value(1)),
                When(semester=Semester.winter, then=Value(2)),
                When(semester=Semester.spring, then=Value(3)),
                When(semester=Semester.summer, then=Value(4))
            ),
            'year'
        )

        permissions = (
            ('create_course', 'Can create new courses and clone courses they are an admin for.'),
        )

    name = ag_fields.ShortStringField(
        validators=[validators.MinLengthValidator(1)],
        help_text="The name of this course. Must be unique, non-empty and non-null.")

    semester = ag_fields.EnumField(Semester, blank=True, null=True, default=None)

    year = models.IntegerField(blank=True, null=True, default=None,
                               validators=[MinValueValidator(1950)])

    subtitle = ag_fields.ShortStringField(
        blank=True, help_text='An optional descriptive name for the course.')

    num_late_days = models.IntegerField(
        default=0, validators=[validators.MinValueValidator(0)],
        help_text="The number of late days to give to users submitting to this course's projects."
    )

    admins = models.ManyToManyField(
        User, related_name='courses_is_admin_for',
        help_text="""The Users that are admins for this Course.
                     Admins have edit privileges for this Course.""")

    staff = models.ManyToManyField(
        User, related_name='courses_is_staff_for',
        help_text="""Users that are staff members for this Course.
            Staff members receive full feedback on autograder test
            cases and can view student submissions.""")

    handgraders = models.ManyToManyField(
        User, related_name='courses_is_handgrader_for',
        help_text="""Users that are handgraders for this Course.
            Handgraders can view best submissions from students
            and edit the Handgrading Result""")

    students = models.ManyToManyField(
        User, related_name='courses_is_enrolled_in',
        help_text="""Users that are enrolled in this Course.
                     Enrolled students can view all visible Projects
                     associated with this Course and may be in
                     groups together.""")

    def is_admin(self, user: User) -> bool:
        """
        Convenience method for determining if the given user
        is an admin.
        """
        return self.admins.filter(pk=user.pk).exists()

    def is_staff(self, user: User) -> bool:
        """
        Returns True if the given user is a staff member for this
        Course. Note that admins are also considered staff members.
        Returns False otherwise.
        """
        return (self.staff.filter(pk=user.pk).exists()
                or self.admins.filter(pk=user.pk).exists())

    def is_handgrader(self, user: User) -> bool:
        """
        Returns True if the given user is a handgrader for this Course.
        Returns False otherwise.
        """
        return self.handgraders.filter(pk=user.pk).exists()

    def is_student(self, user):
        """
        Returns True if the given user is an enrolled student for
        this Course. Returns False otherwise.
        """
        return self.students.filter(pk=user.pk).exists()

    def clean(self):
        super().clean()

        duplicate_exists = Course.objects.exclude(
            pk=self.pk
        ).filter(
            name=self.name, semester=self.semester, year=self.year
        ).exists()
        if duplicate_exists:
            raise ValidationError('A course with this name, semester, and year already exists.')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        course_root_dir = core_ut.get_course_root_dir(self)
        if not os.path.isdir(course_root_dir):
            # Since the database is in charge or validating the uniqueness
            # of this course, we can assume at this point that creating
            # the course directory will succeed. If for some reason it fails,
            # this will be considered a more severe error, and the OSError
            # thrown by os.makedirs will be handled at a higher level.

            os.makedirs(course_root_dir)

    SERIALIZABLE_FIELDS = (
        'pk',
        'name',
        'semester',
        'year',
        'subtitle',
        'num_late_days',
        'last_modified'
    )
    EDITABLE_FIELDS = (
        'name',
        'semester',
        'year',
        'subtitle',
        'num_late_days'
    )


class LateDaysRemaining(AutograderModel):
    class Meta:
        unique_together = ('course', 'user')

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    late_days_remaining = models.IntegerField(validators=[validators.MinValueValidator(0)],
                                              blank=True)

    def save(self, *args, **kwargs):
        if self.pk is None and self.late_days_remaining is None:
            self.late_days_remaining = self.course.num_late_days

        return super().save(*args, **kwargs)
