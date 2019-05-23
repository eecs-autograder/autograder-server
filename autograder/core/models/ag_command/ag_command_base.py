from django.core import exceptions
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models

from autograder.core import constants
from ..ag_model_base import AutograderModel, DictSerializableMixin
import autograder.core.fields as ag_fields


def _make_min_value_validator(min_value: int):
    def validator(value: int):
        if value < min_value:
            raise exceptions.ValidationError(f'Must be >= {min_value}')

    return validator


def _make_max_value_validator(max_value: int):
    def validator(value: int):
        if value > max_value:
            raise exceptions.ValidationError(f'Must be <= {max_value}')

    return validator


def _non_empty_str_validator(string: str):
    if len(string) == 0:
        raise exceptions.ValidationError(f'Must not be empty')


class Command(DictSerializableMixin):
    """
    Contains the core information needed to run a command during grading.
    """
    def __init__(self,
                 cmd: str,
                 name: str='',
                 time_limit: int=constants.DEFAULT_SUBPROCESS_TIMEOUT,
                 stack_size_limit: int=constants.DEFAULT_STACK_SIZE_LIMIT,
                 virtual_memory_limit: int=constants.DEFAULT_VIRTUAL_MEM_LIMIT,
                 process_spawn_limit: int=constants.DEFAULT_PROCESS_LIMIT):
        self.cmd = cmd
        self.name = name
        self.time_limit = time_limit
        self.stack_size_limit = stack_size_limit
        self.virtual_memory_limit = virtual_memory_limit
        self.process_spawn_limit = process_spawn_limit

    FIELD_VALIDATORS = {
        'cmd': [_non_empty_str_validator],
        'time_limit': [_make_min_value_validator(1),
                       _make_max_value_validator(constants.MAX_SUBPROCESS_TIMEOUT)],
        'stack_size_limit': [_make_min_value_validator(1),
                             _make_max_value_validator(constants.MAX_STACK_SIZE_LIMIT)],
        'virtual_memory_limit': [_make_min_value_validator(1),
                                 _make_max_value_validator(constants.MAX_VIRTUAL_MEM_LIMIT)],
        'process_spawn_limit': [_make_min_value_validator(0),
                                _make_max_value_validator(constants.MAX_PROCESS_LIMIT)],
    }

    FIELD_DESCRIPTIONS = {
        'name': "An optional name for this command to be displayed to users.",
        'cmd': '''A string containing the command to be run.
                  Note: This string will be inserted into ['bash', '-c', <cmd>]
                     in order to be executed.''',
        'time_limit': f"""The time limit in seconds to be placed on the command.
            Must be > 0
            Must be <= {constants.MAX_SUBPROCESS_TIMEOUT}""",
        'stack_size_limit': f"""The maximum stack size in bytes.
            Must be > 0
            Must be <= {constants.MAX_STACK_SIZE_LIMIT}
            NOTE: Setting this value too low may cause the command to crash prematurely.""",
        'virtual_memory_limit': f"""The maximum amount of virtual memory (in bytes) allowed.
            Must be > 0
            Must be <= {constants.MAX_VIRTUAL_MEM_LIMIT}
            NOTE: Setting this value too low may cause the command to crash prematurely.""",
        'process_spawn_limit': f"""The maximum number of processes the command is allowed to spawn.
            Must be >= 0
            Must be <= {constants.MAX_PROCESS_LIMIT}
            NOTE: This limit applies cumulatively to the processes
                  spawned by the main program being run. i.e. If a
                  spawned process spawns it's own child process, both
                  of those processes will count towards the main
                  program's process limit.""",
    }

    SERIALIZABLE_FIELDS = [
        'name',
        'cmd',
        'time_limit',
        'stack_size_limit',
        'virtual_memory_limit',
        'process_spawn_limit',
    ]


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
        help_text=f"""The time limit in seconds to be placed on the command.
            Must be > 0
            Must be <= {constants.MAX_SUBPROCESS_TIMEOUT}""")

    stack_size_limit = models.IntegerField(
        default=constants.DEFAULT_STACK_SIZE_LIMIT,
        validators=[MinValueValidator(1), MaxValueValidator(constants.MAX_STACK_SIZE_LIMIT)],
        help_text=f"""The maximum stack size in bytes.
            Must be > 0
            Must be <= {constants.MAX_STACK_SIZE_LIMIT}
            NOTE: Setting this value too low may cause the command to crash prematurely.""")

    virtual_memory_limit = models.BigIntegerField(
        default=constants.DEFAULT_VIRTUAL_MEM_LIMIT,
        validators=[MinValueValidator(1), MaxValueValidator(constants.MAX_VIRTUAL_MEM_LIMIT)],
        help_text=f"""The maximum amount of virtual memory
            (in bytes) the command can use.
            Must be > 0
            Must be <= {constants.MAX_VIRTUAL_MEM_LIMIT}
            NOTE: Setting this value too low may cause the command to crash prematurely.""")

    process_spawn_limit = models.IntegerField(
        default=constants.DEFAULT_PROCESS_LIMIT,
        validators=[MinValueValidator(0), MaxValueValidator(constants.MAX_PROCESS_LIMIT)],
        help_text=f"""The maximum number of processes that the command is allowed to spawn.
            Must be >= 0
            Must be <= {constants.MAX_PROCESS_LIMIT}
            NOTE: This limit applies cumulatively to the processes
                  spawned by the main program being run. i.e. If a
                  spawned process spawns it's own child process, both
                  of those processes will count towards the main
                  program's process limit.""")
