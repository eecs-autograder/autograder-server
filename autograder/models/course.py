from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from autograder.models.model_utils import ModelValidatedOnSave

from autograder.shared import global_constants as gc


class Course(ModelValidatedOnSave):
    """
    Represents a programming course for which students will be submitting
    code to an autograder.

    Primary key: name

    Fields:
        name -- The name of this course.
                Must be unique, non-empty and non-null.

        staff_members -- A list of staff members of a course who
            have elevated read privileges.

    Overridden member functions:
        validate_fields()
    """
    name = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN, primary_key=True)
    staff_members = models.ManyToManyField(User)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def validate_fields(self):
        if not self.name:
            raise ValidationError(
                "Course name must be non-null and non-empty.")
