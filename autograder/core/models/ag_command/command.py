from django.core import exceptions
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models

from autograder.core import constants
from ..ag_model_base import (
    AutograderModel,
    DictSerializableMixin,
    non_empty_str_validator,
    make_min_value_validator,
    make_max_value_validator)
import autograder.core.fields as ag_fields


class Command(DictSerializableMixin):
    """
    Contains the core information needed to run a command during grading.
    """
    def __init__(self,
                 cmd: str,
                 name: str='',
                 time_limit: int=constants.DEFAULT_SUBPROCESS_TIMEOUT,
                 # Remove in version 5.0.0
                 stack_size_limit: int=constants.DEFAULT_STACK_SIZE_LIMIT,
                 use_virtual_memory_limit: bool=True,
                 virtual_memory_limit: int=constants.DEFAULT_VIRTUAL_MEM_LIMIT,
                 block_process_spawn: bool=False,
                 # Remove in version 5.0.0
                 process_spawn_limit: int=constants.DEFAULT_PROCESS_LIMIT):
        self.cmd = cmd
        self.name = name
        self.time_limit = time_limit
        self.stack_size_limit = stack_size_limit
        self.use_virtual_memory_limit = use_virtual_memory_limit
        self.virtual_memory_limit = virtual_memory_limit
        self.block_process_spawn = block_process_spawn
        self.process_spawn_limit = process_spawn_limit

    FIELD_VALIDATORS = {
        'cmd': [non_empty_str_validator],
        'time_limit': [make_min_value_validator(1),
                       make_max_value_validator(constants.MAX_SUBPROCESS_TIMEOUT)],
        'stack_size_limit': [make_min_value_validator(1),
                             make_max_value_validator(constants.MAX_STACK_SIZE_LIMIT)],
        'virtual_memory_limit': [make_min_value_validator(1),
                                 make_max_value_validator(constants.MAX_VIRTUAL_MEM_LIMIT)],
        'process_spawn_limit': [make_min_value_validator(0),
                                make_max_value_validator(constants.MAX_PROCESS_LIMIT)],
    }

    FIELD_DESCRIPTIONS = {
        'name': "An optional name for this command to be displayed to users.",
        'cmd': '''A string containing the command to be run.
                  Note: This string will be inserted into ['bash', '-c', <cmd>]
                     in order to be executed.''',
        'time_limit': f"""The time limit in seconds to be placed on the command.
            Must be > 0
            Must be <= {constants.MAX_SUBPROCESS_TIMEOUT}""",
        'stack_size_limit': "This field is IGNORED and will be removed in version 5.0.0.",
        'use_virtual_memory_limit': """When set to false, the virtual memory limit will not
            be applied to the command. Note that the sandbox will still apply
            a physical memory limit to all commands run in the sandbox.""",
        'virtual_memory_limit': f"""The maximum amount of virtual memory (in bytes) allowed.
            Must be > 0
            Must be <= {constants.MAX_VIRTUAL_MEM_LIMIT}
            NOTE: Setting this value too low may cause the command to crash prematurely.""",
        'block_process_spawn': "When true, prevents the command from spawning child processes.",
        'process_spawn_limit': """This field is IGNORED and will be removed in version 5.0.0.
            Use block_process_spawn instead.""",
    }
