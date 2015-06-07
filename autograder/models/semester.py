from django.db import models
from django.core.exceptions import ValidationError

from autograder.models.model_utils import ModelValidatedOnSave
from autograder.models import Course, Project

from autograder.shared import global_constants as gc


class Semester(ModelValidatedOnSave):
    """
    Represents a semester or term in which a course takes place.

    Primary key: composite of course name and semester name.

    Fields:
        name -- The name used to identify this Semester.
                Must be non-empty and non-null.
                Must be unique among Semesters associated with a given Course.

        course -- The Course that this semester is associated with.

        projects -- The projects that will be open for submission this
                    Semester.

    Overridden member functions:
        validate_fields()

    Static methods:
        get_by_composite_key()
    """
    name = models.CharField(max_length=gc.MAX_CHAR_FIELD_LEN)
    course = models.ForeignKey(Course)
    projects = models.ManyToManyField(Project)

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

    def validate_fields(self):
        if not self.pk:
            self._composite_primary_key = (
                Semester._compute_composite_primary_key(
                    self.name, self.course))

        if not self.name:
            raise ValidationError(
                "Semester name must be non-empty and non-null")

        # Foreign key fields raise ValueError if you try to
        # assign a null value to them, so an extra check for course
        # is not needed.

        if not self._composite_primary_key:
            raise Exception("Invalid composite primary key")
