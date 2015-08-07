import json
# import uuid

from django.db import models
from django.core.exceptions import ValidationError

from jsonfield import JSONField


def _validate_feedback_configuration(config):
    config.validate()


class FeedbackConfigurationField(JSONField):
    def __init__(self, *args, **kwargs):
        kwargs.pop('default', None)

        validators = kwargs.pop('validators', [])
        validators.append(_validate_feedback_configuration)
        return super().__init__(*args, validators=validators, **kwargs)

    def get_prep_value(self, value):
        return super().get_prep_value(value.to_json())

    def to_python(self, value):
        value = super().to_python(value)

        if value is None:
            return None

        if isinstance(value, dict):
            return FeedbackConfiguration(**value)

        return value

    def get_default(self):
        return FeedbackConfiguration()


class FeedbackConfiguration(object):
    """
    FeedbackConfiguration objects store information on how much
    feedback should be given about the results of an autograder
    test case.
    """

    # The following class attributes contain acceptable values
    # for each variable in the configuration.
    # The values in these lists are ordered from least
    # feedback to most feedback.

    RETURN_CODE_FEEDBACK_LEVELS = (
        'no_feedback',
        'correct_or_incorrect_only',
        'show_expected_and_actual_values',
    )

    OUTPUT_FEEDBACK_LEVELS = (
        'no_feedback',
        'correct_or_incorrect_only',
        'show_expected_and_actual_values',
    )

    COMPILATION_FEEDBACK_LEVELS = (
        'no_feedback',
        'success_or_failure_only',
        'show_error_messages',
    )

    VALGRIND_FEEDBACK_LEVELS = (
        'no_feedback',
        'errors_or_no_errors_only',
        'show_valgrind_output',
    )

    POINTS_FEEDBACK_LEVELS = (
        'hide',
        # Note: When "show_total" is chosen, it will only show the
        # total calculated from parts of the test case that the
        # student receives feedback on.
        'show_total',
        'show_breakdown',
    )

    def __init__(self, **kwargs):
        self.return_code_feedback_level = kwargs.get(
            'return_code_feedback_level',
            FeedbackConfiguration.RETURN_CODE_FEEDBACK_LEVELS[0])

        self.output_feedback_level = kwargs.get(
            'output_feedback_level',
            FeedbackConfiguration.OUTPUT_FEEDBACK_LEVELS[0])

        self.compilation_feedback_level = kwargs.get(
            'compilation_feedback_level',
            FeedbackConfiguration.COMPILATION_FEEDBACK_LEVELS[0])

        self.valgrind_feedback_level = kwargs.get(
            'valgrind_feedback_level',
            FeedbackConfiguration.VALGRIND_FEEDBACK_LEVELS[0])

        self.points_feedback_level = kwargs.get(
            'points_feedback_level',
            FeedbackConfiguration.POINTS_FEEDBACK_LEVELS[0])

    def __eq__(self, other):
        try:
            return (
                self.return_code_feedback_level == other.return_code_feedback_level and
                self.output_feedback_level == other.output_feedback_level and
                self.compilation_feedback_level == other.compilation_feedback_level and
                self.valgrind_feedback_level == other.valgrind_feedback_level and
                self.points_feedback_level == other.points_feedback_level)
        except Exception:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def to_json(self):
        return {
            'return_code_feedback_level': self.return_code_feedback_level,
            'output_feedback_level': self.output_feedback_level,
            'compilation_feedback_level': self.compilation_feedback_level,
            'valgrind_feedback_level': self.valgrind_feedback_level,
            'points_feedback_level': self.points_feedback_level
        }

    def validate(self):
        errors = {}
        if (self.return_code_feedback_level not in
                FeedbackConfiguration.RETURN_CODE_FEEDBACK_LEVELS):
            errors['return_code_feedback_level'] = 'Invalid configuration value'

        if (self.output_feedback_level not in
                FeedbackConfiguration.OUTPUT_FEEDBACK_LEVELS):
            errors['output_feedback_level'] = 'Invalid configuration value'

        if (self.compilation_feedback_level not in
                FeedbackConfiguration.COMPILATION_FEEDBACK_LEVELS):
            errors['compilation_feedback_level'] = 'Invalid configuration value'

        if (self.valgrind_feedback_level not in
                FeedbackConfiguration.VALGRIND_FEEDBACK_LEVELS):
            errors['valgrind_feedback_level'] = 'Invalid configuration value'

        if (self.points_feedback_level not in
                FeedbackConfiguration.POINTS_FEEDBACK_LEVELS):
            errors['points_feedback_level'] = 'Invalid configuration value'

        if errors:
            raise ValidationError(json.dumps(errors))
