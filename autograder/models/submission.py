import os
import fnmatch
import enum

from django.db import models, transaction
from django.core.exceptions import ValidationError

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
        # files = self._discard_unnecessary_files(files, kwargs['project'])
        model = self.model(**kwargs)
        super(Submission, model).save()
        for file_obj in files:
            if file_obj.name in model.get_submitted_file_basenames():
                continue

            if model.file_is_extra(file_obj.name):
                continue

            try:
                model.submitted_files.add(
                    _SubmittedFile.objects.validate_and_create(
                        submitted_file=file_obj, submission=model))
            except ValidationError:
                continue

        # model.validate_and_save()
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


class Submission(models.Model):
    """
    Represents a single submission for a particular project.

    IMPORTANT: Always use Submission.objects.create_submission()
        when creating new submission objects.

    Fields:
        submission_group -- The SubmissionGroup that this submission
            belongs to. Note that this field indirectly links this Submission
            object to a Project.
            This field is REQUIRED.

        submitted_files -- The files included in this submission.
            This model's clean() method will verify that these files
            conform to the requirements of the Project that submission_group
            belongs to.
            If a submission doesn't meet those requirements
            (i.e. it is missing a required file or has
            too many or too few files that match one of the expected patterns),
            the submission will be marked as invalid. Any other extra files
            submitted will be discarded. Also, any files that have illegal
            filenames will be discarded.

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
        validate_and_save()

        get_submitted_files()
        get_submitted_file_basenames()

    Overridden methods:
        save()
        clean()
    """
    objects = _SubmissionManager()

    # -------------------------------------------------------------------------

    # TODO: make this a proper enum once migrations support it enums
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
    def timestamp(self):
        return self._timestamp

    _timestamp = models.DateTimeField(auto_now_add=True, editable=False)

    test_case_feedback_config_override = FeedbackConfigurationField(
        null=True, default=None)
    status = models.CharField(
        max_length=gc.MAX_CHAR_FIELD_LEN, default=GradingStatus.received,
        choices=_GRADING_STATUS_CHOICES)

    invalid_reason = JSONField(default=[])

    # -------------------------------------------------------------------------

    def validate_and_save(self):
        self.full_clean()
        super().save()

    def get_submitted_files(self):
        return [obj.submitted_file for obj in self.submitted_files.all()]

    def get_submitted_file_basenames(self):
        return [
            os.path.basename(obj.submitted_file.name) for
            obj in self.submitted_files.all()]

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
        submitted_filenames = [
            os.path.basename(file_obj.name) for
            file_obj in self.get_submitted_files()
        ]

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

        for filename in submitted_filenames:
            duplicated = ut.count_if(
                submitted_filenames, lambda name: name == filename) > 1
            if duplicated:
                errors.append('Duplicate file: ' + filename)

            # matches_any_pattern = ut.count_if(
            #     expected_patterns,
            #     lambda pattern_obj: fnmatch.fnmatch(
            #         filename, pattern_obj.pattern))
            # is_extra_file = (
            #     filename not in required_filenames and
            #     not matches_any_pattern)
            is_extra_file = self.file_is_extra(filename)
            if is_extra_file:
                errors.append('Extra file submitted: ' + filename)

        if errors:
            raise ValidationError(errors)

    def file_is_extra(self, filename):
        matches_any_pattern = ut.count_if(
            self.submission_group.project.expected_student_file_patterns,
            lambda pattern_obj: fnmatch.fnmatch(
                filename, pattern_obj.pattern))

        return (filename not in self.submission_group.project.required_student_files and
                not matches_any_pattern)


class _SubmittedFile(ModelValidatableOnSave):
    objects = ManagerWithValidateOnCreate()

    class Meta:
        unique_together = ('submitted_file', 'submission')

    submission = models.ForeignKey(Submission, related_name='submitted_files')

    submitted_file = models.FileField(
        upload_to=_get_submission_file_upload_to_dir,
        validators=[_validate_filename],
        max_length=gc.MAX_CHAR_FIELD_LEN * 2)
