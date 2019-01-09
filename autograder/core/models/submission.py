import fnmatch
import os

import django.contrib.postgres.fields as pg_fields
from django.core import exceptions
from django.core.files import File
from django.db import models, transaction
from django.db.models import Prefetch
from django.utils import timezone

import autograder.core.constants as const
import autograder.core.fields as ag_fields
import autograder.core.utils as core_ut
from autograder.core import constants
from . import ag_model_base
from .ag_test.ag_test_case_result import AGTestCaseResult
from .ag_test.ag_test_command_result import AGTestCommandResult
from .ag_test.feedback_category import FeedbackCategory
from .student_test_suite import StudentTestSuiteResult


def _get_submission_file_upload_to_dir(submission, filename):
    value = os.path.join(
        core_ut.get_submission_dir(submission), filename)
    return value


class _SubmissionManager(ag_model_base.AutograderModelManager):
    def validate_and_create(self, submitted_files, group, timestamp=None, submitter=''):
        """
        This method override handles additional details required for
        creating a Submission.
        - Submitted files are filtered based on the patterns students
          are supposed to submit. Extra files are discarded.
        Positional args:
            submitted_files -- A list of files being submitted. The
                following checks are performed on this argument:
                - Any extra files are discarded and recorded as such.
                - Any missing files are recorded as such, but the
                    Submission is still accepted.
        """
        if timestamp is None:
            timestamp = timezone.now()

        with transaction.atomic():
            submission = self.model(group=group,
                                    project=group.project,
                                    timestamp=timestamp,
                                    submitter=submitter)
            # The submission needs to be saved so that a directory is
            # created for it.
            submission.save()

            for file_ in submitted_files:
                try:
                    core_ut.check_filename(file_.name)
                except exceptions.ValidationError:
                    submission.discarded_files.append(file_.name)
                    continue

                if self.file_is_extra(submission, file_.name):
                    submission.discarded_files.append(file_.name)
                    continue

                submission.submitted_filenames.append(file_.name)
                write_dest = _get_submission_file_upload_to_dir(
                    submission, file_.name)
                with open(write_dest, 'wb') as f:
                    for chunk in file_.chunks():
                        f.write(chunk)

            self.check_for_missing_files(submission)
            submission.save()
            return submission

    def check_for_missing_files(self, submission):
        submitted_filenames = submission.get_submitted_file_basenames()

        expected_student_files = submission.group.project.expected_student_files.all()
        for expected_file in expected_student_files:
            count = len(fnmatch.filter(submitted_filenames, expected_file.pattern))
            if count < expected_file.min_num_matches:
                submission.missing_files[expected_file.pattern] = (
                    expected_file.min_num_matches - count)

    def file_is_extra(self, submission, filename):
        project = submission.group.project
        for expected_file in project.expected_student_files.all():
            if not fnmatch.fnmatch(filename, expected_file.pattern):
                continue

            num_matches_so_far = len(
                fnmatch.filter(submission.submitted_filenames,
                               expected_file.pattern))
            if num_matches_so_far == expected_file.max_num_matches:
                continue

            return False

        return True


