from django.db import models
# from django.core.exceptions import ValidationError

# from autograder.models.model_utils import ModelValidatableOnSave
from autograder.models import SubmissionGroup


class Submission(models.Model):
    """
    Represents a single submission for a particular project.

    Fields:
        submission_group -- The SubmissionGroup that this submission
            belongs to.
            This field is REQUIRED.

        timestamp -- The timestamp at which this Submission was
            recorded.
            This field is generated and assigned automatically.

        feedback_level -- TODO
    """
    submission_group = models.ForeignKey(SubmissionGroup)

    @property
    def timestamp(self):
        return self._timestamp

    _timestamp = models.DateTimeField(auto_now_add=True)
