import os
import shutil

from django.db import models
from django.core import validators
from django.contrib.auth.models import User

from .ag_model_base import AutograderModel

import autograder.core.shared.utilities as ut
import autograder.utilities.fields as ag_fields


class Course(AutograderModel):
    """
    Represents a programming course for which students will be submitting
    code to an autograder.

    Related object fields:
        semesters -- The group of Semesters that belong to this Course.
    """
    DEFAULT_INCLUDE_FIELDS = ['name']

    name = ag_fields.ShortStringField(
        unique=True,
        validators=[validators.MinLengthValidator(1)],
        help_text='''The name of this course.
                  Must be unique, non-empty and non-null.''')

    administrators = models.ManyToManyField(
        User, related_name='courses_is_admin_for',
        help_text='''The Users that are administrators for
                  this Course. Administrators have edit access
                  to this Course and its Semesters.''')

    @property
    def administrator_names(self):
        """
        The usernames of Users that are administrators for this Course.
        """
        return tuple(user.username for user in self.administrators.all())

    # -------------------------------------------------------------------------

    def is_administrator(self, user):
        """
        Convenience method for determining if the given user
        is an administrator.
        """
        return self.administrators.filter(pk=user.pk).exists()

    # -------------------------------------------------------------------------

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        course_root_dir = ut.get_course_root_dir(self)
        if not os.path.isdir(course_root_dir):
            # Since the database is in charge or validating the uniqueness
            # of this course, we can assume at this point that creating
            # the course directory will succeed. If for some reason it fails,
            # this will be considered a more severe error, and the OSError
            # thrown by os.makedirs will be handled at a higher level.

            os.makedirs(course_root_dir)
