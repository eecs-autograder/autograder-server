import uuid

from django.db import models

from polymorphic import PolymorphicManager, PolymorphicModel


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
        'show_expected_and_actual_values'
    )

    OUTPUT_FEEDBACK_LEVELS = (
        'no_feedback',
        'correct_or_incorrect_only',
        'show_expected_and_actual_values'
    )

    COMPILATION_FEEDBACK_LEVELS = (
        'no_feedback',
        'success_or_failure_only',
        'show_error_messages'
    )

    VALGRIND_FEEDBACK_LEVELS = (
        'no_feedback',
        'errors_or_no_errors_only',
        'show_valgrind_output'
    )

    POINTS_FEEDBACK_LEVELS = (
        'hide',
        'show'
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

    def to_json(self):
        return {
            'return_code_feedback_level': self.return_code_feedback_level,
            'output_feedback_level': self.output_feedback_level,
            'compilation_feedback_level': self.compilation_feedback_level,
            'valgrind_feedback_level': self.valgrind_feedback_level,
            'points_feedback_level': self.points_feedback_level
        }

    @property
    def return_code_feedback_level(self):
        self._return_code_feedback_level

    @return_code_feedback_level.setter
    def return_code_feedback_level(self, value):
        if value not in FeedbackConfiguration.RETURN_CODE_FEEDBACK_LEVELS:
            raise ValueError()
        self._return_code_feedback_level = value

    @property
    def output_feedback_level(self):
        self._output_feedback_level

    @output_feedback_level.setter
    def output_feedback_level(self, value):
        if value not in FeedbackConfiguration.OUTPUT_FEEDBACK_LEVELS:
            raise ValueError()
        self._output_feedback_level = value

    @property
    def compilation_feedback_level(self):
        self._compilation_feedback_level

    @compilation_feedback_level.setter
    def compilation_feedback_level(self, value):
        if value not in FeedbackConfiguration.COMPILATION_FEEDBACK_LEVELS:
            raise ValueError()
        self._compilation_feedback_level = value

    @property
    def valgrind_feedback_level(self):
        self._valgrind_feedback_level

    @valgrind_feedback_level.setter
    def valgrind_feedback_level(self, value):
        if value not in FeedbackConfiguration.VALGRIND_FEEDBACK_LEVELS:
            raise ValueError()
        self._valgrind_feedback_level = value

    @property
    def points_feedback_level(self):
        self._points_feedback_level

    @points_feedback_level.setter
    def points_feedback_level(self, value):
        if value not in FeedbackConfiguration.POINTS_FEEDBACK_LEVELS:
            raise ValueError()
        self._points_feedback_level = value


# class PointDistribution(object):
#     def __init__(self, **kwargs):
#         self.


class ManagerWithValidateOnCreate(models.Manager):
    """
    This manager provides a shortcut for creating and validating
    model objects.

    <Model class>.objects.validate_and_create is a shortcut for
        constructing a model object, calling full_clean(), and
        then calling save.

    """
    def validate_and_create(self, **kwargs):
        model = self.model(**kwargs)
        model.full_clean()
        model.save()
        return model


class PolymorphicManagerWithValidateOnCreate(PolymorphicManager):
    """
    Same as ManagerWithValidateOnCreate, but to be used with
    PolymorphicModels.
    """
    def validate_and_create(self, **kwargs):
        model = self.model(**kwargs)
        model.full_clean()
        model.save()
        return model


class ModelValidatableOnSave(models.Model):
    """
    This base class provides shortcut for validating and saving
    model objects.
    <Model object>.validate_and_save() is a shortcut for calling
        <Model object>.full_clean() followed by <Model object>.save()

    Methods:
        validate_and_save()
    """
    def validate_and_save(self):
        self.full_clean()
        self.save()


class PolymorphicModelValidatableOnSave(PolymorphicModel):
    """
    Same as ModelValidatableOnSave, but to be used with polymorphic models.
    """
    def validate_and_save(self):
        self.full_clean()
        self.save()


# class UUIDModelMixin(object):
#     """
#     Mixin class that adds a UUID field called "unique_id" to models.
#     """
#     unique_id = models.UUIDField(
#         primary_key=True, default=uuid.uuid4, editable=False)
