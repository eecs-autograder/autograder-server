import os

from django.conf import settings
from django.db import models

from .ag_command_result_base import AGCommandResultBase
from .ag_command import AGCommand


class AGCommandResult(AGCommandResultBase):
    """
    Contains the core run results of an AGCommand.
    """

    ag_command = models.ForeignKey(
        AGCommand, on_delete=models.SET_NULL,
        null=True, blank=True, default=None,
        help_text="The AGCommand this result belongs to, or None if this "
                  "result doesn't belong to a command or if its command has been deleted.")

    @property
    def stdout_filename(self):
        return os.path.join(_get_cmd_result_output_dirname(),
                            'cmd_result_{}_stdout'.format(self.pk))

    @property
    def stderr_filename(self):
        return os.path.join(_get_cmd_result_output_dirname(),
                            'cmd_result_{}_stderr'.format(self.pk))

    def save(self, *args, **kwargs):
        super().save()
        os.makedirs(_get_cmd_result_output_dirname(), exist_ok=True)

    # We won't define any serialization settings here because run results
    # are typically processed through some sort of "feedback calculator"
    # before being serialized.


def _get_cmd_result_output_dirname():
    return os.path.join(settings.MEDIA_ROOT, 'misc_cmd_output')
