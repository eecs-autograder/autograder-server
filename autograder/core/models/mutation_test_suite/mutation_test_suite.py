from django.core import exceptions
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

import autograder.core.fields as ag_fields
import autograder.core.utils as core_ut
from autograder.core import constants
from ..ag_command import Command
from ..ag_model_base import AutograderModel, DictSerializableMixin
from ..project import Project, InstructorFile, ExpectedStudentFile
from ..sandbox_docker_image import SandboxDockerImage, get_default_image_pk


class BugsExposedFeedbackLevel(core_ut.OrderedEnum):
    no_feedback = 'no_feedback'
    num_bugs_exposed = 'num_bugs_exposed'
    exposed_bug_names = 'exposed_bug_names'


class MutationTestSuiteFeedbackConfig(DictSerializableMixin):
    """
    Contains feedback options for a MutationTestSuite
    """
    def __init__(
            self,
            visible: bool=True,
            show_setup_return_code: bool=True,
            show_setup_stdout: bool=False,
            show_setup_stderr: bool=False,
            show_get_test_names_return_code: bool=False,
            show_get_test_names_stdout: bool=False,
            show_get_test_names_stderr: bool = False,
            show_validity_check_stdout: bool=False,
            show_validity_check_stderr: bool=False,
            show_grade_buggy_impls_stdout: bool=False,
            show_grade_buggy_impls_stderr: bool=False,
            show_invalid_test_names: bool=True,
            show_points: bool=False,
            bugs_exposed_fdbk_level: BugsExposedFeedbackLevel=BugsExposedFeedbackLevel.get_min()):
        self.visible = visible

        self.show_setup_return_code = show_setup_return_code
        self.show_setup_stdout = show_setup_stdout
        self.show_setup_stderr = show_setup_stderr

        self.show_get_test_names_return_code = show_get_test_names_return_code
        self.show_get_test_names_stdout = show_get_test_names_stdout
        self.show_get_test_names_stderr = show_get_test_names_stderr

        self.show_validity_check_stdout = show_validity_check_stdout
        self.show_validity_check_stderr = show_validity_check_stderr

        self.show_grade_buggy_impls_stdout = show_grade_buggy_impls_stdout
        self.show_grade_buggy_impls_stderr = show_grade_buggy_impls_stderr

        self.show_invalid_test_names = show_invalid_test_names
        self.show_points = show_points
        self.bugs_exposed_fdbk_level = bugs_exposed_fdbk_level

    @classmethod
    def default_ultimate_submission_fdbk_config(cls) -> 'MutationTestSuiteFeedbackConfig':
        return MutationTestSuiteFeedbackConfig(
            show_setup_return_code=True,
            show_invalid_test_names=True,
            show_points=True,
            bugs_exposed_fdbk_level=BugsExposedFeedbackLevel.num_bugs_exposed,
        )

    @classmethod
    def default_past_limit_submission_fdbk_config(cls) -> 'MutationTestSuiteFeedbackConfig':
        return MutationTestSuiteFeedbackConfig(
            visible=True,
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
        )

    @classmethod
    def max_fdbk_config(cls) -> 'MutationTestSuiteFeedbackConfig':
        return MutationTestSuiteFeedbackConfig(
            visible=True,
            show_setup_return_code=True,
            show_setup_stdout=True,
            show_setup_stderr=True,
            show_get_test_names_return_code=True,
            show_get_test_names_stdout=True,
            show_get_test_names_stderr=True,
            show_validity_check_stdout=True,
            show_validity_check_stderr=True,
            show_grade_buggy_impls_stdout=True,
            show_grade_buggy_impls_stderr=True,
            show_invalid_test_names=True,
            show_points=True,
            bugs_exposed_fdbk_level=BugsExposedFeedbackLevel.get_max()
        )

    FIELD_DESCRIPTIONS = {}


