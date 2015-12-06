import os
import fnmatch
import enum

from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone

from jsonfield import JSONField

from autograder.models import SubmissionGroup
from autograder.models.fields import FeedbackConfigurationField, ClassField
from autograder.models.utils import (
    ModelValidatableOnSave, ManagerWithValidateOnCreate,
    find_matching_pattern)
from .feedback_configuration import StudentTestSuiteFeedbackConfiguration

import autograder.shared.global_constants as gc
import autograder.shared.utilities as ut


def _get_submission_file_upload_to_dir(instance, filename):
    value = os.path.join(
        ut.get_submission_relative_dir(instance.submission), filename)
    return value


def _validate_filename(file_obj):
    ut.check_user_provided_filename(file_obj.name)


class _SubmissionManager(ManagerWithValidateOnCreate):
    @transaction.atomic
    def validate_and_create(self, **kwargs):
        files = kwargs.pop('submitted_files')
        model = self.model(**kwargs)
        # # Submission's save method throws an exception if the model
        # # hasn't already been saved, so we need to call the parent
        # # version here.
        # super(Submission, model).save()
        model.save()
        for file_obj in files:
            if file_obj.name in model.get_submitted_file_basenames():
                model.discarded_files.append(file_obj.name)
                continue

            if model.file_is_extra(file_obj.name):
                model.discarded_files.append(file_obj.name)
                continue

            try:
                # TODO optimize
                model._submitted_files.add(
                    _SubmittedFile.objects.validate_and_create(
                        submitted_file=file_obj, submission=model))
            except ValidationError:
                model.discarded_files.append(file_obj.name)
                continue

        try:
            model.full_clean()
            model._validate_submitted_files()
        except ValidationError as e:
            model.status = Submission.GradingStatus.invalid
            model.invalid_reason_or_error = e.message_dict

        model.save()
        return model

    def create(self, *args, **kwargs):
        raise NotImplementedError(
            'This method is not supported for Submissions')


