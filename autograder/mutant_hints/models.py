import datetime

from django.core import exceptions
from django.core.validators import MinValueValidator
from django.db import models

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
from autograder.core.models.ag_model_base import AutograderModelManager


class MutantNameObfuscationChoices(models.TextChoices):
    # Do not obfuscate mutant names
    none = 'none'

    # Mutant name obfuscated as "Mutant X", where X is replaced with
    # the index of the mutant in the mutation test suite settings.
    sequential = 'sequential'

    # Mutant name obfuscated as "Mutant X", where X is replaced with
    # a hash generated using the mutant name and the primary key
    # of the current group. This ensures that obfuscated mutant names are
    # deterministic but unique to the group it is shown to.
    hash = 'hash'


class MutationTestSuiteHintConfig(ag_models.AutograderModel):
    objects = AutograderModelManager["MutationTestSuiteHintConfig"]()

    created_at = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    mutation_test_suite = models.OneToOneField(
        ag_models.MutationTestSuite,
        related_name='mutation_test_suite_hint_config',
        on_delete=models.CASCADE,
        help_text="The mutation test suite that these hints are configured for.",
    )

    hints_by_mutant_name = models.JSONField(
        blank=True, default=dict, help_text="A mapping of mutant names to list of hints."
    )

    num_hints_per_day = models.IntegerField(
        blank=True, null=True, default=None,
        validators=[MinValueValidator(1)],
        help_text="The number of hints a student is allowed to unlock per "
                   "submission for this mutation test suite in a 24 hour period. "
                  "None indicates no limit.")

    hint_limit_reset_time = models.TimeField(
        default=datetime.time,
        help_text="""The time at which the number of hints a group
                     has unlocked resets. Defaults to 00:00:00.""")

    hint_limit_reset_timezone = models.TextField(
        default='UTC',
        help_text="""A string representing the timezone to use when computing
            how many hints a group has unlocked in a 24 hour period.""",
        validators=[core_ut.validate_timezone]
    )

    num_hints_per_submission = models.IntegerField(
        blank=True, null=True, default=None,
        validators=[MinValueValidator(1)],
        help_text="The number of hints that can be unlocked for this "
                  "mutation test suite on a single submission. "
                  "None indicates no limit."
    )

    obfuscate_mutant_names = models.TextField(
        blank=True, default=MutantNameObfuscationChoices.none,
        choices=MutantNameObfuscationChoices.choices,
        help_text="""Determines whether the mutant names included with
            unlocked hints should be obfuscated. The options are as follows:
            - "none": Do not obfuscate mutant names
            - "sequential": Mutant names are obfuscated as "Mutant X",
            where X is replaced with the index of the mutant in the
            mutation test suite settings.
            - "hash": Mutant names are obfuscated as "Mutant X", where X
            is replaced with a hash generated using the mutant name and
            some information unique to the current group. This ensures that
            obfuscated mutant names are deterministic but unique to the
            group they are shown to.

        Note that the "Mutant" part of "Mutant X" in the above examples can
        be changed in the obfuscated_mutant_name_prefix field.
        """
    )
    obfuscated_mutant_name_prefix = models.TextField(
        blank=True, default='Mutant',
        help_text="""A user-specified prefix for obfuscated mutant names.
            See "obfuscated_mutant_names" for more information."""
    )

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        error_msg = {
            "hints_by_mutant_name":
                "This field must be a dictionary of strings to list of strings."
        }
        if not isinstance(self.hints_by_mutant_name, dict):
            raise exceptions.ValidationError(error_msg)

        for key, value in self.hints_by_mutant_name.items():
            if not isinstance(key, str):
                raise exceptions.ValidationError(error_msg)

            if not isinstance(value, list):
                raise exceptions.ValidationError(error_msg)

            for item in value:
                if not isinstance(item, str):
                    raise exceptions.ValidationError(error_msg)

    SERIALIZABLE_FIELDS = (
        'pk',
        'mutation_test_suite',
        'hints_by_mutant_name',
        'num_hints_per_day',
        'hint_limit_reset_time',
        'hint_limit_reset_timezone',
        'num_hints_per_submission',
        'obfuscate_mutant_names',
        'obfuscated_mutant_name_prefix',

        'created_at',
        'last_modified',
    )

    EDITABLE_FIELDS = (
        'hints_by_mutant_name',
        'num_hints_per_day',
        'hint_limit_reset_time',
        'hint_limit_reset_timezone',
        'num_hints_per_submission',
        'obfuscate_mutant_names',
        'obfuscated_mutant_name_prefix',
    )


class UnlockedHint(ag_models.AutograderModel):
    objects = AutograderModelManager["UnlockedHint"]()

    created_at = models.DateTimeField(auto_now_add=True)
    unlocked_by = models.TextField(blank=True)

    mutation_test_suite_result = models.ForeignKey(
        ag_models.MutationTestSuiteResult,
        related_name='unlocked_hints',
        on_delete=models.CASCADE)
    mutation_test_suite_hint_config = models.ForeignKey(
        MutationTestSuiteHintConfig,
        on_delete=models.CASCADE)

    mutant_name = models.TextField()
    hint_number = models.IntegerField(
        help_text="""The index of the unlocked hint in the hint configuration
                     (0-indexed).
                     Note that if the hints in the list change, the hint this
                     refers to may be different or no longer exist.""")
    hint_text = models.TextField()

    hint_rating = models.IntegerField(blank=True, null=True, default=None)
    rated_by = models.TextField(blank=True)
    user_comment = models.TextField(blank=True)

    SERIALIZABLE_FIELDS = (
        'pk',
        'created_at',
        'mutation_test_suite_result',
        'mutation_test_suite_hint_config',
        'mutant_name',
        'hint_number',
        'hint_text',
        'hint_rating',
        'user_comment',
    )

    EDITABLE_FIELDS = (
        'hint_rating',
        'user_comment',
        'rated_by',
    )

# Note to self: hints should only be unlockable on submissions eligible for normal feedback
