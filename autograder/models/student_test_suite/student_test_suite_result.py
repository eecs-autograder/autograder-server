from django.db import models
import django.contrib.postgres.fields as pg_fields

from autograder.models import Submission
from .. import fields as ag_fields


class StudentTestCaseEvaluationResult:
    """
    student_test_case_name

    compilation_return_code
    compilation_standard_output
    compilation_standard_error_output

    valid (store True/False)
    validity_check_standard_output
    validity_check_standard_error_output

    buggy_implementations_exposed
    """
    def __init__(self, student_test_case_name, **kwargs):
        self.student_test_case_name = student_test_case_name

        self.compilation_return_code = kwargs.get(
            'compilation_return_code', None)
        self.compilation_standard_output = kwargs.get(
            'compilation_standard_output', None)
        self.compilation_standard_error_output = kwargs.get(
            'compilation_standard_error_output', None)
        self.valid = kwargs.get('valid', None)
        self.validity_check_standard_output = kwargs.get(
            'validity_check_standard_output', None)
        self.validity_check_standard_error_output = kwargs.get(
            'validity_check_standard_error_output', None)

        self.timed_out = kwargs.get('timed_out', None)

        self.buggy_implementations_exposed = kwargs.get(
            'buggy_implementations_exposed', [])

    @property
    def compilation_succeeded(self):
        return self.compilation_return_code == 0


class StudentTestSuiteResult(models.Model):
    """
    This class stores the result of evaluating a student test suite and
    provides an interface for serializing the data.

    Fields:
        test_suite -- The student test suite whose results this object holds.
            This field is REQUIRED.

        submission -- The submission the test suite was run for.
            This value can be None.

        buggy_implementations_exposed -- A list of the names of buggy
            implementations that were exposed by the student test suite.
            Default value: empty list

        detailed_results -- A list of StudentTestCaseEvaluationResult objects.

    Instance methods:
        to_json()
    """
    test_suite = models.ForeignKey(
        'StudentTestSuiteBase', related_name='results')

    submission = models.ForeignKey(
        Submission, null=True, blank=True, default=None)

    buggy_implementations_exposed = ag_fields.ClassField(set, default=set)

    # buggy_implementations_exposed = ag_fields.StringListField(
    #     strip_strings=False, default=[])

    detailed_results = pg_fields.ArrayField(
        ag_fields.ClassField(StudentTestCaseEvaluationResult),
        default=list, blank=True)
