from django.db import models

from ..ag_model_base import AutograderModel


class AGCommandResultBase(AutograderModel):
    """
    Contains the core information needed to store the results of
    running a command.
    """

    class Meta:
        abstract = True

    return_code = models.IntegerField(
        blank=True, null=True, default=None,
        help_text=""""The return code of the completed command. A value of None
                      for a completed usually is caused by the the command timing out.""")

    timed_out = models.BooleanField(
        blank=True, default=False, help_text="Whether the command exceeded its time limit.")

    stdout_truncated = models.BooleanField(
        blank=True, default=False, help_text="Whether the command's stdout was truncated.")
    stderr_truncated = models.BooleanField(
        blank=True, default=False, help_text="Whether the command's stderr was truncated.")

    @property
    def stdout_filename(self):
        raise NotImplementedError('Derived classes must implement this property')

    @property
    def stderr_filename(self):
        raise NotImplementedError('Derived classes must implement this property')
