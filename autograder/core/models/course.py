from autograder.core.constants import MAX_CHAR_FIELD_LEN
import enum
import os

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.core import validators
from django.contrib.auth.models import User
from django.db.models import Case, When, Value
from typing import Iterable, Optional, Sequence, TypedDict, Union, cast

from .ag_model_base import AutograderModel, AutograderModelManager

import autograder.core.fields as ag_fields
import autograder.core.utils as core_ut


class Semester(enum.Enum):
    fall = 'Fall'
    winter = 'Winter'
    spring = 'Spring'
    summer = 'Summer'


class UserRolesDict(TypedDict):
    is_admin: bool
    is_staff: bool
    is_student: bool
    is_handgrader: bool


class Course(AutograderModel):
    """
    Represents a programming course for which students will be submitting
    code to an autograder.

    Related object fields:
        projects -- The group of Projects that belong to this Course.
    """
    objects = AutograderModelManager['Course']()

    class Meta:
        unique_together = ('name', 'semester', 'year')
        ordering = (
            'name',
            'year',
            Case(
                When(semester=Semester.winter, then=Value(1)),
                When(semester=Semester.spring, then=Value(2)),
                When(semester=Semester.summer, then=Value(3)),
                When(semester=Semester.fall, then=Value(4))
            ),
        )

        permissions = (
            ('create_course', 'Can create new courses and clone courses they are an admin for.'),
        )

    name = models.CharField(
        max_length=MAX_CHAR_FIELD_LEN,
        validators=[validators.MinLengthValidator(1)],
        help_text="The name of this course. Must be unique, non-empty and non-null.")

    semester = ag_fields.EnumField(Semester, blank=True, null=True, default=None)

    year = models.IntegerField(blank=True, null=True, default=None,
                               validators=[MinValueValidator(1950)])

    subtitle = models.CharField(
        max_length=MAX_CHAR_FIELD_LEN,
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

    allowed_guest_domain = models.CharField(
        max_length=MAX_CHAR_FIELD_LEN,
        blank=True,
        help_text="""When non-empty, indicates that guest users' usernames
                     must end with this string for them to be allowed access
                     to projects that allow guests.
                     When empty, indicates that all guests can access projects
                     in this course where guests are allowed access.""")

    def is_admin(self, user: User) -> bool:
        """
        Convenience method for determining if the given user
        is an admin.
        """
        return self.get_user_roles(user)['is_admin']

    def is_staff(self, user: User) -> bool:
        """
        Returns True if the given user is a staff member for this
        Course. Note that admins are also considered staff members.
        Returns False otherwise.
        """
        return self.get_user_roles(user)['is_staff']

    def is_handgrader(self, user: User) -> bool:
        """
        Returns True if the given user is a handgrader for this Course.
        Returns False otherwise.
        """
        return self.get_user_roles(user)['is_handgrader']

    def is_student(self, user: User) -> bool:
        """
        Returns True if the given user is an enrolled student for
        this Course. Returns False otherwise.
        """
        return self.get_user_roles(user)['is_student']

    def get_user_roles(self, user: User) -> UserRolesDict:
        # To prevent different permissions checks from causing redundant
        # cache hits, we'll store the user roles in self.
        user_roles_attr = f'_user_roles_{user.pk}'
        if hasattr(self, user_roles_attr):
            return cast(UserRolesDict, getattr(self, user_roles_attr))

        cache_key = f'course_{self.pk}_user_{user.pk}'
        user_roles = cast(Optional[UserRolesDict], cache.get(cache_key))

        if user_roles is None:
            is_admin = self.admins.filter(pk=user.pk).exists()
            user_roles = {
                'is_admin': is_admin,
                'is_staff': is_admin or self.staff.filter(pk=user.pk).exists(),
                'is_handgrader': self.handgraders.filter(pk=user.pk).exists(),
                'is_student': self.students.filter(pk=user.pk).exists(),
            }
            cache.set(cache_key, user_roles, timeout=None)

        setattr(self, user_roles_attr, user_roles)

        return user_roles

    def is_allowed_guest(self, user: User) -> bool:
        """
        If self.allowed_guest_domain is empty, returns True.
        If self.allowed_guest_domain is non-empty returns True if
        the given user's username ends with self.allowed_guest_domain.
        """
        if not self.allowed_guest_domain:
            return True

        return user.username.endswith(self.allowed_guest_domain)

    def clean(self) -> None:
        super().clean()

        duplicate_exists = Course.objects.exclude(
            pk=self.pk
        ).filter(
            name=self.name, semester=self.semester, year=self.year
        ).exists()
        if duplicate_exists:
            raise ValidationError('A course with this name, semester, and year already exists.')

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: Optional[str] = None,
        update_fields: Optional[Iterable[str]] = None
    ) -> None:
        super().save(force_insert, force_update, using, update_fields)

        course_root_dir = core_ut.get_course_root_dir(self)
        if not os.path.isdir(course_root_dir):
            # Since the database is in charge of validating the uniqueness
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
        'allowed_guest_domain',
        'last_modified',
    )
    EDITABLE_FIELDS = (
        'name',
        'semester',
        'year',
        'subtitle',
        'num_late_days',
        'allowed_guest_domain',
    )


class LateDaysRemaining(AutograderModel):
    objects = AutograderModelManager['LateDaysRemaining']()

    class Meta:
        unique_together = ('course', 'user')

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Remove in version 5.0.0
    old_late_days_remaining = models.IntegerField(
        validators=[validators.MinValueValidator(0)], blank=True, default=0)

    @property
    def late_days_remaining(self) -> int:
        return max(0, self._true_late_days_remaining)

    @late_days_remaining.setter
    def late_days_remaining(self, value: int) -> None:
        if value < 0:
            raise ValidationError({
                'late_days_remaining': 'This value cannot be negative.'
            })

        self._extra_late_days_granted += value - self._true_late_days_remaining

    @property
    def _true_late_days_remaining(self) -> int:
        return (
            self.course.num_late_days + self._extra_late_days_granted
            - self.late_days_used
        )

    _extra_late_days_granted = models.IntegerField(blank=True, default=0)
    late_days_used = models.IntegerField(
        blank=True, default=0, validators=[MinValueValidator(0)])


def clear_cached_user_roles(course_pk: int) -> None:
    keys = cache.client.iter_keys(f'course_{course_pk}_user_*', itersize=5000)
    cache.delete_many(list(keys))
