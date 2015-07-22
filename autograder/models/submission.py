import os
import fnmatch

from django.db import models, transaction
from django.core.exceptions import ValidationError

from autograder.models.model_utils import (
    ModelValidatableOnSave, ManagerWithValidateOnCreate)
from autograder.models import SubmissionGroup

import autograder.shared.global_constants as gc
import autograder.shared.utilities as ut


def _get_submission_file_upload_to_dir(instance, filename):
    value = os.path.join(
        ut.get_submission_relative_dir(instance.submission), filename)
    return value


def _validate_filename(file_obj):
    ut.check_user_provided_filename(file_obj.name)


class _SubmissionManager(models.Manager):
    # TODO: Log the submission and flag it as invalid
    # rather than reject it entirely and keep no record of it.
    @transaction.atomic
    def validate_and_create(self, **kwargs):
        files = kwargs.pop('submitted_files')
        model = self.model(**kwargs)
        model.save()
        for file_obj in files:
            model.submitted_files.add(
                _SubmittedFile(submitted_file=file_obj, submission=model))
        # model.validate_and_save()
        model.full_clean()
        return model


class Submission(ModelValidatableOnSave):
    """
    Represents a single submission for a particular project.

    IMPORTANT: Always use Submission.objects.validate_and_create()
        when creating new submission objects.

    Fields:
        submission_group -- The SubmissionGroup that this submission
            belongs to.
            This field is REQUIRED.

        submitted_files -- The files included in this submission.
            This model's clean() method will verify that these files
            conform to the requirements of the Project that submission_group
            belongs to.

        timestamp -- The timestamp at which this Submission was
            recorded.
            This field is given a value automatically and cannot be
            set manually.

        feedback_level_configuration -- TODO

        status -- TODO (queued, evaluating, finished, invalid)

    Methods:
        get_submitted_files()
        get_submitted_file_names() TODO (convenience method for getting basenames only)

    Overridden methods:
        save()
        clean()
    """
    objects = _SubmissionManager()

    # -------------------------------------------------------------------------

    submission_group = models.ForeignKey(SubmissionGroup)

    ignore_extra_files = models.BooleanField(default=True)

    @property
    def timestamp(self):
        return self._timestamp

    _timestamp = models.DateTimeField(auto_now_add=True, editable=False)

    # -------------------------------------------------------------------------

    def get_submitted_files(self):
        return [obj.submitted_file for obj in self.submitted_files.all()]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        submission_dir = ut.get_submission_dir(self)
        if not os.path.isdir(submission_dir):
            os.makedirs(submission_dir)

    def clean(self):
        super().clean()

        errors = {}
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
                errors['submitted_files'] = 'Missing file: {}'.format(req_file)

        for pattern, min_num, max_num in expected_patterns:
            count = len(fnmatch.filter(submitted_filenames, pattern))
            if count < min_num:
                errors['submitted_files'] = (
                    'Not enough files matching the pattern: ' + pattern)

            if count > max_num:
                errors['submitted_files'] = (
                    'Too many files matching the pattern: ' + pattern)

        for filename in submitted_filenames:
            duplicated = ut.count_if(
                submitted_filenames, lambda name: name == filename) > 1
            if duplicated:
                errors['submitted_files'] = 'Duplicate file: ' + filename

            matches_any_pattern = ut.count_if(
                expected_patterns,
                lambda pattern_obj: fnmatch.fnmatch(
                    filename, pattern_obj.pattern))
            is_extra_file = (
                filename not in required_filenames and
                not matches_any_pattern)
            if is_extra_file:
                errors['submitted_files'] = 'Extra file submitted: ' + filename

        if errors:
            raise ValidationError(errors)


class _SubmittedFile(models.Model):
    submission = models.ForeignKey(Submission, related_name='submitted_files')

    submitted_file = models.FileField(
        upload_to=_get_submission_file_upload_to_dir,
        validators=[_validate_filename],
        max_length=gc.MAX_CHAR_FIELD_LEN * 2)


# class SubmissionFeedbackConfiguration(models.Model):
#     """
#     output_feedback_level -- none, match_no_match_only, diff_first_mismatch_only, full_diff
#     return_code_feedback_level -- none, correct_incorrect_only, actual_only, expected_and_actual
#     timed_out_feedback_level -- none, notify_if_timed_out
#     valgrind_feedback_level -- none, show_valgrind_output, (show_valgrind_and_program_output)
#     compilation_feedback_level -- none, success_failure_only, show_compilation_output

#     test_cases -- none, public_only, all
#     """
#     OUTPUT_FEEDBACK_LEVEL_OPTIONS = (
#         ('NONE', 'None'),
#         ('YESNO', 'Notify the viewer only whether the output matched or not'),
#         ('FULL', 'Show full output diff'),
#     )

#     RETURN_CODE_FEEDBACK_LEVEL_OPTIONS = (
#         ('NONE', 'None'),
#         ('YN', 'Inform match or mismatch only'),
#         ('FD', 'Show '),
#     )
#     output_feedback_level = models.CharField(
#         max_length=gc.MAX_CHAR_FIELD_LEN,
#         choices=OUTPUT_FEEDBACK_LEVEL_OPTIONS)
