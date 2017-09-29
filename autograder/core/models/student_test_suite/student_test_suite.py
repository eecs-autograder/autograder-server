from django.core import exceptions
from django.core.validators import MinValueValidator
from django.db import models

from ..ag_model_base import AutograderModel
from ..project import Project, UploadedFile, ExpectedStudentFilePattern
from ..ag_command import AGCommand, StdinSource
import autograder.core.fields as ag_fields
import autograder.core.utils as core_ut


class BugsExposedFeedbackLevel(core_ut.OrderedEnum):
    no_feedback = 'no_feedback'
    num_bugs_exposed = 'num_bugs_exposed'
    exposed_bug_names = 'exposed_bug_names'


class StudentTestSuiteFeedbackConfig(AutograderModel):
    visible = models.BooleanField(default=True)

    show_setup_stdout = models.BooleanField(
        default=False, help_text="Whether to show stdout from the setup command.")
    show_setup_stderr = models.BooleanField(
        default=False, help_text="Whether to show stderr from the setup command")

    show_validity_check_stdout = models.BooleanField(
        default=False,
        help_text="Whether to show stdout from all runs of the setup command.")
    show_validity_check_stderr = models.BooleanField(
        default=False,
        help_text="Whether to show stderr from all runs of the setup command.")

    show_grade_impl_stdout = models.BooleanField(
        default=False,
        help_text="Whether to show stdout from grading all buggy impls.")
    show_grade_impl_stderr = models.BooleanField(
        default=False,
        help_text="Whether to show stderr from grading all buggy impls.")

    show_invalid_test_names = models.BooleanField(
        default=False,
        help_text="Whether to show the names of student tests that failed the validity check.")
    show_points = models.BooleanField(
        default=False,
        help_text="Whether to show how many points were awarded.")

    bugs_exposed_fdbk_level = ag_fields.EnumField(BugsExposedFeedbackLevel,
                                                  default=BugsExposedFeedbackLevel.get_min())

    SERIALIZABLE_FIELDS = (
        'visible',
        'show_setup_stdout',
        'show_setup_stderr',
        'show_validity_check_stdout',
        'show_validity_check_stderr',
        'show_grade_impl_stdout',
        'show_grade_impl_stderr',
        'show_invalid_test_names',
        'show_points',
        'bugs_exposed_fdbk_level',
    )

    EDITABLE_FIELDS = (
        'visible',
        'show_setup_stdout',
        'show_setup_stderr',
        'show_validity_check_stdout',
        'show_validity_check_stderr',
        'show_grade_impl_stdout',
        'show_grade_impl_stderr',
        'show_invalid_test_names',
        'show_points',
        'bugs_exposed_fdbk_level',
    )


def make_default_command_fdbk() -> int:
    return StudentTestSuiteFeedbackConfig.objects.validate_and_create().pk


def make_default_ultimate_submission_command_fdbk() -> int:
    return StudentTestSuiteFeedbackConfig.objects.validate_and_create(
        show_invalid_test_names=True,
        show_points=True,
        bugs_exposed_fdbk_level=BugsExposedFeedbackLevel.num_bugs_exposed,
    ).pk


def make_max_command_fdbk() -> int:
    return StudentTestSuiteFeedbackConfig.objects.validate_and_create(
        show_setup_stdout=True,
        show_setup_stderr=True,
        show_validity_check_stdout=True,
        show_validity_check_stderr=True,
        show_grade_impl_stdout=True,
        show_grade_impl_stderr=True,
        show_invalid_test_names=True,
        show_points=True,
        bugs_exposed_fdbk_level=BugsExposedFeedbackLevel.get_max()
    ).pk


def make_default_ag_command() -> int:
    return AGCommand.objects.validate_and_create(cmd='true').pk


def make_default_validity_check_command() -> int:
    return AGCommand.objects.validate_and_create(
        cmd='echo {}'.format(StudentTestSuite.STUDENT_TEST_NAME_PLACEHOLDER)
    ).pk


