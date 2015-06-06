from django.db import models
from django.core.exceptions import ValidationError

from .model_utils import ModelValidatedOnSave
from autograder.models import Course

from ..shared import global_constants as gc


class Project(ModelValidatedOnSave):
    """
    Represents a programming project for which students can
    submit solutions and have them evaluated.

    Primary key: composite of the course name and project name

    Fields:
        name -- The name used to identify this project.
                Must be non-empty and non-null.
                Must be unique among Projects associated with
                a given course.
        course -- The Course this project is associated with.

        required_student_files -- A list of filenames
            that students are required to submit for this project.
            For example, eecs280's project1 might require the files:
            ["spam.cpp", "eggs.cpp", "sausage.cpp"].

    Overridden methods:
        validate_fields()

    Static methods:
        get_by_composite_key()
    """
    name = models.CharField(max_length=gc.MAX_CHAR_FIELD_LEN)
    course = models.ForeignKey(Course)

    _composite_primary_key = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN, primary_key=True)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    @staticmethod
    def get_by_composite_key(project_name, course):
        """
        Does a key lookup for and returns the Project with the given
        name and that belongs to the specified course.
        """
        return Project.objects.get(
            pk=Project._compute_composite_primary_key(project_name, course))

    @staticmethod
    def _compute_composite_primary_key(project_name, course):
        return "{0}_{1}".format(course.name, project_name)

    # -------------------------------------------------------------------------

    def validate_fields(self):
        if not self.pk:
            self._composite_primary_key = self._compute_composite_primary_key(
                self.name, self.course)

        if not self.name:
            raise ValidationError(
                "Project names must be non-null and non-empty")

        # Foreign key fields raise ValueError if you try to
        # assign a null value to them, so an extra check for course
        # is not needed.

        if not self._composite_primary_key:
            raise Exception("Invalid composite primary key")


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

# class RequiredStudentFileName(ModelValidatedOnSave):
#     """
#     Stores the name of a file that students are required to
#     submit for a given project.
#     """
#     pass


# class ExpectedStudentFilePattern(ModelValidatedOnSave):
#     """
#     Stores the name of a file pattern
#     """
#     # List of characters that are allowed in filepatterns.
#     # All alphanumeric characters, hyphen, underscore, period, parentheses,
#     # and characters that have special meaning when using Python's
#     # fnmatch(), which are square brackets, asterisk question mark,
#     # and exclamation point.
#     #
#     # NOTE: This whitelist is different from the one used for
#     # the actual files being submitted. That whitelist is much stricter.
#     CHAR_WHITELIST_REGEX = r"[a-zA-z0-9-_.()\[\]!\*\?]*"

#     # This list can contain file patterns as per python's fnmatch
#     # function: https://docs.python.org/3.4/library/fnmatch.html
#     # For example, a value of ["*.cpp", "*.h"] would


