from django.db import models
import django.contrib.postgres.fields as pg_fields

from autograder.core.models import Submission
import autograder.utilities.fields as ag_fields

from autograder.core.shared.feedback_configuration import (
    StudentTestCaseValidityFeedbackLevel,
    BuggyImplementationsExposedFeedbackLevel,
    CompilationFeedbackLevel,
    PointsFeedbackLevel)


# TODO: document
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
            (self.compilation_standard_output ==
                other.compilation_standard_output) and
            (self.compilation_standard_error_output ==
                other.compilation_standard_error_output) and
            self.valid == other.valid and
            (self.validity_check_standard_output ==
                other.validity_check_standard_output) and
            (self.validity_check_standard_error_output ==
                other.validity_check_standard_error_output) and
            self.timed_out == other.timed_out and
            (self.buggy_implementations_exposed ==
                other.buggy_implementations_exposed)
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

    def to_json(self, feedback_config_override=None):
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

                student_test_case_name: <name>,

                compilation_succeeded: <true|false>,
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
        feedback_config = (
            feedback_config_override if feedback_config_override is not None
            else self.test_suite.feedback_configuration)

        result = {
            'test_suite_name': self.test_suite.name,
        }

        if (feedback_config.buggy_implementations_exposed_feedback_level !=
                BuggyImplementationsExposedFeedbackLevel.no_feedback):
            result['buggy_implementations_exposed'] = list(
                sorted(self.buggy_implementations_exposed))

        result['detailed_results'] = self._compute_detailed_results(
            feedback_config)

        result.update(self._compute_points_feedback(
            points_feedback_level=feedback_config.points_feedback_level,
            buggy_impls_feedback_level=(
                feedback_config.buggy_implementations_exposed_feedback_level)))

        return result

    def _compute_detailed_results(self, feedback_config):
        detailed_results = []
        for test_case_result in self.detailed_results:
            details = {
                'student_test_case_name': (
                    test_case_result.student_test_case_name)
            }
            details.update(
                self._compute_compilation_feedback(
                    test_case_result,
                    feedback_config.compilation_feedback_level))

            details.update(
                self._compute_validity_feedback(
                    test_case_result,
                    feedback_config.student_test_validity_feedback_level))

            if (feedback_config.buggy_implementations_exposed_feedback_level ==
                    (BuggyImplementationsExposedFeedbackLevel
                        .list_implementations_exposed_per_test)):
                details['buggy_implementations_exposed'] = (
                    list(sorted(
                        test_case_result.buggy_implementations_exposed)))

            detailed_results.append(details)

        return detailed_results

    def _compute_compilation_feedback(self, test_result, feedback_level):
        if feedback_level == CompilationFeedbackLevel.no_feedback:
            return {}

        feedback = {
            'compilation_succeeded': test_result.compilation_succeeded
        }

        if feedback_level == CompilationFeedbackLevel.show_compiler_output:
            feedback['compilation_standard_output'] = (
                test_result.compilation_standard_output)
            feedback['compilation_standard_error_output'] = (
                test_result.compilation_standard_error_output)

        return feedback

    def _compute_validity_feedback(self, test_result, feedback_level):
        if feedback_level == StudentTestCaseValidityFeedbackLevel.no_feedback:
            return {}

        feedback = {
            'valid': test_result.valid,
            'timed_out': test_result.timed_out
        }

        if (feedback_level ==
                (StudentTestCaseValidityFeedbackLevel
                    .show_validity_check_output)):
            feedback['validity_check_standard_output'] = (
                test_result.validity_check_standard_output)
            feedback['validity_check_standard_error_output'] = (
                test_result.validity_check_standard_error_output)

        return feedback

    def _compute_points_feedback(self, points_feedback_level,
                                 buggy_impls_feedback_level):
        if points_feedback_level == PointsFeedbackLevel.hide:
            return {}

        if (buggy_impls_feedback_level ==
                BuggyImplementationsExposedFeedbackLevel.no_feedback):
            return {}

        points_per_buggy = (
            self.test_suite.points_per_buggy_implementation_exposed)
        return {
            'points_possible': (
                points_per_buggy *
                len(self.test_suite.buggy_implementation_filenames)),
            'points_awarded': points_per_buggy * len(
                self.buggy_implementations_exposed)
        }
