from django.core import exceptions
from django.db import models, connection

import autograder.core.fields as ag_fields
from autograder.core import constants
from ..ag_model_base import AutograderModel
from ..project import ExpectedStudentFile, Project, InstructorFile


class AGTestSuiteFeedbackConfig(AutograderModel):
    """
    Contains feedback options for an AGTestSuite.
    """

    visible = models.BooleanField(default=True)

    show_individual_tests = models.BooleanField(
        default=True,
        help_text='''Whether to show information about individual tests in a suite or just a
                     points summary (if available).''')

    show_setup_and_teardown_return_code = models.BooleanField(default=True)
    show_setup_and_teardown_timed_out = models.BooleanField(default=True)

    show_setup_and_teardown_stdout = models.BooleanField(
        default=True,
        help_text="Whether to show stdout content from a suite's setup and teardown commands.")

    show_setup_and_teardown_stderr = models.BooleanField(
        default=True,
        help_text="Whether to show stderr content from a suite's setup and teardown commands.")

    SERIALIZABLE_FIELDS = (
        'visible',
        'show_individual_tests',
        'show_setup_and_teardown_return_code',
        'show_setup_and_teardown_timed_out',
        'show_setup_and_teardown_stdout',
        'show_setup_and_teardown_stderr',
    )

    EDITABLE_FIELDS = (
        'visible',
        'show_individual_tests',
        'show_setup_and_teardown_return_code',
        'show_setup_and_teardown_timed_out',
        'show_setup_and_teardown_stdout',
        'show_setup_and_teardown_stderr',
    )


def make_default_suite_fdbk() -> int:
    """
    Creates a new default AGTestSuiteFeedbackConfig object and returns its pk
    """
    return AGTestSuiteFeedbackConfig.objects.validate_and_create().pk


class AGTestSuite(AutograderModel):
    """
    A group of autograder test cases to be run inside the same sandbox.
    """

    class Meta:
        unique_together = ('name', 'project')
        order_with_respect_to = 'project'

    name = ag_fields.ShortStringField(
        help_text='''The name used to identify this suite.
                     Must be non-empty and non-null.
                     Must be unique among suites that belong to the same project.
                     This field is REQUIRED.''')

    project = models.ForeignKey(Project, related_name='ag_test_suites',
                                on_delete=models.CASCADE,
                                help_text='''The project this suite belongs to.
                                             This field is REQUIRED.''')

    instructor_files_needed = models.ManyToManyField(
        InstructorFile,
        help_text='''The project files that will be copied into the sandbox before the suite's
                     tests are run.''')

    read_only_instructor_files = models.BooleanField(
        default=True,
        help_text="""When True, project files needed for this suite will be read-only when this
                     suite is run.""")

    student_files_needed = models.ManyToManyField(
        ExpectedStudentFile,
        help_text='''Student-submitted files matching these patterns will be copied into the
                     sandbox before the suite's tests are run.''')

    setup_suite_cmd = models.CharField(
        max_length=constants.MAX_COMMAND_LENGTH, blank=True,
        help_text="""A command to be run before this suite's tests are run.
                     This command is only run once at the beginning of the suite.
                     This command will be run after the student and project files
                     have been added to the sandbox.""")

    teardown_suite_cmd = models.CharField(
        max_length=constants.MAX_COMMAND_LENGTH, blank=True,
        help_text="""DEPRECATED. A command to be run after this suite's tests are run.
                     This command is only run once at the end of the suite.""")

    setup_suite_cmd_name = ag_fields.ShortStringField(
        blank=True, help_text="""The name of this suite's setup command.""")
    teardown_suite_cmd_name = ag_fields.ShortStringField(
        blank=True, help_text="""DEPRECATED. The name of this suite's teardown command.""")

    docker_image_to_use = ag_fields.EnumField(
        constants.SupportedImages,
        default=constants.SupportedImages.default,
        help_text="An identifier for the Docker image that the sandbox should be created from.")

    allow_network_access = models.BooleanField(
        default=False,
        help_text='''Specifies whether the sandbox should allow commands run inside of it to
                     make network calls outside of the sandbox.''')

    deferred = models.BooleanField(
        default=False,
        help_text='''If true, this test suite can be graded asynchronously. Deferred suites that
                     have yet to be graded do not prevent members of a group from submitting
                     again.''')

    normal_fdbk_config = models.OneToOneField(
        AGTestSuiteFeedbackConfig,
        on_delete=models.PROTECT,
        default=make_default_suite_fdbk,
        related_name='+',
        help_text='Feedback settings for a normal submission.')
    ultimate_submission_fdbk_config = models.OneToOneField(
        AGTestSuiteFeedbackConfig,
        on_delete=models.PROTECT,
        default=make_default_suite_fdbk,
        related_name='+',
        help_text='Feedback settings for an ultimate submission.')
    past_limit_submission_fdbk_config = models.OneToOneField(
        AGTestSuiteFeedbackConfig,
        on_delete=models.PROTECT,
        default=make_default_suite_fdbk,
        related_name='+',
        help_text='Feedback settings for a submission that is past the daily limit.')
    staff_viewer_fdbk_config = models.OneToOneField(
        AGTestSuiteFeedbackConfig,
        on_delete=models.PROTECT,
        default=make_default_suite_fdbk,
        related_name='+',
        help_text='Feedback settings for a staff member viewing a submission from another group.')

    def clean(self):
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

        if errors:
            raise exceptions.ValidationError(errors)

    def delete(self, *args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute(
                '''UPDATE core_submission
                SET denormalized_ag_test_results = denormalized_ag_test_results #- '{%s}'
                WHERE core_submission.project_id = %s
                ''',
                (self.pk, self.project_id)
            )

        return super().delete()

    SERIALIZABLE_FIELDS = (
        'pk',
        'name',
        'project',
        'last_modified',

        'instructor_files_needed',
        'read_only_instructor_files',
        'student_files_needed',

        'ag_test_cases',

        'setup_suite_cmd',
        'teardown_suite_cmd',

        'setup_suite_cmd_name',
        'teardown_suite_cmd_name',

        'docker_image_to_use',
        'allow_network_access',
        'deferred',

        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config',
    )

    SERIALIZE_RELATED = (
        'instructor_files_needed',
        'student_files_needed',

        'ag_test_cases',
    )

    TRANSPARENT_TO_ONE_FIELDS = (
        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config',
    )

    EDITABLE_FIELDS = (
        'name',

        'instructor_files_needed',
        'read_only_instructor_files',
        'student_files_needed',

        'setup_suite_cmd',
        'teardown_suite_cmd',

        'setup_suite_cmd_name',
        'teardown_suite_cmd_name',

        'allow_network_access',
        'deferred',
        'docker_image_to_use',

        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config'
    )
