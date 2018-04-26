from django.core import exceptions
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

import autograder.core.fields as ag_fields
import autograder.core.utils as core_ut
from autograder.core import constants
from ..ag_command import AGCommand, StdinSource
from ..ag_model_base import AutograderModel
from ..project import Project, InstructorFile, ExpectedStudentFile


class BugsExposedFeedbackLevel(core_ut.OrderedEnum):
    no_feedback = 'no_feedback'
    num_bugs_exposed = 'num_bugs_exposed'
    exposed_bug_names = 'exposed_bug_names'


class StudentTestSuiteFeedbackConfig(AutograderModel):
    visible = models.BooleanField(default=True)

    show_setup_return_code = models.BooleanField(
        default=True,
        help_text=""""Whether to show the return code from the setup command
                      and whether the command timed out.""")
    show_setup_stdout = models.BooleanField(
        default=False, help_text="Whether to show stdout from the setup command.")
    show_setup_stderr = models.BooleanField(
        default=False, help_text="Whether to show stderr from the setup command")

    show_get_test_names_return_code = models.BooleanField(
        default=True,
        help_text=""""Whether to show the return code from the get_test_names command
                      and whether the command timed out.""")
    show_get_test_names_stdout = models.BooleanField(
        default=False, help_text="Whether to show stdout from the get_test_names command.")
    show_get_test_names_stderr = models.BooleanField(
        default=False, help_text="Whether to show stderr from the get_test_names command")

    show_validity_check_stdout = models.BooleanField(
        default=False,
        help_text="Whether to show stdout from all runs of the setup command.")
    show_validity_check_stderr = models.BooleanField(
        default=False,
        help_text="Whether to show stderr from all runs of the setup command.")

    show_grade_buggy_impls_stdout = models.BooleanField(
        default=False,
        help_text="Whether to show stdout from grading all buggy impls.")
    show_grade_buggy_impls_stderr = models.BooleanField(
        default=False,
        help_text="Whether to show stderr from grading all buggy impls.")

    show_invalid_test_names = models.BooleanField(
        default=True,
        help_text="""Whether to show the names of student tests that failed the validity check.
                     Setting this to true will also include information about whether
                     invalid test cases exceeded the validity check command's time limit.""")
    show_points = models.BooleanField(
        default=False,
        help_text="Whether to show how many points were awarded.")

    bugs_exposed_fdbk_level = ag_fields.EnumField(BugsExposedFeedbackLevel,
                                                  default=BugsExposedFeedbackLevel.get_min())

    SERIALIZABLE_FIELDS = (
        'visible',

        'show_setup_return_code',
        'show_setup_stdout',
        'show_setup_stderr',

        'show_get_test_names_return_code',
        'show_get_test_names_stdout',
        'show_get_test_names_stderr',

        'show_validity_check_stdout',
        'show_validity_check_stderr',

        'show_grade_buggy_impls_stdout',
        'show_grade_buggy_impls_stderr',

        'show_invalid_test_names',
        'show_points',

        'bugs_exposed_fdbk_level',
    )

    EDITABLE_FIELDS = (
        'visible',

        'show_setup_return_code',
        'show_setup_stdout',
        'show_setup_stderr',

        'show_get_test_names_return_code',
        'show_get_test_names_stdout',
        'show_get_test_names_stderr',

        'show_validity_check_stdout',
        'show_validity_check_stderr',

        'show_grade_buggy_impls_stdout',
        'show_grade_buggy_impls_stderr',

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


MAX_STUDENT_SUITE_FDBK_SETTINGS = {
    'visible': True,
    'show_setup_return_code': True,
    'show_setup_stdout': True,
    'show_setup_stderr': True,
    'show_get_test_names_return_code': True,
    'show_get_test_names_stdout': True,
    'show_get_test_names_stderr': True,
    'show_validity_check_stdout': True,
    'show_validity_check_stderr': True,
    'show_grade_buggy_impls_stdout': True,
    'show_grade_buggy_impls_stderr': True,
    'show_invalid_test_names': True,
    'show_points': True,
    'bugs_exposed_fdbk_level': BugsExposedFeedbackLevel.get_max()
}


def make_max_student_suite_fdbk() -> int:
    return StudentTestSuiteFeedbackConfig.objects.validate_and_create(
        **MAX_STUDENT_SUITE_FDBK_SETTINGS
    ).pk


def make_default_past_limit_student_suite_fdbk() -> int:
    return StudentTestSuiteFeedbackConfig.objects.validate_and_create(
        visible=False,
        show_setup_return_code=False,
        show_setup_stdout=False,
        show_setup_stderr=False,
        show_get_test_names_return_code=False,
        show_get_test_names_stdout=False,
        show_get_test_names_stderr=False,
        show_validity_check_stdout=False,
        show_validity_check_stderr=False,
        show_grade_buggy_impls_stdout=False,
        show_grade_buggy_impls_stderr=False,
        show_invalid_test_names=False,
        show_points=False,
        bugs_exposed_fdbk_level=BugsExposedFeedbackLevel.get_min()
    ).pk


def make_default_setup_cmd() -> int:
    return AGCommand.objects.validate_and_create(
        cmd='true', process_spawn_limit=constants.MEDIUM_PROCESS_LIMIT).pk


def make_default_get_student_test_names_cmd() -> int:
    return AGCommand.objects.validate_and_create(
        cmd='true', process_spawn_limit=constants.MEDIUM_PROCESS_LIMIT).pk


def make_default_validity_check_command() -> int:
    return AGCommand.objects.validate_and_create(
        cmd='echo {}'.format(StudentTestSuite.STUDENT_TEST_NAME_PLACEHOLDER)
    ).pk


def make_default_grade_buggy_impl_command() -> int:
    return AGCommand.objects.validate_and_create(
        cmd='echo {} {}'.format(StudentTestSuite.BUGGY_IMPL_NAME_PLACEHOLDER,
                                StudentTestSuite.STUDENT_TEST_NAME_PLACEHOLDER)
    ).pk


class StudentTestSuite(AutograderModel):
    """
    A StudentTestSuite defines a way of grading student-submitted
    test cases against a set of intentionally buggy implementations
    of instructor code.
    """

    class Meta:
        unique_together = ('name', 'project')
        order_with_respect_to = 'project'

    STUDENT_TEST_NAME_PLACEHOLDER = r'${student_test_name}'
    BUGGY_IMPL_NAME_PLACEHOLDER = r'${buggy_impl_name}'

    name = ag_fields.ShortStringField(
        help_text="""The name used to identify this StudentTestSuite.
                     Must be non-empty and non-null.""")
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name='student_test_suites',
        help_text="The Project that this student test suite belongs to.")

    instructor_files_needed = models.ManyToManyField(
        InstructorFile,
        help_text="""The project files that will be copied into the sandbox before the suite
                     is graded.""")

    read_only_instructor_files = models.BooleanField(
        default=True,
        help_text="""When True, project files needed for this suite will be read-only when this
                     suite is graded.""")

    student_files_needed = models.ManyToManyField(
        ExpectedStudentFile,
        help_text='''Student-submitted files matching these patterns will be copied into the
                     sandbox before the suite is graded.''')

    buggy_impl_names = ag_fields.StringArrayField(
        strip_strings=True,
        blank=True,
        default=list,
        help_text="The names of buggy implementations that student tests should be run against.")

    use_setup_command = models.BooleanField(default=False)
    setup_command = models.OneToOneField(
        AGCommand,
        on_delete=models.PROTECT,
        related_name='+',
        default=make_default_setup_cmd,
        help_text="""A command to be run after student and project files have
                     been added to the sandbox but before any other commands are run.
                     The AGCommand's 'cmd' field must not be blank. To indicate that no
                     setup command should be run, set use_setup_command to False.""")
    get_student_test_names_command = models.OneToOneField(
        AGCommand,
        on_delete=models.PROTECT,
        related_name='+',
        blank=True,
        default=make_default_get_student_test_names_cmd,
        help_text="""This required command should print out a whitespace-separated
                     list of detected student names. The output of this command will
                     be parsed using Python's str.split().
                     NOTE: This AGCommand's 'cmd' field must not be blank.""")

    DEFAULT_STUDENT_TEST_MAX = 25
    MAX_STUDENT_TEST_MAX = 50

    max_num_student_tests = models.IntegerField(
        default=DEFAULT_STUDENT_TEST_MAX,
        validators=[MinValueValidator(0), MaxValueValidator(MAX_STUDENT_TEST_MAX)],
        help_text="""The maximum number of test cases students are allowed to submit.
                     If more than this many tests are discovered by the
                     get_student_test_names_command, test names will be discarded
                     from the end of that list.""")

    student_test_validity_check_command = models.OneToOneField(
        AGCommand,
        on_delete=models.PROTECT,
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
        on_delete=models.PROTECT,
        related_name='+',
        blank=True,
        default=make_default_grade_buggy_impl_command,
        help_text="""This command will be run once for every (buggy implementation, valid test)
                    pair.
                     A nonzero exit status indicates that the valid student tests exposed the
                     buggy impl, whereas an exit status of zero indicates that the student
                     tests did not expose the buggy impl.
                     This command must contain the placeholders {0} and {1}. The placeholder
                     {0} will be replaced with the name of a valid student test case.
                     The placeholder {1} will be replaced with the name of
                     the buggy impl that the student test is being run against.
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

    docker_image_to_use = ag_fields.EnumField(
        constants.SupportedImages,
        default=constants.SupportedImages.default,
        help_text="An identifier for the Docker image that the sandbox should be created from.")

    allow_network_access = models.BooleanField(
        default=False,
        help_text='''Specifies whether the sandbox should allow commands run inside of it to
                     make network calls outside of the sandbox.''')

    normal_fdbk_config = models.OneToOneField(
        StudentTestSuiteFeedbackConfig,
        on_delete=models.PROTECT,
        default=make_default_command_fdbk,
        related_name='+',
        help_text='Feedback settings for a normal Submission.')
    ultimate_submission_fdbk_config = models.OneToOneField(
        StudentTestSuiteFeedbackConfig,
        on_delete=models.PROTECT,
        default=make_default_ultimate_submission_command_fdbk,
        related_name='+',
        help_text='Feedback settings for an ultimate Submission.')
    past_limit_submission_fdbk_config = models.OneToOneField(
        StudentTestSuiteFeedbackConfig,
        on_delete=models.PROTECT,
        default=make_default_past_limit_student_suite_fdbk,
        related_name='+',
        help_text='Feedback settings for a Submission that is past the daily limit.')
    staff_viewer_fdbk_config = models.OneToOneField(
        StudentTestSuiteFeedbackConfig,
        on_delete=models.PROTECT,
        default=make_max_student_suite_fdbk,
        related_name='+',
        help_text='Feedback settings for a staff member viewing a Submission from another group.')

    def clean(self):
        if self.pk is None:
            return

        errors = {}

        for instructor_file in self.instructor_files_needed.all():
            if instructor_file.project != self.project:
                errors['instructor_files_needed'] = (
                    'File {} does not belong to the project "{}".'.format(
                        instructor_file.name, self.project.name))

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

            if cmd.stdin_instructor_file.project != self.project:
                errors[cmd_field] = 'In {}, file "{}" does not belong to the project "{}"'.format(
                    cmd_field, cmd.stdin_instructor_file.name, self.project.name)

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

        'instructor_files_needed',
        'read_only_instructor_files',
        'student_files_needed',
        'buggy_impl_names',

        'use_setup_command',
        'setup_command',
        'get_student_test_names_command',
        'max_num_student_tests',
        'student_test_validity_check_command',
        'grade_buggy_impl_command',

        'points_per_exposed_bug',
        'max_points',

        'deferred',
        'docker_image_to_use',
        'allow_network_access',

        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config',

        'last_modified',
    )

    EDITABLE_FIELDS = (
        'name',

        'instructor_files_needed',
        'read_only_instructor_files',
        'student_files_needed',
        'buggy_impl_names',

        'use_setup_command',
        'setup_command',
        'get_student_test_names_command',
        'max_num_student_tests',
        'student_test_validity_check_command',
        'grade_buggy_impl_command',

        'points_per_exposed_bug',
        'max_points',

        'deferred',
        'docker_image_to_use',
        'allow_network_access',

        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config',

        'last_modified',
    )

    SERIALIZE_RELATED = (
        'instructor_files_needed',
        'student_files_needed',
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
