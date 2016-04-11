import os
import shutil
import itertools

from django.db import models
from django.core import validators
from django.contrib.auth.models import User

from .ag_model_base import AutograderModel
from .course import Course

import autograder.core.shared.global_constants as gc
import autograder.core.shared.utilities as ut


class Semester(AutograderModel):
    """
    Represents a semester or term in which a course takes place.

    Related object fields:
        projects -- The group of Projects that belong to this Semester.
    """
    class Meta:
        unique_together = ('name', 'course')

    DEFAULT_INCLUDE_FIELDS = ['name', 'course']

    # -------------------------------------------------------------------------

    name = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN,
        validators=[validators.MinLengthValidator(1)],
        help_text='''The name used to identify this Semester.
                  Must be non-empty and non-null.
                  Must be unique among Semesters associated with a
                  given Course.''')

    course = models.ForeignKey(
        Course, related_name='semesters',
        help_text='The Course that this semester belongs to.')

    staff = models.ManyToManyField(
        User, related_name='semesters_is_staff_for',
        help_text='''Users that are staff members for this Semester.
            Staff members receive full feedback on autograder test
            cases and can view student submissions.''')

    enrolled_students = models.ManyToManyField(
        User, related_name='semesters_is_enrolled_in',
        help_text='''Users that are enrolled in this Semester.
                  Enrolled students can view all visible Projects
                  associated with this Semester and may be in
                  SubmissionGroups together.''')

    @property
    def semester_staff_names(self):
        """
        A list of usernames that are staff members for this Semester.
        """
        return list(set(
            itertools.chain(
                (user.username for user in self.staff.all()),
                (user.username for user in self.course.administrators.all())
            )
        ))

    @property
    def enrolled_student_names(self):
        """
        A list of usernames that are enrolled students for this
        Semester.
        """
        return list(user.username for user in self.enrolled_students.all())

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
        staff_semesters = user.semesters_is_staff_for.all()
        staff_semester_pks = (semester.pk for semester in staff_semesters)
        return itertools.chain(
            user.semesters_is_staff_for.all(),
            itertools.chain.from_iterable(
                (course.semesters.exclude(pk__in=staff_semester_pks)
                    for course in user.courses_is_admin_for.all()))
        )

    # -------------------------------------------------------------------------

    def is_semester_staff(self, user):
        """
        Returns True if the given user is a staff member for this
        Semester or a course admin for this Semester's course.
        Returns False otherwise.
        """
        return (
            self.staff.filter(pk=user.pk).exists() or
            self.course.is_administrator(user)
        )

    def is_enrolled_student(self, user):
        """
        Returns True if the given user is an enrolled student for
        this Semester. Returns False otherwise.
        """
        return self.enrolled_students.filter(pk=user.pk).exists()

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

    def delete(self, *args, **kwargs):
        semester_root_dir = ut.get_semester_root_dir(self)
        super().delete(*args, **kwargs)

        shutil.rmtree(semester_root_dir)
