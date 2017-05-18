import enum

from django.core import exceptions
from django.core.validators import (
    MinValueValidator, MaxValueValidator, MaxLengthValidator)
from django.db import models

import autograder.core.fields as ag_fields
from autograder.core import constants
import autograder.core.utils as core_ut
from .ag_test_case import AGTestCase
from ..ag_model_base import AutograderModel
from ..project import UploadedFile


class ValueFeedbackLevel(core_ut.OrderedEnum):
    no_feedback = 'no_feedback'
    correct_or_incorrect = 'correct_or_incorrect'
    expected_and_actual = 'expected_and_actual'


class AGTestCommandFeedbackConfig(AutograderModel):
    """
    Contains feedback options for an AGTestCommand
    """
    visible = models.BooleanField(default=True)

    return_code_fdbk_level = ag_fields.EnumField(ValueFeedbackLevel,
                                                 default=ValueFeedbackLevel.get_min())
    stdout_fdbk_level = ag_fields.EnumField(ValueFeedbackLevel,
                                            default=ValueFeedbackLevel.get_min())
    stderr_fdbk_level = ag_fields.EnumField(ValueFeedbackLevel,
                                            default=ValueFeedbackLevel.get_min())

    show_points = models.BooleanField(default=False)
    show_actual_return_code = models.BooleanField(default=False)
    show_actual_stdout = models.BooleanField(default=False)
    show_actual_stderr = models.BooleanField(default=False)
    show_whether_timed_out = models.BooleanField(default=False)

    SERIALIZABLE_FIELDS = (
        'visible',
        'return_code_fdbk_level',
        'stdout_fdbk_level',
        'stderr_fdbk_level',
        'show_points',
        'show_actual_return_code',
        'show_actual_stdout',
        'show_actual_stderr',
        'show_whether_timed_out'
    )

    EDITABLE_FIELDS = (
        'visible',
        'return_code_fdbk_level',
        'stdout_fdbk_level',
        'stderr_fdbk_level',
        'show_points',
        'show_actual_return_code',
        'show_actual_stdout',
        'show_actual_stderr',
        'show_whether_timed_out'
    )


def make_default_command_fdbk() -> int:
    """
    Creates a new default AGTestCommandFeedbackConfig and returns its pk.
    """
    return AGTestCommandFeedbackConfig.objects.validate_and_create().pk


def make_default_ultimate_submission_command_fdbk() -> int:
    return AGTestCommandFeedbackConfig.objects.validate_and_create(
        return_code_fdbk_level=ValueFeedbackLevel.correct_or_incorrect,
        stdout_fdbk_level=ValueFeedbackLevel.correct_or_incorrect,
        stderr_fdbk_level=ValueFeedbackLevel.correct_or_incorrect,
        show_points=True,
        show_actual_return_code=True,
        show_actual_stdout=True,
        show_actual_stderr=True,
        show_whether_timed_out=True
    ).pk


def make_max_command_fdbk() -> int:
    return AGTestCommandFeedbackConfig.objects.validate_and_create(
        return_code_fdbk_level=ValueFeedbackLevel.get_max(),
        stdout_fdbk_level=ValueFeedbackLevel.get_max(),
        stderr_fdbk_level=ValueFeedbackLevel.get_max(),
        show_points=True,
        show_actual_return_code=True,
        show_actual_stdout=True,
        show_actual_stderr=True,
        show_whether_timed_out=True
    ).pk


class StdinSource(enum.Enum):
    none = 'none'  # No input to redirect
    text = 'text'
    project_file = 'project_file'
    setup_stdout = 'setup_stdout'
    setup_stderr = 'setup_stderr'


class ExpectedOutputSource(enum.Enum):
    none = 'none'  # Don't check output
    text = 'text'
    project_file = 'project_file'


class ExpectedReturnCode(enum.Enum):
    none = 'none'  # Don't check return code
    zero = 'zero'
    nonzero = 'nonzero'


