from django.core.cache import cache
from django.core import exceptions
from django.db import models

from ..ag_model_base import AutograderModel

import autograder.core.fields as ag_fields


class AGTestNameFdbkLevel:
    randomly_obfuscate_name = 'randomly_obfuscate_name'
    deterministically_obfuscate_name = 'deterministically_obfuscate_name'
    show_real_name = 'show_real_name'

    values = [randomly_obfuscate_name,
              deterministically_obfuscate_name,
              show_real_name]

    max_lvl = show_real_name


class ReturnCodeFdbkLevel:
    no_feedback = 'no_feedback'
    correct_or_incorrect_only = 'correct_or_incorrect_only'
    show_expected_and_actual_values = 'show_expected_and_actual_values'

    values = [no_feedback,
              correct_or_incorrect_only,
              show_expected_and_actual_values]

    max_lvl = show_expected_and_actual_values


class StdoutFdbkLevel:
    no_feedback = 'no_feedback'
    correct_or_incorrect_only = 'correct_or_incorrect_only'
    show_expected_and_actual_values = 'show_expected_and_actual_values'

    values = [no_feedback,
              correct_or_incorrect_only,
              show_expected_and_actual_values]

    max_lvl = show_expected_and_actual_values


class StderrFdbkLevel:
    no_feedback = 'no_feedback'
    correct_or_incorrect_only = 'correct_or_incorrect_only'
    show_expected_and_actual_values = 'show_expected_and_actual_values'

    values = [no_feedback,
              correct_or_incorrect_only,
              show_expected_and_actual_values]

    max_lvl = show_expected_and_actual_values


class CompilationFdbkLevel:
    no_feedback = 'no_feedback'
    success_or_failure_only = 'success_or_failure_only'
    show_compiler_output = 'show_compiler_output'

    values = [no_feedback,
              success_or_failure_only,
              show_compiler_output]

    max_lvl = show_compiler_output


class ValgrindFdbkLevel:
    no_feedback = 'no_feedback'
    errors_or_no_errors_only = 'errors_or_no_errors_only'
    show_valgrind_output = 'show_valgrind_output'

    values = [no_feedback,
              errors_or_no_errors_only,
              show_valgrind_output]

    max_lvl = show_valgrind_output


class PointsFdbkLevel:
    hide = 'hide'
    show_breakdown = 'show_breakdown'

    values = [hide, show_breakdown]

    max_lvl = show_breakdown


class FeedbackConfig(AutograderModel):
    @classmethod
    def get_serializable_fields(cls):
        return cls.SERIALIZABLE_FIELDS

    SERIALIZABLE_FIELDS = (
        'ag_test_name_fdbk',
        'return_code_fdbk',
        'show_return_code',
        'stdout_fdbk',
        'show_stdout_content',
        'stderr_fdbk',
        'show_stderr_content',
        'compilation_fdbk',
        'valgrind_fdbk',
        'points_fdbk',
    )

    EDITABLE_FIELDS = (
        'ag_test_name_fdbk',
        'return_code_fdbk',
        'show_return_code',
        'stdout_fdbk',
        'show_stdout_content',
        'stderr_fdbk',
        'show_stderr_content',
        'compilation_fdbk',
        'valgrind_fdbk',
        'points_fdbk',
    )

    @classmethod
    def create_with_max_fdbk(cls):
        return cls.objects.validate_and_create(
            ag_test_name_fdbk=AGTestNameFdbkLevel.max_lvl,
            return_code_fdbk=ReturnCodeFdbkLevel.max_lvl,
            show_return_code=True,
            stdout_fdbk=StdoutFdbkLevel.max_lvl,
            show_stdout_content=True,
            stderr_fdbk=StderrFdbkLevel.max_lvl,
            show_stderr_content=True,
            compilation_fdbk=CompilationFdbkLevel.max_lvl,
            valgrind_fdbk=ValgrindFdbkLevel.max_lvl,
            points_fdbk=PointsFdbkLevel.max_lvl,
        )

    @classmethod
    def create_ultimate_submission_default(cls):
        '''
        Returns a feedback configuration that will show the points
        awarded for each test criterion without showing details (such as
        an output comparison) about why those criteria were not met.
        '''
        return cls.objects.validate_and_create(
            ag_test_name_fdbk=AGTestNameFdbkLevel.show_real_name,
            return_code_fdbk=ReturnCodeFdbkLevel.correct_or_incorrect_only,
            show_return_code=False,
            stdout_fdbk=StdoutFdbkLevel.correct_or_incorrect_only,
            show_stdout_content=False,
            stderr_fdbk=StderrFdbkLevel.correct_or_incorrect_only,
            show_stderr_content=False,
            compilation_fdbk=CompilationFdbkLevel.success_or_failure_only,
            valgrind_fdbk=ValgrindFdbkLevel.errors_or_no_errors_only,
            points_fdbk=PointsFdbkLevel.show_breakdown,
        )

    ag_test_name_fdbk = ag_fields.ShortStringField(
        choices=zip(AGTestNameFdbkLevel.values, AGTestNameFdbkLevel.values),
        default=AGTestNameFdbkLevel.show_real_name)

    return_code_fdbk = ag_fields.ShortStringField(
        choices=zip(ReturnCodeFdbkLevel.values, ReturnCodeFdbkLevel.values),
        default=ReturnCodeFdbkLevel.no_feedback)

    show_return_code = models.BooleanField(default=False)

    stdout_fdbk = ag_fields.ShortStringField(
        choices=zip(StdoutFdbkLevel.values, StdoutFdbkLevel.values),
        default=StdoutFdbkLevel.no_feedback)

    show_stdout_content = models.BooleanField(default=False)

    stderr_fdbk = ag_fields.ShortStringField(
        choices=zip(StderrFdbkLevel.values, StderrFdbkLevel.values),
        default=StderrFdbkLevel.no_feedback)

    show_stderr_content = models.BooleanField(default=False)

    compilation_fdbk = ag_fields.ShortStringField(
        choices=zip(CompilationFdbkLevel.values, CompilationFdbkLevel.values),
        default=CompilationFdbkLevel.no_feedback)

    valgrind_fdbk = ag_fields.ShortStringField(
        choices=zip(ValgrindFdbkLevel.values, ValgrindFdbkLevel.values),
        default=ValgrindFdbkLevel.no_feedback)

    points_fdbk = ag_fields.ShortStringField(
        choices=zip(PointsFdbkLevel.values, PointsFdbkLevel.values),
        default=PointsFdbkLevel.hide)

    @property
    def _include_pk(self):
        return False

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        try:
            cache.delete_many(self.ag_test.dependent_cache_keys)
        except exceptions.ObjectDoesNotExist:
            pass
