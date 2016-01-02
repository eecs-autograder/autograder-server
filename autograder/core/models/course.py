import os
import shutil
import functools

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import User

from autograder.core.models.utils import (
    ModelValidatableOnSave, ManagerWithValidateOnCreate)

import autograder.core.shared.global_constants as gc
import autograder.core.shared.utilities as ut


class Course(ModelValidatableOnSave):
    """
    Represents a programming course for which students will be submitting
    code to an autograder.

    Fields:
        name -- The name of this course.
                Must be unique, non-empty and non-null.

        administrators -- The Users that are administrators for
            this Course.

    Related object fields:
        semesters -- The group of Semesters that belong to this Course.

    Properties:
        administrator_names -- A list of usernames of Users
            that are administrators for this Course.

    Static methods:
        get_courses_for_user()

    Instance methods:
        add_administrator()
        remove_administrator()
        is_administrator()

    Overridden member functions:
        save()
        clean()
        delete()
    """
    objects = ManagerWithValidateOnCreate()

    # -------------------------------------------------------------------------

    name = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN, unique=True)

    administrators = models.ManyToManyField(
        User, related_name='courses_is_admin_for')

    @property
    def administrator_names(self):
        return tuple(user.username for user in self.administrators.all())

    # -------------------------------------------------------------------------

    # TODO: phase out
    @staticmethod
    def get_courses_for_user(user):
        """
        Returns a QuerySet of Courses for which the given user is an
        administrator, sorted by Course name.
        """
        return user.courses_is_admin_for.order_by('name')
        # return Course.objects.filter(
        #     _administrator_names__contains=[user.username]).order_by('name')

    # -------------------------------------------------------------------------

    def add_administrators(self, *users):
        """
        Adds the given Users to this Course's list of administrators.
        Users that are already in this list are ignored.
        """
        self.administrators.add(*users)
        # for user in users:
        #     if not self.is_administrator(user):
        #         self._administrator_names.append(user.username)
        # self.save()

    def remove_administrator(self, user):
        """
        Removes the given User from this Course's list of administrators.
        Raises ValidationError if the User is not an administrator
        for this course.
        """
        self.administrators.remove(user)
        # if not self.is_administrator(user):
        #     raise ValidationError(
        #         "This User is not an administrator for this Course")

        # self._administrator_names.remove(user.username)
        # self.save()

    def is_administrator(self, user):
        """
        Returns True if the given user (can be a User object or string
        username) is an administrator for this Course, False otherwise.
        """
        return self.administrators.filter(pk=user.pk).exists()
        # @functools.singledispatch
        # def _is_administrator_impl(user, names):
        #     return user.username in names

        # @_is_administrator_impl.register(str)
        # def _(username, names):
        #     return username in names

        # return _is_administrator_impl(user, self._administrator_names)

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

            # print('creating: ' + course_root_dir)
            os.makedirs(course_root_dir)

    def clean(self):
        if self.name:
            self.name = self.name.strip()

        errors = {}
        if not self.name:
            errors['name'] = "Name can't be empty"

        if errors:
            raise ValidationError(errors)

    def delete(self, *args, **kwargs):
        course_root_dir = ut.get_course_root_dir(self)
        super().delete(*args, **kwargs)

        shutil.rmtree(course_root_dir)
