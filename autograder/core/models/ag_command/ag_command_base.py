import enum

from django.core import exceptions
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models

from autograder.core import constants
from autograder.core.models import AutograderModel
import autograder.core.fields as ag_fields
from ..project.uploaded_file import UploadedFile


class StdinSource(enum.Enum):
    none = 'none'  # No input to redirect
    text = 'text'
    project_file = 'project_file'
    setup_stdout = 'setup_stdout'
    setup_stderr = 'setup_stderr'


class AGCommandBase(AutograderModel):
    """
    An abstract base class that contains the core information needed to run
    a command during grading.
    """

    class Meta:
        abstract = True

    optional_name = ag_fields.ShortStringField(
        blank=True, help_text="An optional name for this command.")

    cmd = models.CharField(
        max_length=constants.MAX_COMMAND_LENGTH,
        help_text='''A string containing the command to be run.
                     Note: This string will be split using shlex.split() before it is executed.
                     Note: This string defaults to the "true" command
                     (which does nothing and returns 0) so that AGCommands are
                     default-creatable.''')

    stdin_source = ag_fields.EnumField(
        StdinSource, default=StdinSource.none,
        help_text='''Specifies what kind of source stdin will be redirected from.''')
    stdin_text = models.TextField(
        blank=True,
        help_text='''A string whose contents should be redirected to the stdin of this command.
                     This value is used when stdin_source is StdinSource.text and is ignored
                     otherwise.''')
    stdin_project_file = models.ForeignKey(
        UploadedFile, blank=True, null=True, default=None, related_name='+',
        help_text='''An UploadedFile whose contents should be redirected to the stdin of this
                     command. This value is used when stdin_source is StdinSource.project_file
                     and is ignored otherwise.''')

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

    virtual_memory_limit = models.IntegerField(
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

    def clean(self):
        if self.stdin_source == StdinSource.project_file and self.stdin_project_file is None:
            msg = 'This field may not be None when stdin source is project file.'
            raise exceptions.ValidationError({'stdin_project_file': msg})