class Submission(ModelValidatableOnSave):
    """
    Represents a single submission for a particular project.

    IMPORTANT: Always use Submission.objects.validate_and_create()
        when creating new submission objects.

    Submission.objects.validate_and_create() filters through the list
    of submitted files and discards any that:
        - Have illegal filenames
        - Are not required or expected by the Project. This includes files
            that match an expected pattern but exceed the number of allowed
            matches of that pattern. For example, if at most 2 files matching
            the pattern test_*.cpp are expected but 3 such files are submitted,
            the last one listed will be discarded.
        - Are duplicates of another file (in a given group of files with
            the same name, all but one of those
            files are arbitrarily discarded)
    The remaining files are then added to the submission, and
    the normal cleaning process proceeds. If cleaning raises a
    ValidationError, this function will catch it and mark the
    submission as invalid.

    Fields:
        submission_group -- The SubmissionGroup that this submission
            belongs to. Note that this field indirectly links this Submission
            object to a Project.
            This field is REQUIRED.

        submitted_files -- A list of the files included in this submission.

        discarded_files -- A list of names of files that were discarded
            when this Submission was created.
            This field is set automatically.

        timestamp -- The timestamp at which this Submission was
            recorded.
            If no value is specified upon creation, this field is given
            a value automatically.
            Once created, this field is READ ONLY.

        test_case_feedback_config_override -- When this field is not None,
            the feedback configuration here will override the Project level
            feedback configuration.
            Default value: None

        student_test_suite_feedback_config_override -- When this field is not
            None, the student test suite feedback configuration here will
            override the Project level feedback configuration.
            Default value: None

        show_all_test_cases -- A hard override for visible/hidden test cases.
            When this field is True, students will get feedback
            on ALL test cases, including those marked as hidden.
            This field does not effect the feedback configuration.
            Default value: False

        status -- The grading status of this submission. Acceptable values
            and their meanings are as follows:
                GradingStatus.received -- The submission has been received
                    by the server and is being checked for validity.
                GradingStatus.queued -- The submission has been validated
                    and is waiting to be graded.
                GradingStatus.being_graded -- The submission is currently
                    being graded.
                GradingStatus.finished_grading -- The submission is
                    finished being graded.
                GradingStatus.invalid -- The submission failed one or more
                    validation checks that render it ungradeable.
                GradingStatus.error -- Some unexpected error occurred
                    in the grading process.
            Default value: GradingStatus.received

        invalid_reason_or_error -- When a submission is marked as
            invalid or an error occurs while grading, this
            field should store a JSON list describing the reason(s).
            Default value: empty list

    Static methods:
        get_most_recent_submissions()

    Methods:
        get_submitted_file_basenames()

    Overridden methods:
        __init__()
        save()
    """
    objects = _SubmissionManager()

    # -------------------------------------------------------------------------

    # TODO: make this a proper enum once django ORM supports enums
    class GradingStatus(object):
        received = 'received'
        queued = 'queued'
        being_graded = 'being_graded'
        finished_grading = 'finished_grading'
        invalid = 'invalid'
        error = 'error'

    # !!!! IMPORTANT: UPDATE THESE WHENEVER GradingStatus IS CHANGED !!!!
    _GRADING_STATUS_CHOICES = (
        ('received', 'Received'),
        ('queued', 'Queued'),
        ('being_graded', 'Being graded'),
        ('finished_grading', 'Finished grading'),
        ('invalid', 'Invalid'),
        ('error', 'Error')
    )

    # -------------------------------------------------------------------------

    submission_group = models.ForeignKey(
        SubmissionGroup, related_name='submissions')

    @property
    def submitted_files(self):
        return [obj.submitted_file for obj in self._submitted_files.all()]

    discarded_files = ArrayField(
        models.CharField(max_length=gc.MAX_CHAR_FIELD_LEN),
        default=list, blank=True)

    @property
    def timestamp(self):
        return self._timestamp

    _timestamp = models.DateTimeField(auto_now_add=True, editable=False)

    test_case_feedback_config_override = FeedbackConfigurationField(
        null=True, default=None)
    student_test_suite_feedback_config_override = ClassField(
        StudentTestSuiteFeedbackConfiguration, null=True, default=None)
    show_all_test_cases = models.BooleanField(default=False, blank=True)

    status = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN, default=GradingStatus.received,
        choices=_GRADING_STATUS_CHOICES)

    invalid_reason_or_error = JSONField(default=list)

    # -------------------------------------------------------------------------

    @staticmethod
    def get_most_recent_submissions(project):
        """
        Returns a list containing each SubmissionGroup's most
        recent Submission for the given project.
        """
        submissions = []
        for group in project.submission_groups.all():
            try:
                group_sub = group.submissions.order_by('-_timestamp')[0]
            except IndexError:
                continue
            # TODO: get this query working so that we're not grabbing more
            # submissions than we need:
            # .raw(
            #     'SELECT * FROM autograder_submission '
            #     'ORDER BY _timestamp DESC LIMIT 1')[0]
            if group_sub:
                submissions.append(group_sub)

        return submissions

    # -------------------------------------------------------------------------

    def get_submitted_file_basenames(self):
        return [
            os.path.basename(obj.submitted_file.name) for
            obj in self._submitted_files.all()]

    # -------------------------------------------------------------------------

    def __init__(self, *args, **kwargs):
        timestamp = kwargs.pop('timestamp', timezone.now())
        if not timestamp and '_timestamp' in kwargs:
            # __init__ is being called by the actual database
            return super().__init__(*args, **kwargs)

        # __init__ is being called by the user
        return super().__init__(*args, _timestamp=timestamp, **kwargs)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        submission_dir = ut.get_submission_dir(self)
        if not os.path.isdir(submission_dir):
            os.makedirs(submission_dir)

    # TODO: clean method
    # (so that if an invalid submission accidentally gets requeued,
    # it will be marked as invalid again)

    def _validate_submitted_files(self):
        errors = []
        submitted_filenames = self.get_submitted_file_basenames()

        project = self.submission_group.project
        required_filenames = project.required_student_files
        expected_patterns = project.expected_student_file_patterns
        for req_file in required_filenames:
            found = ut.count_if(
                submitted_filenames, lambda name: name == req_file)
            if not found:
                errors.append('Missing file: {}'.format(req_file))

        for pattern, min_num, max_num in expected_patterns:
            count = len(fnmatch.filter(submitted_filenames, pattern))
            if count < min_num:
                errors.append(
                    'Not enough files matching the pattern: ' + pattern)

            if count > max_num:
                errors.append(
                    'Too many files matching the pattern: ' + pattern)

        if errors:
            raise ValidationError({'submitted_files': errors})

    def file_is_extra(self, filename):
        required_files = self.submission_group.project.required_student_files
        pattern_obj = find_matching_pattern(
            filename,
            self.submission_group.project.expected_student_file_patterns)

        if not pattern_obj:
            return filename not in required_files

        submission_dir = ut.get_submission_dir(self)
        num_matches = len(fnmatch.filter(
            os.listdir(submission_dir), pattern_obj.pattern))

        return num_matches == pattern_obj.max_num_matches


class _SubmittedFile(ModelValidatableOnSave):
    objects = ManagerWithValidateOnCreate()

    submission = models.ForeignKey(Submission, related_name='_submitted_files')

    submitted_file = models.FileField(
        upload_to=_get_submission_file_upload_to_dir,
        validators=[_validate_filename],
        max_length=gc.MAX_CHAR_FIELD_LEN * 2)
