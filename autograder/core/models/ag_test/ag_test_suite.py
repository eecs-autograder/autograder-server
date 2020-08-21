from typing import List
from django.core import exceptions
from django.core.exceptions import ValidationError
from django.db import models, connection, transaction

import autograder.core.fields as ag_fields
from autograder.core import constants
from ..ag_model_base import AutograderModel, AutograderModelManager, DictSerializable
from ..project import ExpectedStudentFile, Project, InstructorFile
from ..sandbox_docker_image import SandboxDockerImage, get_default_image_pk


class AGTestSuiteFeedbackConfig(DictSerializable):
    """
    Contains feedback options for an AGTestSuite.
    """
    def __init__(self,
                 visible: bool=True,
                 show_individual_tests: bool=True,
                 show_setup_return_code: bool=True,
                 show_setup_timed_out: bool=True,
                 show_setup_stdout: bool=True,
                 show_setup_stderr: bool=True):
        self.visible = visible
        self.show_individual_tests = show_individual_tests
        self.show_setup_return_code = show_setup_return_code
        self.show_setup_timed_out = show_setup_timed_out
        self.show_setup_stdout = show_setup_stdout
        self.show_setup_stderr = show_setup_stderr

    SERIALIZABLE_FIELDS = [
        'visible',
        'show_individual_tests',
        'show_setup_return_code',
        'show_setup_timed_out',
        'show_setup_stdout',
        'show_setup_stderr',
    ]

    FIELD_DESCRIPTIONS = {
        'show_individual_tests': (
            'Whether to show information about individual tests in a suite or just a '
            'points summary (if available).'),
        'show_setup_stdout': (
            "Whether to show stdout content from a suite's setup command."),
        'show_setup_stderr': (
            "Whether to show stderr content from a suite's setup command."),
    }


class AGTestSuite(AutograderModel):
    """
    A group of autograder test cases to be run inside the same sandbox.
    """
    objects = AutograderModelManager['AGTestSuite']()

    class Meta:
        unique_together = ('name', 'project')
        order_with_respect_to = 'project'

    @staticmethod
    def set_order(project: Project, order: List[int]) -> None:
        if len(order) == 0:
            return

        rejector_suite = project.ag_test_suites.filter(reject_submission_if_setup_fails=True)
        if rejector_suite.count() == 1 and rejector_suite.first().pk != order[0]:
            raise ValidationError(
                'Only the first test suite can be used to reject submissions on setup failure.'
            )

        project.set_agtestsuite_order(order)

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
                     have been added to the sandbox.
                     If this field is empty, then no setup command will be run.""")

    setup_suite_cmd_name = ag_fields.ShortStringField(
        blank=True, help_text="""The name of this suite's setup command.""")

    reject_submission_if_setup_fails = models.BooleanField(
        default=False,
        help_text="""When this field is True and the suite has a setup command,
            the submission will be rejected if that setup command fails.
            This field is only allowed to be True for the first non-deferred AGTestSuite
            (order specified by Project.get_agtestsuite_order()) of the Project.
        """
    )

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

    deferred = models.BooleanField(
        default=False,
        help_text='''If true, this test suite can be graded asynchronously. Deferred suites that
                     have yet to be graded do not prevent members of a group from submitting
                     again.''')

    normal_fdbk_config = ag_fields.ValidatedJSONField(
        AGTestSuiteFeedbackConfig, default=AGTestSuiteFeedbackConfig)
    ultimate_submission_fdbk_config = ag_fields.ValidatedJSONField(
        AGTestSuiteFeedbackConfig, default=AGTestSuiteFeedbackConfig)
    past_limit_submission_fdbk_config = ag_fields.ValidatedJSONField(
        AGTestSuiteFeedbackConfig, default=AGTestSuiteFeedbackConfig)
    staff_viewer_fdbk_config = ag_fields.ValidatedJSONField(
        AGTestSuiteFeedbackConfig, default=AGTestSuiteFeedbackConfig)

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

        if (self.sandbox_docker_image.course is not None
                and self.sandbox_docker_image.course != self.project.course):
            errors['sandbox_docker_image'] = (
                'Sandbox image {} does not belong to the course "{}".'.format(
                    self.sandbox_docker_image.display_name, self.project.course.name
                )
            )

        if self.reject_submission_if_setup_fails:
            if self.deferred:
                raise exceptions.ValidationError({
                    'reject_submission_if_setup_fails': (
                        'Deferred suites cannot be used to reject submissions.'
                    )
                })

            other_reject_suites = self.project.ag_test_suites.exclude(
                pk=self.pk
            ).filter(reject_submission_if_setup_fails=True)
            if other_reject_suites.exists():
                raise exceptions.ValidationError({
                    'reject_submission_if_setup_fails': (
                        'Only one suite per project can reject a submission if its setup fails.'
                    )
                })

            order = self.project.get_agtestsuite_order()
            if len(order) != 0 and order[0] != self.pk:
                raise exceptions.ValidationError({
                    'reject_submission_if_setup_fails': (
                        'Only the first suite of a project can '
                        'reject a submissions if its setup fails.'
                    )
                })

        if errors:
            raise exceptions.ValidationError(errors)

    @transaction.atomic()
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
        'setup_suite_cmd_name',
        'reject_submission_if_setup_fails',

        'sandbox_docker_image',
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

        'sandbox_docker_image',

        'ag_test_cases',
    )

    EDITABLE_FIELDS = (
        'name',

        'instructor_files_needed',
        'read_only_instructor_files',
        'student_files_needed',

        'setup_suite_cmd',
        'setup_suite_cmd_name',
        'reject_submission_if_setup_fails',

        'allow_network_access',
        'deferred',
        'sandbox_docker_image',

        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config'
    )