def make_default_grade_buggy_impl_command() -> int:
    return AGCommand.objects.validate_and_create(
        cmd='echo {} {}'.format(StudentTestSuite.STUDENT_TEST_NAME_PLACEHOLDER,
                                StudentTestSuite.BUGGY_IMPL_NAME_PLACEHOLDER)
    ).pk


class StudentTestSuite(AutograderModel):
    STUDENT_TEST_NAME_PLACEHOLDER = r'${student_test_name}'
    BUGGY_IMPL_NAME_PLACEHOLDER = r'${buggy_impl_name}'

    name = ag_fields.ShortStringField(
        help_text="""The name used to identify this StudentTestSuite.
                     Must be non-empty and non-null.""")
    project = models.ForeignKey(
        Project, related_name='student_test_suites',
        help_text="The Project that this student test suite belongs to.")

    project_files_needed = models.ManyToManyField(
        UploadedFile,
        help_text="""The project files that will be copied into the sandbox before the suite
                     is graded.""")

    read_only_project_files = models.BooleanField(
        default=True,
        help_text="""When True, project files needed for this suite will be read-only when this
                     suite is graded.""")

    student_files_needed = models.ManyToManyField(
        ExpectedStudentFilePattern,
        help_text='''Student-submitted files matching these patterns will be copied into the
                     sandbox before the suite is graded.''')

    buggy_impl_names = ag_fields.StringArrayField(
        strip_strings=True,
        blank=True,
        default=list,
        help_text="The names of buggy implementations that student tests should be run against.")

    setup_command = models.OneToOneField(
        AGCommand,
        related_name='+',
        blank=True, null=True, default=None,
        help_text="""A command to be run after student and project files have
                     been added to the sandbox but before any other commands are run.
                     A value of None indicates that there is no setup command.
                     If this command is not None, then the AGCommand's 'cmd' field must
                     not be blank.""")
    get_student_test_names_command = models.OneToOneField(
        AGCommand,
        related_name='+',
        blank=True,
        default=make_default_ag_command,
        help_text="""This required command should print out a whitespace-separated
                     list of detected student names. The output of this command will
                     be parsed using Python's str.split().
                     NOTE: This AGCommand's 'cmd' field must not be blank.""")
    student_test_validity_check_command = models.OneToOneField(
        AGCommand,
        related_name='+',
        blank=True,
        default=make_default_validity_check_command,
        help_text="""This command will be run once for each detected student test case.
                     An exit status of zero indicates that a student test case is valid,
                     whereas a nonzero exit status indicates that a student test case
                     is invalid.
                     This command must contain the placeholder {} at least once. That
                     placeholder will be replaced with the name of the student test case
                     that is to be checked for validity.
                     NOTE: This AGCommand's 'cmd' field must not be blank.
                     """.format(STUDENT_TEST_NAME_PLACEHOLDER))
    grade_buggy_impl_command = models.OneToOneField(
        AGCommand,
        related_name='+',
        blank=True,
        default=make_default_grade_buggy_impl_command,
        help_text="""This command will be run once for every (student test, buggy impl) pair.
                     A nonzero exit status indicates that the student test exposed the
                     buggy impl, whereas an exit status of zero indicates that the student
                     test did not expose the buggy impl.
                     As soon as a student test exposes a buggy impl, no other student tests
                     will be run against that buggy impl (the evalution short-circuits).
                     This command must contain the placeholders {} and {} at least once.
                     Those placeholders will be replaced with the name of the student
                     test case and the buggy impl that it is being run against, respectively.
                     NOTE: This AGCommand's 'cmd' field must not be blank.
                     """.format(STUDENT_TEST_NAME_PLACEHOLDER, BUGGY_IMPL_NAME_PLACEHOLDER))

    points_per_exposed_bug = models.IntegerField(
        default=0, validators=[MinValueValidator(0)],
        help_text="""The number of points to be awarded per buggy implementation exposed by
                     the student test cases.""")
    max_points = models.IntegerField(
        null=True, default=None, blank=True,
        validators=[MinValueValidator(0)],
        help_text="""An optional ceiling on the number of points to be awarded.""")

    deferred = models.BooleanField(
        default=False,
        help_text='''If true, this student test suite can be graded asynchronously.
                     Deferred suites that have yet to be graded do not prevent members
                     of a group from submitting again.''')

    normal_fdbk_config = models.OneToOneField(
        StudentTestSuiteFeedbackConfig, default=make_default_command_fdbk,
        related_name='+',
        help_text='Feedback settings for a normal Submission.')
    ultimate_submission_fdbk_config = models.OneToOneField(
        StudentTestSuiteFeedbackConfig, default=make_default_ultimate_submission_command_fdbk,
        related_name='+',
        help_text='Feedback settings for an ultimate Submission.')
    past_limit_submission_fdbk_config = models.OneToOneField(
        StudentTestSuiteFeedbackConfig, default=make_default_command_fdbk,
        related_name='+',
        help_text='Feedback settings for a Submission that is past the daily limit.')
    staff_viewer_fdbk_config = models.OneToOneField(
        StudentTestSuiteFeedbackConfig, default=make_max_command_fdbk,
        related_name='+',
        help_text='Feedback settings for a staff member viewing a Submission from another group.')

    def clean(self):
        if self.pk is None:
            return

        errors = {}

        for proj_file in self.project_files_needed.all():
            if proj_file.project != self.project:
                errors['project_files_needed'] = (
                    'File {} does not belong to the project "{}".'.format(
                        proj_file.name, self.project.name))

        for pattern in self.student_files_needed.all():
            if pattern.project != self.project:
                errors['student_files_needed'] = (
                    'Student file pattern {} does not belong to the project "{}".'.format(
                        pattern.pattern, self.project.name))

        for cmd_field in ['setup_command',
                          'get_student_test_names_command',
                          'student_test_validity_check_command',
                          'grade_buggy_impl_command']:
            cmd = getattr(self, cmd_field)  # type: AGCommand
            if cmd is None:
                continue

            if cmd.stdin_source != StdinSource.project_file:
                continue

            if cmd.stdin_project_file.project != self.project:
                errors[cmd_field] = 'In {}, file "{}" does not belong to the project "{}"'.format(
                    cmd_field, cmd.stdin_project_file.name, self.project.name)

        if self.STUDENT_TEST_NAME_PLACEHOLDER not in self.student_test_validity_check_command.cmd:
            errors['student_test_validity_check_command'] = (
                'Validity check command missing placeholder "{}"'.format(
                    self.STUDENT_TEST_NAME_PLACEHOLDER))

        if self.STUDENT_TEST_NAME_PLACEHOLDER not in self.grade_buggy_impl_command.cmd:
            errors['grade_buggy_impl_command'] = (
                'Grade buggy impl command missing placeholder "{}"'.format(
                    self.STUDENT_TEST_NAME_PLACEHOLDER))

        if self.BUGGY_IMPL_NAME_PLACEHOLDER not in self.grade_buggy_impl_command.cmd:
            errors['grade_buggy_impl_command'] = (
                'Grade buggy impl command missing placeholder "{}"'.format(
                    self.BUGGY_IMPL_NAME_PLACEHOLDER))

        if errors:
            raise exceptions.ValidationError(errors)

    SERIALIZABLE_FIELDS = (
        'pk',
        'name',
        'project',

        'project_files_needed',
        'read_only_project_files',
        'student_files_needed',
        'buggy_impl_names',

        'setup_command',
        'get_student_test_names_command',
        'student_test_validity_check_command',
        'grade_buggy_impl_command',

        'points_per_exposed_bug',
        'max_points',

        'deferred',

        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config',

        'last_modified',
    )

    EDITABLE_FIELDS = (
        'name',

        'project_files_needed',
        'read_only_project_files',
        'student_files_needed',
        'buggy_impl_names',

        'setup_command',
        'get_student_test_names_command',
        'student_test_validity_check_command',
        'grade_buggy_impl_command',

        'points_per_exposed_bug',
        'max_points',

        'deferred',

        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config',

        'last_modified',
    )

    TRANSPARENT_TO_ONE_FIELDS = (
        'setup_command',
        'get_student_test_names_command',
        'student_test_validity_check_command',
        'grade_buggy_impl_command',

        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config',
    )
