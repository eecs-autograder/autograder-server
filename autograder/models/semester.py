import os

from django.db import models

from autograder.models.model_validated_on_save import ModelValidatedOnSave
from autograder.models import Course

import autograder.shared.global_constants as gc
import autograder.shared.utilities as ut


class Semester(ModelValidatedOnSave):
    """
    Represents a semester or term in which a course takes place.

    Primary key: composite of course name and semester name.

    Fields:
        name -- The name used to identify this Semester.
                Must be non-empty and non-null.
                Must be unique among Semesters associated with a given Course.

        course -- The Course that this semester is associated with.

    Static methods:
        get_by_composite_key()

    Overridden member functions:
        save()
        validate_fields()
    """
    name = models.CharField(max_length=gc.MAX_CHAR_FIELD_LEN)
    course = models.ForeignKey(Course)

    _composite_primary_key = models.TextField(primary_key=True)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    @staticmethod
    def get_by_composite_key(semester_name, course):
        """
        Does a key lookup for and returns the Semester with the given
        name and that belongs to the specified course.
        """
        return Semester.objects.get(
            pk=Semester._compute_composite_primary_key(semester_name, course))

    @staticmethod
    def _compute_composite_primary_key(semester_name, course):
        return "{0}_{1}".format(course.name, semester_name)

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

    # -------------------------------------------------------------------------

    def validate_fields(self):
        if not self.pk:
            self._composite_primary_key = (
                Semester._compute_composite_primary_key(
                    self.name, self.course))

        if not self.name:
            raise ValueError(
                "Semester name must be non-empty and non-null")

        # Foreign key fields raise ValueError if you try to
        # assign a null value to them, so an extra check for course
        # is not needed.

        if not self._composite_primary_key:
            raise Exception("Invalid composite primary key")