class Submission(ag_model_base.AutograderModel):
    """
    This model stores a set of files submitted by a student for grading.
    """
    objects = _SubmissionManager()

    class Meta:
        ordering = ['-pk']

    class GradingStatus:
        # The submission has been accepted and saved to the database
        received = 'received'

        # The submission has been queued is waiting to be graded
        queued = 'queued'

        being_graded = 'being_graded'

        # Non-deferred test cases have finished and the group can submit
        # again.
        waiting_for_deferred = 'waiting_for_deferred'
        # All test cases have finished grading.
        finished_grading = 'finished_grading'

        # A student removed their submission from the queue before it
        # started being graded.
        removed_from_queue = 'removed_from_queue'

        # Something unexpected occurred during the grading process.
        error = 'error'

        values = [
            received,
            queued,
            being_graded,
            waiting_for_deferred,
            finished_grading,
            removed_from_queue,
            error,
        ]

        # These statuses bar users from making another submission
        # while the current one is active.
        active_statuses = [received, queued, being_graded]

        # A submission should only be counted towards the daily limit if
        # it has one of these statuses.
        count_towards_limit_statuses = [
            received, queued, being_graded,
            waiting_for_deferred, finished_grading]

    # -------------------------------------------------------------------------

    group = models.ForeignKey(
        'core.Group', related_name='submissions',
        on_delete=models.CASCADE,
        help_text="""
            The SubmissionGroup that this submission belongs to. Note
            that this field indirectly links this Submission object to a
            Project.
            This field is REQUIRED.""")

    project = models.ForeignKey(
        'core.Project', related_name='submissions',
        # Project will cascade-delete groups, groups will cascade-delete
        # submissions.
        on_delete=models.DO_NOTHING,
        help_text='A shortcut for submission.group.project.',
    )

    timestamp = models.DateTimeField(default=timezone.now)

    submitter = ag_fields.ShortStringField(
        blank=True,
        help_text="""The name of the user who made this submission""")

    @property
    def submitted_files(self):
        """
        An iterable of the files included in this submission.
        """
        return (self.get_file(filename) for filename in self.submitted_filenames)

    submitted_filenames = ag_fields.StringArrayField(
        blank=True, default=list,
        help_text="""The names of files that were submitted,
                     excluding those that were discarded.""")

    discarded_files = ag_fields.StringArrayField(
        default=list, blank=True,
        help_text="""The names of files that were discarded when this Submission was created.""")

    missing_files = pg_fields.JSONField(
        default=dict, blank=True,
        help_text="""Stores missing filenames and the additional number
            of files needed to satisfy a file pattern requirement.
            Stored as key-value pairs of the form:
            {pattern: num_additional_needed}""")

    status = models.CharField(
        max_length=const.MAX_CHAR_FIELD_LEN, default=GradingStatus.received,
        choices=zip(GradingStatus.values, GradingStatus.values),
        help_text="""The grading status of this submission see
            Submission.GradingStatus for details on allowed values.""")

    count_towards_daily_limit = models.BooleanField(
        default=True,
        help_text="""Indicates whether this submission should count
            towards the daily submission limit.""")

    is_past_daily_limit = models.BooleanField(
        default=False,
        help_text="Whether this submission is past the daily submission limit.")

    is_bonus_submission = models.BooleanField(
        default=False,
        help_text="""When True, indicates that the group that made this
            submission should be able to request normal feedback for
            this submission's results.
            Note: If this field is True, is_past_daily_limit should be
            False."""
    )

    count_towards_total_limit = models.BooleanField(
        default=True,
        help_text="Whether this submission should count towards the total submission limit."
    )

    does_not_count_for = pg_fields.ArrayField(
        models.CharField(max_length=constants.MAX_USERNAME_LEN),
        default=list,
        blank=True,
        help_text="""A list of users for whom this submission will NOT
            count as their final graded submission. Users are added to
            this list if they are out of late days and another group
            member (who still has late days remaining) uses their own
            late day to submit.""")

    error_msg = models.TextField(
        blank=True,
        help_text="""If status is "error", an error message will be stored here.""")

    denormalized_ag_test_results = pg_fields.JSONField(
        default=dict, blank=True,
        help_text="""Stores denormalized AG test results in order to avoid
                     expensive joins when getting submission result feedback.
                     To update this field, use
                     autograder.core.submission_feedback.update_denormalized_ag_test_results

                     Data format:
{
    "<ag test suite pk>": {
        <ag test suite result data>,
        "ag_test_case_results": {
            "<ag test case pk>": {
                <ag test case result data>,
                "ag_test_command_results": <ag test command result data>
            }
        }
    }
}
        """
    )

    @property
    def position_in_queue(self) -> int:
        """
        Returns this submission's position in the queue of submissions
        to be graded for the associated project.
        """
        if self.status != Submission.GradingStatus.queued:
            return 0

        return Submission.objects.filter(
            status=Submission.GradingStatus.queued,
            group__project=self.group.project,
            pk__lte=self.pk
        ).count()

    # -------------------------------------------------------------------------

    def get_file(self, filename, mode='rb'):
        """
        Returns a Django File object containing the submitted file with
        the given name. The file is opened using the specified mode
        (mode can be any valid value for the same argument to the Python
        open() function).
        If the file doesn't exist, ObjectDoesNotExist will be raised.
        """
        self._check_file_exists(filename)
        return File(
            open(self._get_submitted_file_dir(filename), mode),
            name=os.path.basename(filename))

    def _check_file_exists(self, filename):
        if filename not in self.submitted_filenames:
            raise exceptions.ObjectDoesNotExist()

    def _get_submitted_file_dir(self, filename):
        return os.path.join(core_ut.get_submission_dir(self), filename)

    def get_submitted_file_basenames(self):
        return self.submitted_filenames

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # result_output_dir is a subdir of the submission dir
        result_output_dir = core_ut.get_result_output_dir(self)
        if not os.path.isdir(result_output_dir):
            os.makedirs(result_output_dir, exist_ok=True)

    SERIALIZABLE_FIELDS = (
        'pk',
        'group',
        'timestamp',
        'submitter',
        'submitted_filenames',
        'discarded_files',
        'missing_files',
        'status',

        'count_towards_daily_limit',
        'is_past_daily_limit',
        'is_bonus_submission',

        'count_towards_total_limit',

        'does_not_count_for',

        'position_in_queue',
    )

    EDITABLE_FIELDS = ('count_towards_daily_limit', 'count_towards_total_limit')


# These functions return querysets that are optimized to return
# the requested data in as few database hits as possible. The
# results are also properly sorted. Note that the result objects
# are ordered by the '_order' column added by Django to models
# that use order_with_respect_to.


def get_submissions_with_results_queryset(base_manager=Submission.objects):
    student_suite_result_queryset = get_student_test_suite_results_queryset()
    prefetch_student_suite_results = Prefetch('student_test_suite_results',
                                              student_suite_result_queryset)

    return base_manager.prefetch_related(prefetch_student_suite_results)


def get_student_test_suite_results_queryset():
    return StudentTestSuiteResult.objects.select_related(
        'student_test_suite__normal_fdbk_config',
        'student_test_suite__ultimate_submission_fdbk_config',
        'student_test_suite__past_limit_submission_fdbk_config',
        'student_test_suite__staff_viewer_fdbk_config',
    )
