import os

from django.db import models
from django.db import transaction

import autograder.core.utils as core_ut
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
        if not self.pk:
            raise AttributeError(
                'stdout_filename is not available until the AGCommandResult has been saved')

        return os.path.join(core_ut.misc_cmd_output_dir(), 'cmd_result_{}_stdout'.format(self.pk))

    @property
    def stderr_filename(self):
        if not self.pk:
            raise AttributeError(
                'stderr_filename is not available until the AGCommandResult has been saved')

        return os.path.join(core_ut.misc_cmd_output_dir(), 'cmd_result_{}_stderr'.format(self.pk))

    def save(self, *args, **kwargs):
        is_create = self.pk is None

        with transaction.atomic():
            super().save(*args, **kwargs)

            if is_create:
                os.makedirs(core_ut.misc_cmd_output_dir(), exist_ok=True)
                open(self.stdout_filename, 'w').close()
                open(self.stderr_filename, 'w').close()

                self.save()

    # We won't define any serialization settings here because run results
    # are typically processed through some sort of "result feedback" class
    # before being serialized.
