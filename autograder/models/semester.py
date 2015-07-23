import os
import shutil
import copy

from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q

from django.contrib.postgres.fields import ArrayField

from autograder.models.model_utils import (
    ModelValidatableOnSave, ManagerWithValidateOnCreate)
from autograder.models import Course

import autograder.shared.global_constants as gc
import autograder.shared.utilities as ut


class Semester(ModelValidatableOnSave):
    """
    Represents a semester or term in which a course takes place.

    Fields:
        name -- The name used to identify this Semester.
                Must be non-empty and non-null.
                Must be unique among Semesters associated with a given Course.

        course -- The Course that this semester is associated with.

        projects -- A django manager object that can be used to query
            Projects that belong to this Semester.

        staff_members -- A list of usernames that are staff members for
            this Semester.
            This field is READ ONLY.

        enrolled_students -- A list of usernames that are enrolled students
            for this Semester.
            This field is READ ONLY.

    Static methods:
        get_staff_semesters_for_user()
        get_enrolled_semesters_for_user()

    Instance methods:
        add_semester_staff()
        remove_semester_staff()
        is_semester_staff()

        add_enrolled_student()
        remove_enrolled_student()
        is_enrolled_student()

    Overridden member functions:
        save()
        clean()
        delete()
    """
    class Meta:
        unique_together = ('name', 'course')

    objects = ManagerWithValidateOnCreate()

    # -------------------------------------------------------------------------

    name = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN)
    course = models.ForeignKey(Course, related_name='semesters')

    @property
    def staff_members(self):
        return copy.deepcopy(self._semester_staff)

    _semester_staff = ArrayField(
        models.CharField(max_length=gc.MAX_CHAR_FIELD_LEN),
        blank=True, default=list)

    @property
    def enrolled_students(self):
        return copy.deepcopy(self._enrolled_students)

    _enrolled_students = ArrayField(
        models.CharField(max_length=gc.MAX_CHAR_FIELD_LEN),
        blank=True, default=list)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    @staticmethod
    def get_staff_semesters_for_user(user):
        """
        Returns a QuerySet of Semesters for which the given user is
        a staff member, sorted by Semester name.
        Note that if user is an administrator for this Semester's Course,
        all Semesters for that Course will be returned.
        """
        return Semester.objects.filter(
            Q(_semester_staff__contains=[user.username]) |
            Q(course___course_admins__contains=[user.username])
        ).order_by('name')

    @staticmethod
    def get_enrolled_semesters_for_user(user):
        """
        Returns a QuerySet of Semesters for which the given user
        is an enrolled student, sorted by Semester name.
        """
        return Semester.objects.filter(
            _enrolled_students__contains=[user.username]).order_by('name')

    # -------------------------------------------------------------------------

    def add_semester_staff(self, user):
        """
        Adds the given User to this Semester's list of staff members.
        Raises ValidationError if the User is already a staff member.
        """
        if self.is_semester_staff(user):
            raise ValidationError("User is already staff for this semester")

        self._semester_staff.append(user.username)
        self.save()

    def remove_semester_staff(self, user):
        """
        Removes the given User from this Semester's list of staff members.
        Raises ValidationError if the User is not a staff member.
        """
        if not self.is_semester_staff(user):
            raise ValidationError("User is not staff for this semester")

        self._semester_staff.remove(user.username)
        self.save()

    def is_semester_staff(self, user):
        """
        Returns True if the given User is a staff member for this Semester.
        Returns False otherwise.
        """
        return user.username in self._semester_staff

    def add_enrolled_student(self, user):
        """
        Adds the given User to this Semester's list of enrolled students.
        Raises ValidationError if the User is already enrolled.
        """
        if self.is_enrolled_student(user):
            raise ValidationError("User is already enrolled in this semester")

        self._enrolled_students.append(user.username)
        self.save()

    def remove_enrolled_student(self, user):
        """
        Removes the given User from this Semester's list of enrolled students.
        Raises ValidationError if the User is not enrolled.
        """
        if not self.is_enrolled_student(user):
            raise ValidationError("User is not enrolled in this semester")

        self._enrolled_students.remove(user.username)
        self.save()

    def is_enrolled_student(self, user):
        """
        Returns True if the given User is an enrolled student for
        this Semester. Returns False otherwise.
        """
        return user.username in self._enrolled_students

    # -------------------------------------------------------------------------

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        semester_root_dir = ut.get_semester_root_dir(self)
        if not os.path.isdir(semester_root_dir):
            # Since the database is in charge or validating the uniqueness
            # of this semester, we can assume at this point that creating
            # the semester directory will succeed. If for some reason it fails,
            # this will be considered a more severe error, and the OSError
            # thrown by os.makedirs will be handled at a higher level.

            os.makedirs(semester_root_dir)

    def clean(self):
        if self.name:
            self.name = self.name.strip()

        errors = {}
        if not self.name:
            errors['name'] = "Name can't be empty"

        if errors:
            raise ValidationError(errors)

    def delete(self, *args, **kwargs):
        semester_root_dir = ut.get_semester_root_dir(self)
        super().delete(*args, **kwargs)

        shutil.rmtree(semester_root_dir)
