from enum import Enum

from autograder.utilities.json_serializable_interface import JsonSerializable


class AutograderTestCaseFeedbackConfiguration(JsonSerializable):
    """
    AutograderTestCaseFeedbackConfiguration objects specify how much
    feedback should be given about the results of an autograder
    test case.

    Member variables:
        visibility_level -- Determines whether students will
            be shown a given test case on their own submissions and
            whether semester staff and course admins will be shown
            that test case when viewing a student's submission.

        return_code_feedback_level
        output_feedback_level
        compilation_feedback_level
        valgrind_feedback_level
        points_feedback_level
    """
    def __init__(self, **kwargs):
        self.visibility_level = kwargs.get(
            'visibility_level',
            VisibilityLevel.hide_from_students)

        self.return_code_feedback_level = kwargs.get(
            'return_code_feedback_level',
            ReturnCodeFeedbackLevel.no_feedback)

        self.show_return_code = kwargs.get('show_return_code', False)

        self.standard_output_feedback_level = kwargs.get(
            'standard_output_feedback_level',
            StandardOutputFeedbackLevel.no_feedback)

        self.show_stdout_content = kwargs.get('show_stdout_content', False)

        self.standard_error_output_feedback_level = kwargs.get(
            'standard_error_output_feedback_level',
            StandardErrorOutputFeedbackLevel.no_feedback)

        self.show_stderr_content = kwargs.get('show_stderr_content', False)

        self.compilation_feedback_level = kwargs.get(
            'compilation_feedback_level',
            CompilationFeedbackLevel.no_feedback)

        self.valgrind_feedback_level = kwargs.get(
            'valgrind_feedback_level',
            ValgrindFeedbackLevel.no_feedback)

        self.points_feedback_level = kwargs.get(
            'points_feedback_level',
            PointsFeedbackLevel.hide)

    @classmethod
    def from_json(class_, json):
        return class_(**json)

    def to_json(self):
        return {
            'visibility_level': self.visibility_level.value,
            'return_code_feedback_level': (
                self.return_code_feedback_level.value),
            'output_feedback_level': self.output_feedback_level.value,
            'compilation_feedback_level': (
                self.compilation_feedback_level.value),
            'valgrind_feedback_level': self.valgrind_feedback_level.value,
            'points_feedback_level': self.points_feedback_level.value,
        }

    @classmethod
    def get_max_feedback(class_):
        return class_(
            visibility_level=VisibilityLevel.show_to_students,
            return_code_feedback_level=(
                ReturnCodeFeedbackLevel.show_expected_and_actual_values),
            standard_output_feedback_level=(
                StandardOutputFeedbackLevel.show_expected_and_actual_values),
            standard_error_output_feedback_level=(
                StandardErrorOutputFeedbackLevel.show_expected_and_actual_values),
            compilation_feedback_level=(
                CompilationFeedbackLevel.show_compiler_output),
            valgrind_feedback_level=(
                ValgrindFeedbackLevel.show_valgrind_output),
            points_feedback_level=(
                PointsFeedbackLevel.show_breakdown),
        )

    def __eq__(self, other):
        if not isinstance(other, AutograderTestCaseFeedbackConfiguration):
            return False

        return (
            (self.visibility_level ==
                other.visibility_level) and
            (self.return_code_feedback_level ==
                other.return_code_feedback_level) and
            self.output_feedback_level == other.output_feedback_level and
            (self.compilation_feedback_level ==
                other.compilation_feedback_level) and
            (self.valgrind_feedback_level ==
                other.valgrind_feedback_level) and
            self.points_feedback_level == other.points_feedback_level)

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def visibility_level(self):
        return self._visibility_level

    @visibility_level.setter
    def visibility_level(self, value):
        self._visibility_level = VisibilityLevel(value)

    @property
    def return_code_feedback_level(self):
        return self._return_code_feedback_level

    @return_code_feedback_level.setter
    def return_code_feedback_level(self, value):
        self._return_code_feedback_level = ReturnCodeFeedbackLevel(value)

    @property
    def standard_output_feedback_level(self):
        return self._standard_output_feedback_level

    @standard_output_feedback_level.setter
    def standard_output_feedback_level(self, value):
        self._standard_output_feedback_level = StandardOutputFeedbackLevel(
            value)

    @property
    def standard_error_output_feedback_level(self):
        return self._standard_error_output_feedback_level

    @standard_error_output_feedback_level.setter
    def standard_error_output_feedback_level(self, value):
        self._standard_error_output_feedback_level = (
            StandardErrorOutputFeedbackLevel(value))

    @property
    def compilation_feedback_level(self):
        return self._compilation_feedback_level

    @compilation_feedback_level.setter
    def compilation_feedback_level(self, value):
        self._compilation_feedback_level = CompilationFeedbackLevel(value)

    @property
    def valgrind_feedback_level(self):
        return self._valgrind_feedback_level

    @valgrind_feedback_level.setter
    def valgrind_feedback_level(self, value):
        self._valgrind_feedback_level = ValgrindFeedbackLevel(value)

    @property
    def points_feedback_level(self):
        return self._points_feedback_level

    @points_feedback_level.setter
    def points_feedback_level(self, value):
        self._points_feedback_level = PointsFeedbackLevel(value)


