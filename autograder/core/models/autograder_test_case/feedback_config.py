from django.db import models

from ..ag_model_base import AutograderModel
from .autograder_test_case_base import AutograderTestCaseBase

import autograder.utilities.fields as ag_fields


class AGTestNameFdbkLevel:
    randomly_obfuscate_name = 'randomly_obfuscate_name'
    deterministically_obfuscate_name = 'deterministically_obfuscate_name'
    show_real_name = 'show_real_name'

    values = [randomly_obfuscate_name,
              deterministically_obfuscate_name,
              show_real_name]


class ReturnCodeFdbkLevel:
    no_feedback = 'no_feedback'
    correct_or_incorrect_only = 'correct_or_incorrect_only'
    show_expected_and_actual_values = 'show_expected_and_actual_values'

    values = [no_feedback,
              correct_or_incorrect_only,
              show_expected_and_actual_values]


class StdoutFdbkLevel:
    no_feedback = 'no_feedback'
    correct_or_incorrect_only = 'correct_or_incorrect_only'
    show_expected_and_actual_values = 'show_expected_and_actual_values'

    values = [no_feedback,
              correct_or_incorrect_only,
              show_expected_and_actual_values]


class StderrFdbkLevel:
    no_feedback = 'no_feedback'
    correct_or_incorrect_only = 'correct_or_incorrect_only'
    show_expected_and_actual_values = 'show_expected_and_actual_values'

    values = [no_feedback,
              correct_or_incorrect_only,
              show_expected_and_actual_values]


class CompilationFdbkLevel:
    no_feedback = 'no_feedback'
    success_or_failure_only = 'success_or_failure_only'
    show_compiler_output = 'show_compiler_output'

    values = [no_feedback,
              success_or_failure_only,
              show_compiler_output]


class ValgrindFdbkLevel:
    no_feedback = 'no_feedback'
    errors_or_no_errors_only = 'errors_or_no_errors_only'
    show_valgrind_output = 'show_valgrind_output'

    values = [no_feedback,
              errors_or_no_errors_only,
              show_valgrind_output]


class PointsFdbkLevel:
    hide = 'hide'
    show_breakdown = 'show_breakdown'

    values = [hide, show_breakdown]


class FeedbackConfig(AutograderModel):
    DEFAULT_INCLUDE_FIELDS = [
        'ag_test',
        'ag_test_name_fdbk',
        'return_code_fdbk',
        'stdout_fdbk',
        'stderr_fdbk',
        'compilation_fdbk',
        'valgrind_fdbk',
        'points_fdbk',
    ]

    ag_test = models.OneToOneField(AutograderTestCaseBase)

    ag_test_name_fdbk = ag_fields.StringChoiceField(
        choices=AGTestNameFdbkLevel.values,
        default=AGTestNameFdbkLevel.show_real_name)

    return_code_fdbk = ag_fields.StringChoiceField(
        choices=ReturnCodeFdbkLevel.values,
        default=ReturnCodeFdbkLevel.no_feedback)

    stdout_fdbk = ag_fields.StringChoiceField(
        choices=StdoutFdbkLevel.values,
        default=StdoutFdbkLevel.no_feedback)

    stderr_fdbk = ag_fields.StringChoiceField(
        choices=StderrFdbkLevel.values,
        default=StderrFdbkLevel.no_feedback)

    compilation_fdbk = ag_fields.StringChoiceField(
        choices=CompilationFdbkLevel.values,
        default=CompilationFdbkLevel.no_feedback)

    valgrind_fdbk = ag_fields.StringChoiceField(
        choices=ValgrindFdbkLevel.values,
        default=ValgrindFdbkLevel.no_feedback)

    points_fdbk = ag_fields.StringChoiceField(
        choices=PointsFdbkLevel.values,
        default=PointsFdbkLevel.hide)
