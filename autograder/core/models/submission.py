import fnmatch
import os
from typing import List

from django.core import exceptions
from django.core.cache import cache
from django.core.files import File
import django.contrib.postgres.fields as pg_fields
from django.db import models, transaction
from django.utils import timezone

import autograder.core.utils as core_ut
import autograder.core.constants as const
import autograder.core.fields as ag_fields
from autograder.core.models.ag_model_base import ToDictMixin

from . import ag_model_base
from .autograder_test_case.autograder_test_case_result import (
    AutograderTestCaseResult)
from .ag_test.feedback_category import FeedbackCategory


def _get_submission_file_upload_to_dir(submission, filename):
    value = os.path.join(
        core_ut.get_submission_dir(submission), filename)
    return value


class _SubmissionManager(ag_model_base.AutograderModelManager):
    @transaction.atomic()
    def validate_and_create(self, submitted_files, submission_group, timestamp=None, submitter=''):
        """
        This method override handles additional details required for
        creating a Submission.
        - Submitted files are filtered based on the patterns students
          are supposed to submit. Extra files are discarded.
        - A set of AutograderTestCaseResults is created--one for each
          autograder test case associated with this Submission's
          Project.
        Positional args:
            submitted_files -- A list of files being submitted. The
                following checks are performed on this argument:
                - Any extra files are discarded and recorded as such.
                - Any missing files are recorded as such, but the
                    Submission is still accepted.
        """
        if timestamp is None:
            timestamp = timezone.now()
        submission = self.model(submission_group=submission_group,
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
        ag_tests = submission.submission_group.project.autograder_test_cases.all()
        AutograderTestCaseResult.objects.bulk_create([
            AutograderTestCaseResult(test_case=test_case, submission=submission)
            for test_case in ag_tests
        ])
        return submission

    def check_for_missing_files(self, submission):
        submitted_filenames = submission.get_submitted_file_basenames()

        patterns = (submission.submission_group.project
                              .expected_student_file_patterns.all())
        for pattern in patterns:
            count = len(fnmatch.filter(submitted_filenames, pattern.pattern))
            if count < pattern.min_num_matches:
                submission.missing_files[pattern.pattern] = (
                    pattern.min_num_matches - count)

    def file_is_extra(self, submission, filename):
        project = submission.submission_group.project
        for pattern in project.expected_student_file_patterns.all():
            if not fnmatch.fnmatch(filename, pattern.pattern):
                continue

            num_matches_so_far = len(
                fnmatch.filter(submission.submitted_filenames,
                               pattern.pattern))
            if num_matches_so_far == pattern.max_num_matches:
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

    SERIALIZABLE_FIELDS = (
        "submission_group",
        "timestamp",
        "submitter",
        "submitted_filenames",
        "discarded_files",
        "missing_files",
        "status",

        'count_towards_daily_limit',
        'is_past_daily_limit',

        'position_in_queue',
    )

    EDITABLE_FIELDS = ('count_towards_daily_limit',)

    # -------------------------------------------------------------------------

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

    submission_group = models.ForeignKey(
        'SubmissionGroup', related_name='submissions',
        help_text='''
            The SubmissionGroup that this submission belongs to. Note
            that this field indirectly links this Submission object to a
            Project.
            This field is REQUIRED.''')

    timestamp = models.DateTimeField(default=timezone.now)

    submitter = ag_fields.ShortStringField(
        blank=True,
        help_text='''The name of the user who made this submission''')

    @property
    def submitted_files(self):
        """
        An iterable of the files included in this submission.
        """
        return (self.get_file(filename)
                for filename in self.submitted_filenames)

    submitted_filenames = ag_fields.StringArrayField(
        blank=True, default=list,
        help_text='''The names of submitted_files.''')

    discarded_files = ag_fields.StringArrayField(
        default=list, blank=True,
        help_text='''A list of names of files that were discarded when
            this Submission was created.''')

    missing_files = pg_fields.JSONField(
        default=dict, blank=True,
        help_text='''Stores missing filenames and the additional number
            of files needed to satisfy a file pattern requirement.
            Stored as key-value pairs of the form:
            {pattern: num_additional_needed}''')

    status = models.CharField(
        max_length=const.MAX_CHAR_FIELD_LEN, default=GradingStatus.received,
        choices=zip(GradingStatus.values, GradingStatus.values),
        help_text='''The grading status of this submission see
            Submission.GradingStatus for details on allowed values.''')

    count_towards_daily_limit = models.BooleanField(
        default=True,
        help_text='''Indicates whether this submission should count
            towards the daily submission limit.''')

    @property
    def is_past_daily_limit(self):
        '''
        Whether this submission is past the daily submission limit in
        its 24 hour period.
        This value is computed dynamically, and therefore can change
        if other submissions in the same 24 hour period are marked
        or unmarked as counting towards the daily limit.
        '''
        project = self.submission_group.project
        if project.submission_limit_per_day is None:
            return False

        start_datetime, end_datetime = core_ut.get_24_hour_period(
            project.submission_limit_reset_time, self.timestamp)

        num_submissions_before_self = self.submission_group.submissions.filter(
            timestamp__gte=start_datetime,
            timestamp__lt=end_datetime,
            count_towards_daily_limit=True,
            status__in=Submission.GradingStatus.count_towards_limit_statuses,
            pk__lt=self.pk
        ).count()

        return num_submissions_before_self >= project.submission_limit_per_day

    error_msg = models.TextField(
        blank=True,
        help_text='''If status is "error", an error message will be stored here.''')

    # Note: Don't include basic_score in to_dict() serialization. If you
    # want to expose it as part of the server api, do so with a
    # dedicated endpoint and make sure permissions are handled properly
    # based on the standing of the submission (ultimate, past limit,
    # etc.).
    @property
    def basic_score(self):
        """
        The sum of the basic scores for each test case result belonging
        to this submission.
        """
        key = self.basic_score_cache_key
        score = cache.get(key)
        if score is not None:
            return score

        # TODO: one cache hit instead of a lot
        score = sum((result.basic_score for result in self.results.all()))
        cache.set(key, score, timeout=None)
        return score

    @property
    def basic_score_cache_key(self):
        return 'submission_basic_score{}'.format(self.pk)

    @property
    def position_in_queue(self):
        """
        Returns this submissions position in the queue of submissions to
        be graded for the associated project.
        """
        if self.status != Submission.GradingStatus.queued:
            return 0

        return Submission.objects.filter(
            status=Submission.GradingStatus.queued,
            submission_group__project=self.submission_group.project,
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

        submission_dir = core_ut.get_submission_dir(self)
        if not os.path.isdir(submission_dir):
            os.makedirs(submission_dir)

    def get_fdbk(self, fdbk_category: FeedbackCategory) -> 'Submission.FeedbackCalculator':
        return Submission.FeedbackCalculator(self, fdbk_category)

    class FeedbackCalculator(ToDictMixin):
        def __init__(self, submission: 'Submission', fdbk_category: FeedbackCategory):
            self.submission = submission
            self.fdbk_category = fdbk_category

        @property
        def total_points(self):
            raise NotImplementedError

        @property
        def total_points_possible(self):
            raise NotImplementedError

        @property
        def ag_test_suite_results(self) -> List['AGTestSuiteResult']:
            raise NotImplementedError

        def to_dict(self):
            raise NotImplementedError
