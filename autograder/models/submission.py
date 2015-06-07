from django.db import models
from django.core.exceptions import ValidationError

from autograder.models.model_utils import ModelValidatedOnSave
from autograder.models import Semester, Project


class Submission(ModelValidatedOnSave):
    """
    Represents a student's submission for a particular project.
    """
    timestamp = models.DateTimeField(auto_add_now=True)
    # semester =
