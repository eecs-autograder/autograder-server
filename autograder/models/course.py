import os
import shutil
import copy

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField

from autograder.models.utils import (
    ModelValidatableOnSave, ManagerWithValidateOnCreate)

import autograder.shared.global_constants as gc
import autograder.shared.utilities as ut


class Course(ModelValidatableOnSave):
    """
    Represents a programming course for which students will be submitting
    code to an autograder.

    Fields:
        name -- The name of this course.
                Must be unique, non-empty and non-null.

        semesters -- A django manager object that can be used to query
            Semesters that belong to this Course.

        course_admin_names -- A list of usernames that are administrators for
            this Course.
            This field is READ ONLY.

    Static methods:
        get_courses_for_user()

    Instance methods:
        add_course_admin()
        remove_course_admin()
        is_course_admin()

    Overridden member functions:
        save()
        clean()
        delete()
    """
    objects = ManagerWithValidateOnCreate()

    # -------------------------------------------------------------------------

    name = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN, unique=True)

    @property
    def course_admin_names(self):
        return copy.deepcopy(self._course_admin_names)

    _course_admin_names = ArrayField(
        models.CharField(max_length=gc.MAX_CHAR_FIELD_LEN),
        blank=True, default=list)

    # -------------------------------------------------------------------------

    @staticmethod
    def get_courses_for_user(user):
        """
        Returns a QuerySet of Courses for which the given user is an
        administrator, sorted by Course name.
        """
        return Course.objects.filter(
            _course_admin_names__contains=[user.username]).order_by('name')

    # -------------------------------------------------------------------------

    def add_course_admins(self, *users):
        """
        Adds the given Users to this Course's list of administrators.
        Users that are already in this list are ignored.
        """
        for user in users:
            if not self.is_course_admin(user):
                self._course_admin_names.append(user.username)
        self.save()

    def remove_course_admin(self, user):
        """
        Removes the given User from this Course's list of administrators.
        Raises ValidationError if the User is not an administrator
        for this course.
        """
        if not self.is_course_admin(user):
            raise ValidationError(
                "This User is not an administrator for this Course")

        self._course_admin_names.remove(user.username)
        self.save()

    def is_course_admin(self, user):
        """
        Returns True if the given User is an administrator for this Course,
        False otherwise.
        """
        return user.username in self._course_admin_names

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
