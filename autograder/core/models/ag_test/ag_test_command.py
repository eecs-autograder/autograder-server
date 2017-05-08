import enum

from django.db import models

import autograder.core.fields as ag_fields
import autograder.core.utils as core_ut
from .ag_test_case import AGTestCase
from .ag_test_suite import AGTestSuite
from ..ag_model_base import AutograderModel


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
        show_actual_stderr=True
    ).pk


def make_max_command_fdbk() -> int:
    return AGTestCommandFeedbackConfig.objects.validate_and_create(
        return_code_fdbk_level=ValueFeedbackLevel.get_max(),
        stdout_fdbk_level=ValueFeedbackLevel.get_max(),
        stderr_fdbk_level=ValueFeedbackLevel.get_max(),
        show_points=True,
        show_actual_return_code=True,
        show_actual_stdout=True,
        show_actual_stderr=True
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
        AGTestCase, null=True, blank=True, default=None,
        related_name='ag_test_commands',
        help_text='''When non-null, indicates that this command belongs to the specified
                     autograder test.
                     Either this field or ag_test_suite must be non-null.''')

    ag_test_suite_is_setup_for = models.OneToOneField(
        AGTestSuite, null=True, blank=True, default=None,
        related_name='setup_command',
        help_text='''When non-null, indicates that this command should be used as the setup
                     command for the specified suite.
                     Either this field or ag_test_case must be non-null.''')

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
    # stdin_project_file
    #
    # expected_return_code

    expected_stdout_source = ag_fields.EnumField(
        ExpectedOutputSource, default=ExpectedOutputSource.none,
        help_text="Specifies what kind of source this command's stdout should be compared to.")
    expected_stdout_text = models.TextField(
        blank=True,
        help_text='''A string whose contents should be compared against this command's stdout.
                     This value is used when expected_stdout_source is ExpectedOutputSource.text
                     and is ignored otherwise.''')
    # expected_stdout_project_file

    expected_stderr_source = ag_fields.EnumField(
        ExpectedOutputSource, default=ExpectedOutputSource.none,
        help_text="Specifies what kind of source this command's stderr should be compared to.")
    expected_stderr_text = models.TextField(
        blank=True,
        help_text='''A string whose contents should be compared against this command's stderr.
                     This value is used when expected_stderr_source is ExpectedOutputSource.text
                     and is ignored otherwise.''')
    # expected_stderr_project_file

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

    # points_for_correct_return_code
    # points_for_correct_stdout
    # points_for_correct_stderr
    #
    # deduction_for_wrong_return_code
    # deduction_for_wrong_stdout
    # deduction_for_wrong_stderr
    #
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
    #

    # time_limit = models.IntegerField(
    #     default=const.DEFAULT_SUBPROCESS_TIMEOUT,
    #     validators=[MinValueValidator(1),
    #                 MaxValueValidator(const.MAX_SUBPROCESS_TIMEOUT)],
    #     help_text='''The time limit in seconds to be placed on the
    #         program being tested. This limit currently applies to each
    #         of: compilation, running the program, and running the
    #         program with Valgrind (the timeout is applied separately to
    #         each).
    #         Must be > 0
    #         Must be <= autograder.shared.global_constants
    #                              .MAX_SUBPROCESS_TIMEOUT''')

    # stack_size_limit = models.IntegerField(
    #     default=const.DEFAULT_STACK_SIZE_LIMIT,
    #     validators=[MinValueValidator(1),
    #                 MaxValueValidator(const.MAX_STACK_SIZE_LIMIT)],
    #     help_text='''
    #     stack_size_limit -- The maximum stack size in bytes.
    #         Must be > 0
    #         Must be <= autograder.shared.global_constants.MAX_STACK_SIZE_LIMIT
    #         NOTE: Setting this value too low may cause the program being
    #                 tested to crash prematurely.''')
    #
    # virtual_memory_limit = models.IntegerField(
    #     default=const.DEFAULT_VIRTUAL_MEM_LIMIT,
    #     validators=[MinValueValidator(1),
    #                 MaxValueValidator(const.MAX_VIRTUAL_MEM_LIMIT)],
    #     help_text='''The maximum amount of virtual memory
    #         (in bytes) the program being tested can use.
    #         Must be > 0
    #         Must be <= autograder.shared.global_constants.MAX_VIRTUAL_MEM_LIMIT
    #         NOTE: Setting this value too low may cause the program being
    #                 tested to crash prematurely.''')
    #
    # process_spawn_limit = models.IntegerField(
    #     default=const.DEFAULT_PROCESS_LIMIT,
    #     validators=[MinValueValidator(0),
    #                 MaxValueValidator(const.MAX_PROCESS_LIMIT)],
    #     help_text='''The maximum number of processes that the program
    #         being tested is allowed to spawn.
    #         Must be >= 0
    #         Must be <= autograder.shared.global_constants.MAX_PROCESS_LIMIT
    #         NOTE: This limit applies cumulatively to the processes
    #                 spawned by the main program being run. i.e. If a
    #                 spawned process spawns it's own child process, both
    #                 of those processes will count towards the main
    #                 program's process limit.''')
