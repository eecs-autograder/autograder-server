from django.db import models
from django.core.exceptions import ValidationError

from .model_utils import ModelValidatedOnSave
from .course import Course

from ..shared import global_constants as gc


class Semester(ModelValidatedOnSave):
    """
    Represents a semester or term in which a course takes place.

    Primary key: composite of course name and semester name.

    Fields:
        name -- The name used to identify this Semester.
                Must be non-empty and non-null.
                Must be unique among Semesters associated with a given Course.
        course -- The Course that this semester is associated with.
    """
    name = models.CharField(max_length=gc.MAX_CHAR_FIELD_LEN)
    course = models.ForeignKey(Course)

    _composite_primary_key = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN, primary_key=True)

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

    def validate_fields(self):
        if not self.pk:
            self._composite_primary_key = (
                Semester._compute_composite_primary_key(
                    self.name, self.course))

        if not self.name:
            raise ValidationError(
                "Semester name must be non-empty and non-null")

        # Foreign key fields raise ValueError if you try to
        # assign a null value to them, so an extra check here
        # is not needed.

        if not self._composite_primary_key:
            raise Exception("Invalid composite primary key")

    # -------------------------------------------------------------------------
