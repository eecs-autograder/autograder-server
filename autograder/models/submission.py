import os
import fnmatch
import enum

from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField

from jsonfield import JSONField

from autograder.models import SubmissionGroup
from autograder.models.fields import FeedbackConfigurationField
from autograder.models.utils import (
    ModelValidatableOnSave, ManagerWithValidateOnCreate)

import autograder.shared.global_constants as gc
import autograder.shared.utilities as ut


def _get_submission_file_upload_to_dir(instance, filename):
    value = os.path.join(
        ut.get_submission_relative_dir(instance.submission), filename)
    return value


def _validate_filename(file_obj):
    ut.check_user_provided_filename(file_obj.name)


class _SubmissionManager(models.Manager):
    @transaction.atomic
    def create_submission(self, **kwargs):
        files = kwargs.pop('submitted_files')
        model = self.model(**kwargs)
        # Submission's save method throws an exception if the model
        # hasn't already been saved, so we need to call the parent
        # version here.
        super(Submission, model).save()
        for file_obj in files:
            if file_obj.name in model.get_submitted_file_basenames():
                model.discarded_files.append(file_obj.name)
                continue

            if model.file_is_extra(file_obj.name):
                model.discarded_files.append(file_obj.name)
                continue

            try:
                model._submitted_files.add(
                    _SubmittedFile.objects.validate_and_create(
                        submitted_file=file_obj, submission=model))
            except ValidationError:
                model.discarded_files.append(file_obj.name)
                continue

        try:
            model.full_clean()
        except ValidationError as e:
            model.status = Submission.GradingStatus.invalid
            model.invalid_reason = e.message_dict

        model.save()
        return model

    def create(self, *args, **kwargs):
        raise NotImplementedError(
            'This method is not supported for Submissions')


# TODO: submitted_files protocol and documentation thereof
class Submission(ModelValidatableOnSave):
    """
    Represents a single submission for a particular project.

    IMPORTANT: Always use Submission.objects.create_submission()
        when creating new submission objects.

    Submission.objects.create_submission() filters through the list
    of submitted files and discards any that:
        - Have illegal filenames
        - Are not required or expected by the Project
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

        timestamp -- The timestamp at which this Submission was
            recorded.
            This field is given a value automatically and cannot be
            set manually.

        test_case_feedback_config_override -- When this field is not None,
            the feedback configuration here will override the Project level
            feedback configuration.
            Default value: None

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
            Default value: GradingStatus.received

        invalid_reason -- When a submission is marked as invalid, this
            field should store a JSON list describing the reason(s).
            Default value: empty string

    Methods:
        get_submitted_file_basenames()

    Overridden methods:
        save()
        clean()
    """
    objects = _SubmissionManager()

    # -------------------------------------------------------------------------

    # TODO: make this a proper enum once migrations support enums
    class GradingStatus(object):
        received = 'received'
        queued = 'queued'
        being_graded = 'being_graded'
        finished_grading = 'finished_grading'
        invalid = 'invalid'

    # !!!! IMPORTANT: UPDATE THESE WHENEVER GradingStatus IS CHANGED !!!!
    _GRADING_STATUS_CHOICES = (
        ('received', 'Received'),
        ('queued', 'Queued'),
        ('being_graded', 'Being graded'),
        ('finished_grading', 'Finished grading'),
        ('invalid', 'Invalid')
    )

    # -------------------------------------------------------------------------

    submission_group = models.ForeignKey(SubmissionGroup)

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
    status = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN, default=GradingStatus.received,
        choices=_GRADING_STATUS_CHOICES)

    invalid_reason = JSONField(default=list)

    # -------------------------------------------------------------------------

    def get_submitted_file_basenames(self):
        return [
            os.path.basename(obj.submitted_file.name) for
            obj in self._submitted_files.all()]

    def save(self, *args, **kwargs):
        if not self.pk:
            raise RuntimeError(
                'When creating a new Submission, '
                'you must use Submission.objects.create_submission')

        super().save(*args, **kwargs)

        submission_dir = ut.get_submission_dir(self)
        if not os.path.isdir(submission_dir):
            os.makedirs(submission_dir)

    def clean(self):
        super().clean()

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

        # for filename in submitted_filenames:
        #     duplicated = ut.count_if(
        #         submitted_filenames, lambda name: name == filename) > 1
        #     if duplicated:
        #         errors.append('Duplicate file: ' + filename)

        #     is_extra_file = self.file_is_extra(filename)
        #     if is_extra_file:
        #         errors.append('Extra file submitted: ' + filename)

        if errors:
            raise ValidationError(errors)

    def file_is_extra(self, filename):
        matches_any_pattern = ut.count_if(
            self.submission_group.project.expected_student_file_patterns,
            lambda pattern_obj: fnmatch.fnmatch(
                filename, pattern_obj.pattern))
        required_files = self.submission_group.project.required_student_files
        return (filename not in required_files and
                not matches_any_pattern)


class _SubmittedFile(ModelValidatableOnSave):
    objects = ManagerWithValidateOnCreate()

    submission = models.ForeignKey(Submission, related_name='_submitted_files')

    submitted_file = models.FileField(
        upload_to=_get_submission_file_upload_to_dir,
        validators=[_validate_filename],
        max_length=gc.MAX_CHAR_FIELD_LEN * 2)