# -----------------------------------------------------------------------------


class StudentTestSuiteFeedbackConfiguration(JsonSerializable):
    """
    Objects of this class specify how much feedback should be given
    about the results of an evaluated student test suite.

    Member variables:
        visibility_level -- Determines whether students will
            be shown a given test suite on their own submissions and
            whether semester staff and course admins will be shown
            that suite when viewing a student's submission.

        compilation_feedback_level
        student_test_validity_feedback_level
        buggy_implementations_exposed_feedback_level
        points_feedback_level
    """
    def __init__(self, **kwargs):
        self.visibility_level = kwargs.get(
            'visibility_level',
            VisibilityLevel.hide_from_students)

        self.compilation_feedback_level = kwargs.get(
            'compilation_feedback_level', CompilationFeedbackLevel.no_feedback)

        self.student_test_validity_feedback_level = kwargs.get(
            'student_test_validity_feedback_level',
            StudentTestCaseValidityFeedbackLevel.no_feedback)

        self.buggy_implementations_exposed_feedback_level = kwargs.get(
            'buggy_implementations_exposed_feedback_level',
            BuggyImplementationsExposedFeedbackLevel.no_feedback)

        self.points_feedback_level = kwargs.get(
            'points_feedback_level', PointsFeedbackLevel.hide)

    def __eq__(self, other):
        if not isinstance(other, StudentTestSuiteFeedbackConfiguration):
            return False

        return (
            self.visibility_level == other.visibility_level and
            (self.compilation_feedback_level ==
                other.compilation_feedback_level) and
            (self.student_test_validity_feedback_level ==
                other.student_test_validity_feedback_level) and
            (self.buggy_implementations_exposed_feedback_level ==
                other.buggy_implementations_exposed_feedback_level) and
            self.points_feedback_level == other.points_feedback_level
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    @classmethod
    def from_json(class_, json):
        return class_(**json)

    def to_json(self):
        return {
            'visibility_level': self.visibility_level.value,
            'compilation_feedback_level': (
                self.compilation_feedback_level.value),
            'student_test_validity_feedback_level': (
                self.student_test_validity_feedback_level.value),
            'buggy_implementations_exposed_feedback_level': (
                self.buggy_implementations_exposed_feedback_level.value),
            'points_feedback_level': self.points_feedback_level.value
        }

    @classmethod
    def get_max_feedback(class_):
        return class_(
            visibility_level=(VisibilityLevel.show_to_students),
            compilation_feedback_level=(
                CompilationFeedbackLevel.show_compiler_output
            ),
            student_test_validity_feedback_level=(
                StudentTestCaseValidityFeedbackLevel.show_validity_check_output
            ),
            buggy_implementations_exposed_feedback_level=(
                (BuggyImplementationsExposedFeedbackLevel.
                    list_implementations_exposed_per_test)),
            points_feedback_level=PointsFeedbackLevel.show_breakdown
        )

    @property
    def visibility_level(self):
        return self._visibility_level

    @visibility_level.setter
    def visibility_level(self, value):
        self._visibility_level = VisibilityLevel(value)

    @property
    def compilation_feedback_level(self):
        return self._compilation_feedback_level

    @compilation_feedback_level.setter
    def compilation_feedback_level(self, value):
        self._compilation_feedback_level = CompilationFeedbackLevel(value)

    @property
    def student_test_validity_feedback_level(self):
        return self._student_test_validity_feedback_level

    @student_test_validity_feedback_level.setter
    def student_test_validity_feedback_level(self, value):
        self._student_test_validity_feedback_level = (
            StudentTestCaseValidityFeedbackLevel(value))

    @property
    def buggy_implementations_exposed_feedback_level(self):
        return self._buggy_implementations_exposed_feedback_level

    @buggy_implementations_exposed_feedback_level.setter
    def buggy_implementations_exposed_feedback_level(self, value):
        self._buggy_implementations_exposed_feedback_level = (
            BuggyImplementationsExposedFeedbackLevel(value))

    @property
    def points_feedback_level(self):
        return self._points_feedback_level

    @points_feedback_level.setter
    def points_feedback_level(self, value):
        self._points_feedback_level = PointsFeedbackLevel(value)

# -----------------------------------------------------------------------------


class VisibilityLevel(Enum):
    hide_from_students_and_staff_viewers = (
        'hide_from_students_and_staff_viewers')
    hide_from_students = 'hide_from_students'
    show_to_students = 'show_to_students'


class CompilationFeedbackLevel(Enum):
    no_feedback = 'no_feedback'
    success_or_failure_only = 'success_or_failure_only'
    show_compiler_output = 'show_compiler_output'


# TODO
# class ProgramTimeoutFeedbackLevel(Enum):
#     pass


class ReturnCodeFeedbackLevel(Enum):
    no_feedback = 'no_feedback'
    correct_or_incorrect_only = 'correct_or_incorrect_only'
    show_expected_and_actual_values = 'show_expected_and_actual_values'


class StandardOutputFeedbackLevel(Enum):
    no_feedback = 'no_feedback'
    correct_or_incorrect_only = 'correct_or_incorrect_only'
    show_expected_and_actual_values = 'show_expected_and_actual_values'


class StandardErrorOutputFeedbackLevel(Enum):
    no_feedback = 'no_feedback'
    correct_or_incorrect_only = 'correct_or_incorrect_only'
    show_expected_and_actual_values = 'show_expected_and_actual_values'


class ValgrindFeedbackLevel(Enum):
    no_feedback = 'no_feedback'
    errors_or_no_errors_only = 'errors_or_no_errors_only'
    show_valgrind_output = 'show_valgrind_output'


class PointsFeedbackLevel(Enum):
    hide = 'hide'
    # Note: When "show_total" or "show_breakdown" is chosen,
    # it will only show the
    # points from parts of the test case or suite that the
    # student receives feedback on.
    show_total = 'show_total'
    show_breakdown = 'show_breakdown'


class StudentTestCaseValidityFeedbackLevel(Enum):
    no_feedback = 'no_feedback'
    show_valid_or_invalid = 'show_valid_or_invalid'
    show_validity_check_output = 'show_validity_check_output'


class BuggyImplementationsExposedFeedbackLevel(Enum):
    no_feedback = 'no_feedback'
    list_implementations_exposed_overall = (
        'list_implementations_exposed_overall')
    list_implementations_exposed_per_test = (
        'list_implementations_exposed_per_test')
