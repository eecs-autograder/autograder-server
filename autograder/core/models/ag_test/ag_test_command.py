from django.db import models

import autograder.core.fields as ag_fields
import autograder.core.utils as core_ut
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


def make_default_command_fdbk() -> AGTestCommandFeedbackConfig:
    return AGTestCommandFeedbackConfig.objects.validate_and_create()


def make_default_ultimate_submission_command_fdbk() -> AGTestCommandFeedbackConfig:
    return AGTestCommandFeedbackConfig.objects.validate_and_create(
        return_code_fdbk_level=ValueFeedbackLevel.correct_or_incorrect,
        stdout_fdbk_level=ValueFeedbackLevel.correct_or_incorrect,
        stderr_fdbk_level=ValueFeedbackLevel.correct_or_incorrect,
        show_points=True,
        show_actual_return_code=True,
        show_actual_stdout=True,
        show_actual_stderr=True)


def make_max_command_fdbk() -> AGTestCommandFeedbackConfig:
    return AGTestCommandFeedbackConfig.objects.validate_and_create(
        return_code_fdbk_level=ValueFeedbackLevel.get_max(),
        stdout_fdbk_level=ValueFeedbackLevel.get_max(),
        stderr_fdbk_level=ValueFeedbackLevel.get_max(),
        show_points=True,
        show_actual_return_code=True,
        show_actual_stdout=True,
        show_actual_stderr=True)


class AGTestCommand(AutograderModel):
    """
    An AGTestCommand represents a single command to either evaluate student code or set up
    an AGTestSuite.
    """

    class Meta:
        unique_together = ('name', 'ag_test_case')
        order_with_respect_to = ('ag_test_case',)

    name = ag_fields.ShortStringField(
        help_text="""The name used to identify this command.
                     Must be non-empty and non-null.
                     Must be unique among commands that belong to the same autograder test.
                     This field is REQUIRED.""")

    ag_test_case = models.ForeignKey(
        'AGTestCase', null=True, default=None,
        help_text="""When non-null, indicates that this command belongs to the specified
                     autograder test.
                     Either this field or ag_test_suite must be non-null.""")

    ag_test_suite = models.OneToOneField(
        'AGTestSuite', null=True, default=None,
        help_text="""When non-null, indicates that this command should be used as the setup
                     command for the specified suite.
                     Either this field or ag_test_case must be non-null.""")

    args = ag_fields.StringArrayField(
        help_text="""A list of strings describing the command to be run. The list may not be
                     empty, and individual items of the list may not be empty.""")

    # stdin_source
    # stdin_project_file
    #
    # expected_return_code
    # expect_any_nonzero_return_code
    # expected_stdout
    # expected_stderr
    #
    # ignore_case = models.BooleanField(
    #     default=False,
    #     help_text='Ignore case when checking output. Equivalent to diff -i')
    # ignore_whitespace = models.BooleanField(
    #     default=False,
    #     help_text='Ignore inline whitespace when checking output. Equivalent to diff -w')
    # ignore_whitespace_changes = models.BooleanField(
    #     default=False,
    #     help_text='Ignore whitespace changes when checking output. Equivalent to diff -b')
    # ignore_blank_lines = models.BooleanField(
    #     default=False,
    #     help_text='Ignore changes in blank lines when checking output. Equivalent to diff -B')
    #
    # points_for_correct_return_code
    # points_for_correct_stdout
    # points_for_correct_stderr
    #
    # deduction_for_wrong_return_code
    #
    # normal_fdbk_config = models.OneToOneField(
    #     AGTestCommandFeedbackConfig, default=make_default_command_fdbk)
    # ultimate_submission_fdbk_config = models.OneToOneField(
    #     AGTestCommandFeedbackConfig, default=make_default_ultimate_submission_command_fdbk)
    # past_limit_submission_fdbk_config = models.OneToOneField(
    #     AGTestCommandFeedbackConfig, default=make_default_command_fdbk)
    # staff_viewer_fdbk_config = models.OneToOneField(
    #     AGTestCommandFeedbackConfig, default=make_max_command_fdbk)
    #
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
