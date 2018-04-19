import os
from typing import Iterable, List

from django.db import models
from django.core import validators
from django.contrib.auth.models import User

from .ag_model_base import AutograderModel

import autograder.core.fields as ag_fields
import autograder.core.utils as core_ut


class Course(AutograderModel):
    """
    Represents a programming course for which students will be submitting
    code to an autograder.

    Related object fields:
        projects -- The group of Projects that belong to this Course.
    """
    name = ag_fields.ShortStringField(
        unique=True,
        validators=[validators.MinLengthValidator(1)],
        help_text='''The name of this course.
                  Must be unique, non-empty and non-null.''')

    admins = models.ManyToManyField(
        User, related_name='courses_is_admin_for',
        help_text='''The Users that are admins for
                  this Course. admins have edit access
                  to this Course.''')

    staff = models.ManyToManyField(
        User, related_name='courses_is_staff_for',
        help_text='''Users that are staff members for this Course.
            Staff members receive full feedback on autograder test
            cases and can view student submissions.''')

    handgraders = models.ManyToManyField(
        User, related_name='courses_is_handgrader_for',
        help_text='''Users that are handgraders for this Course.
            Handgraders can view best submissions from students
            and edit the Handgrading Result''')

    students = models.ManyToManyField(
        User, related_name='courses_is_enrolled_in',
        help_text='''Users that are enrolled in this Course.
                  Enrolled students can view all visible Projects
                  associated with this Course and may be in
                  SubmissionGroups together.''')

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
        return (self.staff.filter(pk=user.pk).exists() or
                self.admins.filter(pk=user.pk).exists())

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

    SERIALIZABLE_FIELDS = ('pk', 'name', 'last_modified',)
    EDITABLE_FIELDS = ('name',)