def new_make_default_setup_cmd() -> Command:
    return Command.from_dict(
        {'cmd': 'true', 'process_spawn_limit': constants.MEDIUM_PROCESS_LIMIT})


def new_make_default_get_student_test_names_cmd() -> Command:
    return Command.from_dict(
        {'cmd': 'true', 'process_spawn_limit': constants.MEDIUM_PROCESS_LIMIT})


def new_make_default_validity_check_command() -> Command:
    return Command.from_dict(
        {'cmd': f'echo {MutationTestSuite.STUDENT_TEST_NAME_PLACEHOLDER}'})


def new_make_default_grade_buggy_impl_command() -> Command:
    return Command.from_dict(
        {'cmd': 'echo {} {}'.format(MutationTestSuite.BUGGY_IMPL_NAME_PLACEHOLDER,
                                    MutationTestSuite.STUDENT_TEST_NAME_PLACEHOLDER)}
    )


class MutationTestSuite(AutograderModel):
    """
    A MutationTestSuite defines a way of grading student-submitted
    test cases against a set of intentionally buggy implementations
    of instructor code.
    """

    class Meta:
        unique_together = ('name', 'project')
        order_with_respect_to = 'project'

    STUDENT_TEST_NAME_PLACEHOLDER = r'${student_test_name}'
    BUGGY_IMPL_NAME_PLACEHOLDER = r'${buggy_impl_name}'

    name = ag_fields.ShortStringField(
        help_text="""The name used to identify this MutationTestSuite.
                     Must be non-empty and non-null.""")
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name='mutation_test_suites',
        help_text="The Project that this mutation test suite belongs to.")

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
    setup_command = ag_fields.ValidatedJSONField(
        Command,
        default=new_make_default_setup_cmd,
        help_text="""A command to be run after student and project files have
                     been added to the sandbox but before any other commands are run.
                     To indicate that no setup command should be run,
                     set use_setup_command to False."""
    )

    get_student_test_names_command = ag_fields.ValidatedJSONField(
        Command,
        default=new_make_default_get_student_test_names_cmd,
        help_text="""This required command should print out a whitespace-separated
                     list of detected student names. The output of this command will
                     be parsed using Python's str.split()."""
    )

    DEFAULT_STUDENT_TEST_MAX = 25
    MAX_STUDENT_TEST_MAX = 50

    max_num_student_tests = models.IntegerField(
        default=DEFAULT_STUDENT_TEST_MAX,
        validators=[MinValueValidator(0), MaxValueValidator(MAX_STUDENT_TEST_MAX)],
        help_text="""The maximum number of test cases students are allowed to submit.
                     If more than this many tests are discovered by the
                     get_student_test_names_command, test names will be discarded
                     from the end of that list.""")

    student_test_validity_check_command = ag_fields.ValidatedJSONField(
        Command,
        default=new_make_default_validity_check_command,
        help_text="""This command will be run once for each detected student test case.
                     An exit status of zero indicates that a student test case is valid,
                     whereas a nonzero exit status indicates that a student test case
                     is invalid.
                     This command must contain the placeholder {} at least once. That
                     placeholder will be replaced with the name of the student test case
                     that is to be checked for validity.
                     """.format(STUDENT_TEST_NAME_PLACEHOLDER)
    )

    grade_buggy_impl_command = ag_fields.ValidatedJSONField(
        Command,
        default=new_make_default_grade_buggy_impl_command,
        help_text="""
            This command will be run once for every (buggy implementation, valid test) pair.
            A nonzero exit status indicates that the valid student tests exposed the
            buggy impl, whereas an exit status of zero indicates that the student
            tests did not expose the buggy impl.
            This command must contain the placeholders {0} and {1}. The placeholder
            {0} will be replaced with the name of a valid student test case.
            The placeholder {1} will be replaced with the name of
            the buggy impl that the student test is being run against.
        """.format(STUDENT_TEST_NAME_PLACEHOLDER, BUGGY_IMPL_NAME_PLACEHOLDER)
    )

    points_per_exposed_bug = models.DecimalField(
        decimal_places=2, max_digits=4,
        default=0, validators=[MinValueValidator(0)],
        help_text="""The number of points to be awarded per buggy implementation exposed by
                     the student test cases. This field is limited to 4 digits total and a maximum
                     of 2 decimal places.""")
    max_points = models.IntegerField(
        null=True, default=None, blank=True,
        validators=[MinValueValidator(0)],
        help_text="""An optional ceiling on the number of points to be awarded.""")

    deferred = models.BooleanField(
        default=False,
        help_text='''If true, this mutation test suite can be graded asynchronously.
                     Deferred suites that have yet to be graded do not prevent members
                     of a group from submitting again.''')

    sandbox_docker_image = models.ForeignKey(
        SandboxDockerImage,
        on_delete=models.SET(get_default_image_pk),
        default=get_default_image_pk,
        related_name='+',
        help_text="The sandbox docker image to use for running this suite."
    )

    # Remove in version 5.0.0
    old_sandbox_docker_image = models.ForeignKey(
        SandboxDockerImage,
        on_delete=models.SET_DEFAULT,
        default='default',
        to_field='name',
        help_text="""The sandbox docker image to use for running this suite."""
    )

    allow_network_access = models.BooleanField(
        default=False,
        help_text='''Specifies whether the sandbox should allow commands run inside of it to
                     make network calls outside of the sandbox.''')

    normal_fdbk_config = ag_fields.ValidatedJSONField(
        MutationTestSuiteFeedbackConfig,
        default=MutationTestSuiteFeedbackConfig,
        help_text='Feedback settings for a normal Submission.'
    )
    ultimate_submission_fdbk_config = ag_fields.ValidatedJSONField(
        MutationTestSuiteFeedbackConfig,
        default=MutationTestSuiteFeedbackConfig.default_ultimate_submission_fdbk_config,
        help_text='Feedback settings for an ultimate Submission.'
    )
    past_limit_submission_fdbk_config = ag_fields.ValidatedJSONField(
        MutationTestSuiteFeedbackConfig,
        default=MutationTestSuiteFeedbackConfig.default_past_limit_submission_fdbk_config,
        help_text='Feedback settings for a Submission that is past the daily limit.'
    )
    staff_viewer_fdbk_config = ag_fields.ValidatedJSONField(
        MutationTestSuiteFeedbackConfig,
        default=MutationTestSuiteFeedbackConfig.max_fdbk_config,
        help_text='Feedback settings for a staff member viewing a Submission from another group.'
    )

    def clean(self) -> None:
        if self.pk is None:
            return

        errors = {}

        for instructor_file in self.instructor_files_needed.all():
            if instructor_file.project != self.project:
                errors['instructor_files_needed'] = (
                    'File {} does not belong to the project "{}".'.format(
                        instructor_file.name, self.project.name))

        for student_file in self.student_files_needed.all():
            if student_file.project != self.project:
                errors['student_files_needed'] = (
                    'Student file pattern {} does not belong to the project "{}".'.format(
                        student_file.pattern, self.project.name))

        if (self.sandbox_docker_image.course is not None
                and self.sandbox_docker_image.course != self.project.course):
            errors['sandbox_docker_image'] = (
                'Sandbox image {} does not belong to the course "{}".'.format(
                    self.sandbox_docker_image.display_name, self.project.course.name
                )
            )

        for cmd_field in ['setup_command',
                          'get_student_test_names_command',
                          'student_test_validity_check_command',
                          'grade_buggy_impl_command']:
            cmd = getattr(self, cmd_field)
            if cmd is None:
                continue

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
        'sandbox_docker_image',
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
        'sandbox_docker_image',
        'allow_network_access',

        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config',
    )

    SERIALIZE_RELATED = (
        'instructor_files_needed',
        'student_files_needed',

        'sandbox_docker_image',
    )
