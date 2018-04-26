from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models

from autograder.core import constants
from autograder.core.models import AutograderModel
import autograder.core.fields as ag_fields


class AGCommandBase(AutograderModel):
    """
    An abstract base class that contains the core information needed to run
    a command during grading.
    """

    class Meta:
        abstract = True

    name = ag_fields.ShortStringField(
        blank=True, help_text="An optional name for this command.")

    cmd = models.CharField(
        max_length=constants.MAX_COMMAND_LENGTH,
        help_text='''A string containing the command to be run.
                     Note: This string will be inserted into ['bash', '-c', <cmd>]
                        in order to be executed.
                     Note: This string defaults to the "true" command
                     (which does nothing and returns 0) so that AGCommands are
                     default-creatable.''')

    time_limit = models.IntegerField(
        default=constants.DEFAULT_SUBPROCESS_TIMEOUT,
        validators=[MinValueValidator(1), MaxValueValidator(constants.MAX_SUBPROCESS_TIMEOUT)],
        help_text='''The time limit in seconds to be placed on the
            command.
            Must be > 0
            Must be <= autograder.shared.global_constants
                                 .MAX_SUBPROCESS_TIMEOUT''')

    stack_size_limit = models.IntegerField(
        default=constants.DEFAULT_STACK_SIZE_LIMIT,
        validators=[MinValueValidator(1), MaxValueValidator(constants.MAX_STACK_SIZE_LIMIT)],
        help_text='''
        stack_size_limit -- The maximum stack size in bytes.
            Must be > 0
            Must be <= autograder.shared.global_constants.MAX_STACK_SIZE_LIMIT
            NOTE: Setting this value too low may cause the command to crash prematurely.''')

    virtual_memory_limit = models.BigIntegerField(
        default=constants.DEFAULT_VIRTUAL_MEM_LIMIT,
        validators=[MinValueValidator(1), MaxValueValidator(constants.MAX_VIRTUAL_MEM_LIMIT)],
        help_text='''The maximum amount of virtual memory
            (in bytes) the command can use.
            Must be > 0
            Must be <= autograder.shared.global_constants.MAX_VIRTUAL_MEM_LIMIT
            NOTE: Setting this value too low may cause the command to crash prematurely.''')

    process_spawn_limit = models.IntegerField(
        default=constants.DEFAULT_PROCESS_LIMIT,
        validators=[MinValueValidator(0), MaxValueValidator(constants.MAX_PROCESS_LIMIT)],
        help_text='''The maximum number of processes that the command is allowed to spawn.
            Must be >= 0
            Must be <= autograder.shared.global_constants.MAX_PROCESS_LIMIT
            NOTE: This limit applies cumulatively to the processes
                    spawned by the main program being run. i.e. If a
                    spawned process spawns it's own child process, both
                    of those processes will count towards the main
                    program's process limit.''')
