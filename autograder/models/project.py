from django.db import models
from django.core.exceptions import ValidationError

from autograder.models.model_utils import ModelValidatedOnSave
from autograder.models import Semester

from autograder.shared import global_constants as gc


class Project(ModelValidatedOnSave):
    """
    Represents a programming project for which students can
    submit solutions and have them evaluated.

    Primary key: composite of the semester name and project name

    Fields:
        name -- The name used to identify this project.
                Must be non-empty and non-null.
                Must be unique among Projects associated with
                a given semester.

        semester -- The Semester this project belongs to.

    Static methods:
        get_by_composite_key()

    Overridden methods:
        validate_fields()
    """
    name = models.CharField(max_length=gc.MAX_CHAR_FIELD_LEN)
    semester = models.ForeignKey(Semester)

    _composite_primary_key = models.TextField(primary_key=True)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    @staticmethod
    def get_by_composite_key(project_name, semester):
        """
        Does a key lookup for and returns the Project with the given
        name and that belongs to the specified semester.
        """
        return Project.objects.get(
            pk=Project._compute_composite_primary_key(project_name, semester))

    @staticmethod
    def _compute_composite_primary_key(project_name, semester):
        return "{0}_{1}".format(semester.name, project_name)

    # -------------------------------------------------------------------------

    def validate_fields(self):
        if not self.pk:
            self._composite_primary_key = self._compute_composite_primary_key(
                self.name, self.semester)

        if not self.name:
            raise ValidationError(
                "Project names must be non-null and non-empty")

        # Foreign key fields raise ValueError if you try to
        # assign a null value to them, so an extra check for semester
        # is not needed.

        if not self._composite_primary_key:
            raise Exception("Invalid composite primary key")
