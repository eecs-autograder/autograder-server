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

    def __eq__(self, other):
        if not isinstance(other, StudentTestCaseEvaluationResult):
            return False

        return (
            self.student_test_case_name == other.student_test_case_name and
            self.compilation_return_code == other.compilation_return_code and
            self.compilation_standard_output == other.compilation_standard_output and
            self.compilation_standard_error_output == other.compilation_standard_error_output and
            self.valid == other.valid and
            self.validity_check_standard_output == other.validity_check_standard_output and
            self.validity_check_standard_error_output == other.validity_check_standard_error_output and
            self.timed_out == other.timed_out and
            self.buggy_implementations_exposed == other.buggy_implementations_exposed
        )

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
            Default value: None

        buggy_implementations_exposed -- A list of the names of buggy
            implementations that were exposed by the student test suite.
            Default value: empty list

        detailed_results -- A list of StudentTestCaseEvaluationResult objects.
            This field can be empty but may NOT be None.
            Default value: empty list

    Static methods:
        new_test_evaluation_result_instance()

    Instance methods:
        to_json()
    """
    test_suite = models.ForeignKey(
        'StudentTestSuiteBase')

    submission = models.ForeignKey(
        Submission, null=True, blank=True, default=None,
        related_name='suite_results')

    buggy_implementations_exposed = ag_fields.ClassField(set, default=set)

    detailed_results = ag_fields.ClassField(
        list, blank=True, default=list)

    @staticmethod
    def new_test_evaluation_result_instance(student_test_case_name, **kwargs):
        return StudentTestCaseEvaluationResult(
            student_test_case_name, **kwargs)

    def to_json(self, feedack_config_override=None):
        """
        Returns a JSON representation of this test suite result of the
        following form:

        test_suite_name: <name>,

        //** NOTE: Some or all of the following may be ommitted **//
        //** depending on the feedback level.                   **//

        buggy_implementations_exposed: [
            <implementation filename>,
            ...
        ],

        detailed_results: [
            {
                //** NOTE: Some of the following may be ommitted **//
                //** depending on the feedback level.            **//

                student_test_name: <name>,

                compilation_return_code: <value>,
                compilation_standard_output: <value>,
                compilation_standard_error_output: <value>,

                valid: <true|false>,
                validity_check_standard_output: <value>,
                validity_check_standard_error_output: <value>,

                timed_out: <true|false>,

                buggy_implementations_exposed: [
                    <implementation filename>,
                    ...
                ]
            },
            ...
        ]
        """
        pass
