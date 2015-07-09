from django.db import models
from django.contrib.postgres.fields import ArrayField
# from django.core.exceptions import ValidationError

from autograder.models.model_utils import (
    ModelValidatableOnSave, ManagerWithValidateOnCreate)
from autograder.models import SubmissionGroup

import autograder.shared.global_constants as gc


class Submission(ModelValidatableOnSave):
    """
    Represents a single submission for a particular project.

    Fields:
        submission_group -- The SubmissionGroup that this submission
            belongs to.
            This field is REQUIRED.

        submitted_files -- The files included in this submission.
            This model's clean() method will verify that these files
            conform to the requirements of the Project that submission_group
            belongs to.

        ignore_extra_files -- When this field is true, any extra files
            submitted that aren't required or expected will be ignored
            and the submission will be processed normally.
            When this field is true, the presence of such files will
            be treated as an error.
            Default value: True

        timestamp -- The timestamp at which this Submission was
            recorded.
            This field is generated and assigned automatically.

        feedback_level_configuration -- TODO

    Overridden methods:
        save()
    """
    objects = ManagerWithValidateOnCreate()

    # -------------------------------------------------------------------------

    submission_group = models.ForeignKey(SubmissionGroup)

    # submitted_files = ArrayField(models.FileField())

    @property
    def timestamp(self):
        return self._timestamp

    _timestamp = models.DateTimeField(auto_now_add=True)


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
