import json
# import uuid

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField

# from jsonfield import JSONField
# from picklefield.fields import PickledObjectField
from picklefield.fields import PickledObjectField

import autograder.shared.global_constants as gc


class ClassField(PickledObjectField):
    def __init__(self, class_, **kwargs):
        self._class = class_
        super().__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.update({
            'class_': self._class
        })
        return name, path, args, kwargs

    def get_prep_value(self, value):
        if value is None or isinstance(value, self._class):
            return super().get_prep_value(value)

        raise TypeError(
            'Error preparing value of type {} to the field {}. '
            'Expected value of type {}'.format(
                type(value), self.name, self._class))


class StringListField(ArrayField):
    def __init__(self, string_validators=[],
                 strip_strings=True, allow_empty_strings=False, **kwargs):
        self.base_string_field = models.CharField(
            max_length=gc.MAX_CHAR_FIELD_LEN, blank=allow_empty_strings)
        self.string_validators = string_validators
        self.strip_strings = strip_strings
        self.allow_empty_strings = allow_empty_strings

        super().__init__(self.base_string_field, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs['base_field']
        kwargs.update({
            'string_validators': self.string_validators,
            'strip_strings': self.strip_strings,
            'allow_empty_strings': self.allow_empty_strings
        })
        return name, path, args, kwargs

    def clean(self, value, model_instance):
        if not self.strip_strings:
            return

        for string in value:
            string = string.strip()

        return super().clean(value, model_instance)

    def validate(self, value, model_instance):
        # intentionally models.Field super(), NOT ArrayField super()
        super(ArrayField, self).validate(value, model_instance)
        errors = []
        error_found = False
        for string in value:
            try:
                self.base_field.validate(string, model_instance)
                for validator in self.string_validators:
                    validator(string)
                errors.append('')
            except ValidationError as e:
                errors.append(e.message)
                error_found = True

        if error_found:
            raise ValidationError(errors)

    def run_validators(self, value):
        # intentionally models.Field super(), NOT ArrayField super()
        super(ArrayField, self).run_validators(value)

# -----------------------------------------------------------------------------


class FeedbackConfigurationField(models.TextField):
    def get_prep_value(self, value):
        if value is None:
            return None

        if isinstance(value, dict):
            return json.dumps(value)

        if isinstance(value, FeedbackConfiguration):
            return json.dumps(value.to_json())

        return value

    def to_python(self, value):
        if value is None:
            return None

        if isinstance(value, dict):
            return FeedbackConfiguration(**value)

        if isinstance(value, str):
            return FeedbackConfiguration(**json.loads(value))

        return value

    def validate(self, value, model_instance):
        if value is None:
            return

        value.validate()
        return super().validate(value, model_instance)

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)


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

    # TODO: use enums or named constants instead of strings
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
        'show_compiler_output',
    )

    VALGRIND_FEEDBACK_LEVELS = (
        'no_feedback',
        'errors_or_no_errors_only',
        'show_valgrind_output',
    )

    POINTS_FEEDBACK_LEVELS = (
        'hide',
        # Note: When "show_total" or "show_breakdown" is chosen,
        # it will only show the
        # points from parts of the test case that the
        # student receives feedback on.
        'show_total',
        'show_breakdown',
    )

    @classmethod
    def get_max_feedback(class_):
        return FeedbackConfiguration(
            return_code_feedback_level=class_.RETURN_CODE_FEEDBACK_LEVELS[-1],
            output_feedback_level=class_.OUTPUT_FEEDBACK_LEVELS[-1],
            compilation_feedback_level=class_.COMPILATION_FEEDBACK_LEVELS[-1],
            valgrind_feedback_level=class_.VALGRIND_FEEDBACK_LEVELS[-1],
            points_feedback_level=class_.POINTS_FEEDBACK_LEVELS[-1]
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
