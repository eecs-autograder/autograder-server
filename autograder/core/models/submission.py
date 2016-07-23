import fnmatch
import os

from django.core import exceptions
from django.core.cache import cache
from django.core.files import File
import django.contrib.postgres.fields as pg_fields
from django.db import models, transaction
from django.utils import timezone

import autograder.utilities.fields as ag_fields

from . import ag_model_base
from .submission_group import SubmissionGroup

import autograder.core.shared.global_constants as gc
import autograder.core.shared.utilities as ut


def _get_submission_file_upload_to_dir(submission, filename):
    value = os.path.join(
        ut.get_submission_dir(submission), filename)
    return value


def _validate_filename(file_):
    ut.check_user_provided_filename(file_.name)


class _SubmissionManager(ag_model_base.AutograderModelManager):
    @transaction.atomic()
    def validate_and_create(self, submitted_files, **kwargs):
        """
        Positional args:
            submitted_files -- A list of files being submitted. The
                following checks are performed on this argument:
                - Any extra files are discarded and recorded as such.
                - Any missing files are recorded as such, but the
                    Submission is still accepted.
        """
        submission = self.model(**kwargs)
        # The submission needs to be saved so that a directory is
        # created for it.
        submission.save()

        for file_ in submitted_files:
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

    _DEFAULT_TO_DICT_FIELDS = [
        "submission_group",
        "timestamp",
        "submitter",
        "submitted_filenames",
        "discarded_files",
        "missing_files",
        "status",
        "grading_errors",

        'count_towards_daily_limit',
        'is_past_daily_limit',
    ]

    @classmethod
    def get_default_to_dict_fields(class_):
        return class_._DEFAULT_TO_DICT_FIELDS

    _EDITABLE_FIELDS = frozenset(['count_towards_daily_limit'])

    @classmethod
    def get_editable_fields(class_):
        return class_._EDITABLE_FIELDS

    # -------------------------------------------------------------------------

    class GradingStatus:
        # The server has saved the submission.
        received = 'received'

        # The submission is waiting to be graded
        queued = 'queued'

        being_graded = 'being_graded'
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
            finished_grading,
            removed_from_queue,
            error,
        ]

        active_statuses = [received, queued, being_graded]

    # -------------------------------------------------------------------------

    submission_group = models.ForeignKey(
        SubmissionGroup, related_name='submissions',
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
        max_length=gc.MAX_CHAR_FIELD_LEN, default=GradingStatus.received,
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

        start_datetime, end_datetime = ut.get_24_hour_period(
            project.submission_limit_reset_time, self.timestamp)

        num_submissions_before_self = self.submission_group.submissions.filter(
            timestamp__gte=start_datetime,
            timestamp__lt=end_datetime,
            count_towards_daily_limit=True,
            pk__lt=self.pk
        ).count()

        return num_submissions_before_self >= project.submission_limit_per_day

    grading_errors = ag_fields.StringArrayField(
        default=list, blank=True,
        help_text='''A list of errors that occurred while grading this
            submission''')

    # Note: Don't include basic_score in to_dict() serialization. If you
    # want to expose it as part of the server api, do so with a
    # dedicated endpoint and make sure permissions are handled properly
    # based on the standing of the submission (ultimate, past limit,
    # etc.).
    @property
    def basic_score(self):
        '''
        The sum of the basic scores for each test case result belonging
        to this submission.
        '''
        key = self.basic_score_cache_key
        score = cache.get(key)
        if score is not None:
            return score

        score = sum((result.basic_score for result in self.results.all()))
        cache.set(key, score, timeout=None)
        return score

    @property
    def basic_score_cache_key(self):
        return 'submission_basic_score{}'.format(self.pk)

    # -------------------------------------------------------------------------

    def get_file(self, filename, mode='rb'):
        '''
        Returns a Django File object containing the submitted file with
        the given name. The file is opened using the specified mode
        (mode can be any valid value for the same argument to the Python
        open() function).
        If the file doesn't exist, ObjectDoesNotExist will be raised.
        '''
        self._check_file_exists(filename)
        return File(
            open(self._get_submitted_file_dir(filename), mode),
            name=os.path.basename(filename))

    def _check_file_exists(self, filename):
        if filename not in self.submitted_filenames:
            raise exceptions.ObjectDoesNotExist()

    def _get_submitted_file_dir(self, filename):
        return os.path.join(ut.get_submission_dir(self), filename)

    @staticmethod
    def get_most_recent_submissions(project):
        """
        Returns a list containing each SubmissionGroup's most
        recent Submission for the given project.
        """
        submissions = []
        for group in project.submission_groups.all():
            try:
                group_sub = group.submissions.first()
            except IndexError:
                continue
            if group_sub:
                submissions.append(group_sub)

        return submissions

    def get_submitted_file_basenames(self):
        return self.submitted_filenames

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        submission_dir = ut.get_submission_dir(self)
        if not os.path.isdir(submission_dir):
            os.makedirs(submission_dir)