class AGTestCommand(AutograderModel):
    """
    An AGTestCommand represents a single command to either evaluate student code or set up
    an AGTestSuite.
    """

    class Meta:
        unique_together = ('name', 'ag_test_case')
        order_with_respect_to = 'ag_test_case'

    name = ag_fields.ShortStringField(
        help_text='''The name used to identify this command.
                     Must be non-empty and non-null.
                     Must be unique among commands that belong to the same autograder test.
                     This field is REQUIRED.''')

    ag_test_case = models.ForeignKey(
        AGTestCase,
        related_name='ag_test_commands',
        help_text='''When non-null, indicates that this command belongs to the specified
                     autograder test.
                     Either this field or ag_test_suite must be non-null.''')

    cmd = ag_fields.ShortStringField(
        help_text='''A string containing the command to be run.
                     Note: This string will be split using shlex.split() before it is executed.''')

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

    expected_return_code = ag_fields.EnumField(
        ExpectedReturnCode, default=ExpectedReturnCode.none,
        help_text="Specifies the command's expected return code.")

    expected_stdout_source = ag_fields.EnumField(
        ExpectedOutputSource, default=ExpectedOutputSource.none,
        help_text="Specifies what kind of source this command's stdout should be compared to.")
    expected_stdout_text = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(constants.MAX_OUTPUT_LENGTH)],
        help_text='''A string whose contents should be compared against this command's stdout.
                     This value is used when expected_stdout_source is ExpectedOutputSource.text
                     and is ignored otherwise.''')
    expected_stdout_project_file = models.ForeignKey(
        UploadedFile, blank=True, null=True, default=None, related_name='+',
        help_text='''An UploadedFile whose contents should be compared against this command's
                     stdout. This value is used (and may not be null) when expected_stdout_source
                     is ExpectedOutputSource.project_file and is ignored otherwise.''')

    expected_stderr_source = ag_fields.EnumField(
        ExpectedOutputSource, default=ExpectedOutputSource.none,
        help_text="Specifies what kind of source this command's stderr should be compared to.")
    expected_stderr_text = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(constants.MAX_OUTPUT_LENGTH)],
        help_text='''A string whose contents should be compared against this command's stderr.
                     This value is used when expected_stderr_source is ExpectedOutputSource.text
                     and is ignored otherwise.''')
    expected_stderr_project_file = models.ForeignKey(
        UploadedFile, blank=True, null=True, default=None, related_name='+',
        help_text='''An UploadedFile whose contents should be compared against this command's
                     stderr. This value is used (and may not be null) when expected_stderr_source
                     is ExpectedOutputSource.project_file and is ignored otherwise.''')

    ignore_case = models.BooleanField(
        default=False,
        help_text='Ignore case when checking output. Equivalent to diff -i')
    ignore_whitespace = models.BooleanField(
        default=False,
        help_text='Ignore inline whitespace when checking output. Equivalent to diff -w')
    ignore_whitespace_changes = models.BooleanField(
        default=False,
        help_text='Ignore whitespace changes when checking output. Equivalent to diff -b')
    ignore_blank_lines = models.BooleanField(
        default=False,
        help_text='Ignore changes in blank lines when checking output. Equivalent to diff -B')

    points_for_correct_return_code = models.IntegerField(
        default=0, validators=[MinValueValidator(0)],
        help_text='''The number of points to be awarded when this command
                     produces the correct return_code''')
    points_for_correct_stdout = models.IntegerField(
        default=0, validators=[MinValueValidator(0)],
        help_text='''The number of points to be awarded when this command
                     produces the correct stdout''')
    points_for_correct_stderr = models.IntegerField(
        default=0, validators=[MinValueValidator(0)],
        help_text='''The number of points to be awarded when this command
                     produces the correct stderr''')

    deduction_for_wrong_return_code = models.IntegerField(
        default=0, validators=[MaxValueValidator(0)],
        help_text='''The number of points to deduct when this command
                     produces the wrong return_code (this value must be negative).
                     Note: The total points given for a single command may be negative,
                     but the total points for an AGTestCase will be capped at zero.''')
    deduction_for_wrong_stdout = models.IntegerField(
        default=0, validators=[MaxValueValidator(0)],
        help_text='''The number of points to deduct when this command
                     produces the wrong stdout (this value must be negative).
                     Note: The total points given for a single command may be negative,
                     but the total points for an AGTestCase will be capped at zero.''')
    deduction_for_wrong_stderr = models.IntegerField(
        default=0, validators=[MaxValueValidator(0)],
        help_text='''The number of points to deduct when this command
                     produces the wrong stderr (this value must be negative).
                     Note: The total points given for a single command may be negative,
                     but the total points for an AGTestCase will be capped at zero.''')

    normal_fdbk_config = models.OneToOneField(
        AGTestCommandFeedbackConfig, default=make_default_command_fdbk,
        related_name='+',
        help_text='Feedback settings for a normal Submission.')
    ultimate_submission_fdbk_config = models.OneToOneField(
        AGTestCommandFeedbackConfig, default=make_default_ultimate_submission_command_fdbk,
        related_name='+',
        help_text='Feedback settings for an ultimate Submission.')
    past_limit_submission_fdbk_config = models.OneToOneField(
        AGTestCommandFeedbackConfig, default=make_default_command_fdbk,
        related_name='+',
        help_text='Feedback settings for a Submission that is past the daily limit.')
    staff_viewer_fdbk_config = models.OneToOneField(
        AGTestCommandFeedbackConfig, default=make_max_command_fdbk,
        related_name='+',
        help_text='Feedback settings for a staff member viewing a Submission from another group.')

    time_limit = models.IntegerField(
        default=constants.DEFAULT_SUBPROCESS_TIMEOUT,
        validators=[MinValueValidator(1), MaxValueValidator(constants.MAX_SUBPROCESS_TIMEOUT)],
        help_text='''The time limit in seconds to be placed on the
            program being tested. This limit currently applies to each
            of: compilation, running the program, and running the
            program with Valgrind (the timeout is applied separately to
            each).
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
            NOTE: Setting this value too low may cause the program being
                    tested to crash prematurely.''')

    virtual_memory_limit = models.IntegerField(
        default=constants.DEFAULT_VIRTUAL_MEM_LIMIT,
        validators=[MinValueValidator(1), MaxValueValidator(constants.MAX_VIRTUAL_MEM_LIMIT)],
        help_text='''The maximum amount of virtual memory
            (in bytes) the program being tested can use.
            Must be > 0
            Must be <= autograder.shared.global_constants.MAX_VIRTUAL_MEM_LIMIT
            NOTE: Setting this value too low may cause the program being
                    tested to crash prematurely.''')

    process_spawn_limit = models.IntegerField(
        default=constants.DEFAULT_PROCESS_LIMIT,
        validators=[MinValueValidator(0), MaxValueValidator(constants.MAX_PROCESS_LIMIT)],
        help_text='''The maximum number of processes that the program
            being tested is allowed to spawn.
            Must be >= 0
            Must be <= autograder.shared.global_constants.MAX_PROCESS_LIMIT
            NOTE: This limit applies cumulatively to the processes
                    spawned by the main program being run. i.e. If a
                    spawned process spawns it's own child process, both
                    of those processes will count towards the main
                    program's process limit.''')

    def clean(self):
        error_dict = {}

        if self.stdin_source == StdinSource.project_file and self.stdin_project_file is None:
            error_dict['stdin_project_file'] = (
                'This field may not be None when stdin source is project file.')

        if (self.expected_stdout_source == ExpectedOutputSource.project_file and
                self.expected_stdout_project_file is None):
            error_dict['expected_stdout_project_file'] = (
                'This field may not be None when expected stdout source is project file.')

        if (self.expected_stderr_source == ExpectedOutputSource.project_file and
                self.expected_stderr_project_file is None):
            error_dict['expected_stderr_project_file'] = (
                'This field may not be None when expected stderr source is project file.')

        if error_dict:
            raise exceptions.ValidationError(error_dict)

    SERIALIZABLE_FIELDS = (
        'name',
        'ag_test_case',
        'cmd',

        'stdin_source',
        'stdin_text',
        'stdin_project_file',

        'expected_return_code',

        'expected_stdout_source',
        'expected_stdout_text',
        'expected_stdout_project_file',

        'expected_stderr_source',
        'expected_stderr_text',
        'expected_stderr_project_file',

        'ignore_case',
        'ignore_whitespace',
        'ignore_whitespace_changes',
        'ignore_blank_lines',

        'points_for_correct_return_code',
        'points_for_correct_stdout',
        'points_for_correct_stderr',

        'deduction_for_wrong_return_code',
        'deduction_for_wrong_stdout',
        'deduction_for_wrong_stderr',

        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config',

        'time_limit',
        'stack_size_limit',
        'virtual_memory_limit',
        'process_spawn_limit',
    )

    SERIALIZE_RELATED = (
        'ag_test_case',
    )

    EDITABLE_FIELDS = (
        'name',

        'cmd',

        'stdin_source',
        'stdin_text',
        'stdin_project_file',

        'expected_return_code',

        'expected_stdout_source',
        'expected_stdout_text',
        'expected_stdout_project_file',

        'expected_stderr_source',
        'expected_stderr_text',
        'expected_stderr_project_file',

        'ignore_case',
        'ignore_whitespace',
        'ignore_whitespace_changes',
        'ignore_blank_lines',

        'points_for_correct_return_code',
        'points_for_correct_stdout',
        'points_for_correct_stderr',

        'deduction_for_wrong_return_code',
        'deduction_for_wrong_stdout',
        'deduction_for_wrong_stderr',

        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config',

        'time_limit',
        'stack_size_limit',
        'virtual_memory_limit',
        'process_spawn_limit',
    )

    TRANSPARENT_TO_ONE_FIELDS = (
        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config',
    )
