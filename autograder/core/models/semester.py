import os
import shutil
import functools
import itertools

from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import User

from autograder.core.models.utils import (
    ModelValidatableOnSave, ManagerWithValidateOnCreate)
from autograder.core.models import Course

import autograder.core.shared.global_constants as gc
import autograder.core.shared.utilities as ut


class Semester(ModelValidatableOnSave):
    """
    Represents a semester or term in which a course takes place.

    Fields:
        name -- The name used to identify this Semester.
                Must be non-empty and non-null.
                Must be unique among Semesters associated with a given Course.

        course -- The Course that this semester is associated with.

        staff -- Users that are staff members for this Semester.
            Staff members receive full feedback on autograder test cases
            and can view student submissions.

        enrolled_students -- Users that are enrolled in this Semester.
            Enrolled students can view all visible Projects associated
            with this Semester and may be in SubmissionGroups together.

    Related object fields:
        projects -- The group of Projects that belong to this Semester.

    Properties:
        semester_staff_names -- A list of usernames that are staff members for
            this Semester.

        enrolled_student_names -- A list of usernames that are enrolled
            students for this Semester.

    Static methods:
        get_staff_semesters_for_user()
        get_enrolled_semesters_for_user()

    Instance methods:
        add_semester_staff()
        remove_semester_staff()
        is_semester_staff()

        add_enrolled_students()
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

    staff = models.ManyToManyField(User, related_name='semesters_is_staff_for')

    enrolled_students = models.ManyToManyField(
        User, related_name='semesters_is_enrolled_in')

    @property
    def semester_staff_names(self):
        return set(
            itertools.chain(
                (user.username for user in self.staff.all()),
                (user.username for user in self.course.administrators.all())
            )
        )

    @property
    def enrolled_student_names(self):
        return set(user.username for user in self.enrolled_students.all())

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    @staticmethod
    def get_staff_semesters_for_user(user):
        """
        Returns an iterable of Semesters for which the given user is
        a staff member.
        Note that if user is an administrator for this Semester's Course,
        all Semesters for that Course will be returned.
        """
        return itertools.chain(
            user.courses_is_admin_for.all(),
            user.semesters_is_staff_for.all()
        )
        # return Semester.objects.filter(
        #     Q(_semester_staff_names__contains=[user.username]) |
        #     Q(course___course_admin_names__contains=[user.username])
        # )

    @staticmethod
    def get_enrolled_semesters_for_user(user):
        """
        Returns an iterable of Semesters for which the given user
        is an enrolled student.
        """
        return user.semesters_is_enrolled_in.all()

    # -------------------------------------------------------------------------

    def add_semester_staff(self, *users):
        """
        Adds the given Users to this Semester's list of staff members.
        Raises ValidationError if any of the Users are already staff members.
        """
        self.staff.add(*users)
        # for user in users:
        #     if not self.is_semester_staff(user):
        #         self._semester_staff_names.append(user.username)
        # self.save()

    def remove_semester_staff(self, *users):
        """
        Removes the given Users from this Semester's list of staff members.
        Raises ValidationError if any of the Users are not staff members.
        """
        self.staff.remove(*users)
        # for user in users:
        #     if not self.is_semester_staff(user):
        #         raise ValidationError("User is not staff for this semester")
        #     self._semester_staff_names.remove(user.username)
        # self.save()

    def is_semester_staff(self, user):
        """
        Returns True if the given user (can be a User object or string
        username) is a staff member for this Semester
        or a course admin for this Semester's course.
        Returns False otherwise.
        """
        return (
            self.staff.filter(pk=user.pk).exists() or
            self.course.is_administrator(user)
        )
        # @functools.singledispatch
        # def _is_semester_staff_impl(user, names, course):
        #     return user.username in names or course.is_administrator(user)

        # @_is_semester_staff_impl.register(str)
        # def _(username, names, course):
        #     return username in names or course.is_administrator(username)

        # return _is_semester_staff_impl(
        #     user, self._semester_staff_names, self.course)

    def add_enrolled_students(self, *users):
        """
        Adds the given User to this Semester's list of enrolled students.
        Raises ValidationError if any of the Users are already enrolled.
        """
        self.enrolled_students.add(*users)
        # for user in users:
        #     if not self.is_enrolled_student(user):
        #         self._enrolled_student_names.append(user.username)
        # self.save()

    def remove_enrolled_students(self, *users):
        """
        Removes the given Users from this Semester's list of enrolled students.
        Raises ValidationError if any or the Users are not enrolled.
        """
        self.enrolled_students.remove(*users)
        # for user in users:
        #     if not self.is_enrolled_student(user):
        #         raise ValidationError("User is not enrolled in this semester")
        #     self._enrolled_student_names.remove(user.username)
        # self.save()

    def is_enrolled_student(self, user):
        """
        Returns True if the given user (can be a User object or
        string username) is an enrolled student for
        this Semester. Returns False otherwise.
        """
        return self.enrolled_students.filter(pk=user.pk).exists()
        # @functools.singledispatch
        # def _is_enrolled_student_impl(user, names):
        #     return user.username in names

        # @_is_enrolled_student_impl.register(str)
        # def _(username, names):
        #     return username in names

        # return _is_enrolled_student_impl(user, self._enrolled_student_names)

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
