from django.test import TestCase

from autograder.shared import feedback_configuration as fbc


class AutograderFeedbackConfigurationTestCase(TestCase):
    def setUp(self):
        self.maxDiff = None
        self.json_starter = {
            'visibility_level': 'show_to_students',
            'return_code_feedback_level': 'correct_or_incorrect_only',
            'output_feedback_level': 'correct_or_incorrect_only',
            'compilation_feedback_level': 'success_or_failure_only',
            'valgrind_feedback_level': 'errors_or_no_errors_only',
            'points_feedback_level': 'show_total',
        }

        self.medium_feedback = fbc.AutograderTestCaseFeedbackConfiguration(
            visibility_level=fbc.VisibilityLevel.show_to_students,
            compilation_feedback_level=(
                fbc.CompilationFeedbackLevel.success_or_failure_only),
            return_code_feedback_level=(
                fbc.ReturnCodeFeedbackLevel.correct_or_incorrect_only),
            output_feedback_level=(
                fbc.OutputFeedbackLevel.correct_or_incorrect_only),
            valgrind_feedback_level=(
                fbc.ValgrindFeedbackLevel.errors_or_no_errors_only),
            points_feedback_level=fbc.PointsFeedbackLevel.show_total
        )

    def test_valid_init_all_defaults(self):
        expected = fbc.AutograderTestCaseFeedbackConfiguration(
            visibility_level=fbc.VisibilityLevel.hide_from_students,
            compilation_feedback_level=(
                fbc.CompilationFeedbackLevel.no_feedback),
            return_code_feedback_level=fbc.ReturnCodeFeedbackLevel.no_feedback,
            output_feedback_level=fbc.OutputFeedbackLevel.no_feedback,
            valgrind_feedback_level=fbc.ValgrindFeedbackLevel.no_feedback,
            points_feedback_level=fbc.PointsFeedbackLevel.hide
        )

        default = fbc.AutograderTestCaseFeedbackConfiguration()

        self.assertEqual(expected, default)

    def test_valid_init_from_strings_no_defaults(self):
        expected = self.medium_feedback

        actual = fbc.AutograderTestCaseFeedbackConfiguration(
            **self.json_starter)

        self.assertEqual(expected, actual)

    def test_from_and_to_json(self):
        value = fbc.AutograderTestCaseFeedbackConfiguration.from_json(
            self.json_starter)
        self.assertEqual(self.medium_feedback, value)

        json = value.to_json()
        self.assertEqual(self.json_starter, json)

    def test_setter_type_errors(self):
        default = fbc.AutograderTestCaseFeedbackConfiguration()
        for member_name in self.json_starter:
            with self.assertRaises(ValueError):
                setattr(default, member_name, 'not a valid value')

            with self.assertRaises(ValueError):
                kwargs = {member_name: 'not a value'}
                fbc.AutograderTestCaseFeedbackConfiguration(**kwargs)

    def test_get_max_feedback(self):
        expected = fbc.AutograderTestCaseFeedbackConfiguration(
            visibility_level=fbc.VisibilityLevel.show_to_students,
            compilation_feedback_level=(
                fbc.CompilationFeedbackLevel.show_compiler_output),
            return_code_feedback_level=(
                fbc.ReturnCodeFeedbackLevel.show_expected_and_actual_values),
            output_feedback_level=(
                fbc.OutputFeedbackLevel.show_expected_and_actual_values),
            valgrind_feedback_level=(
                fbc.ValgrindFeedbackLevel.show_valgrind_output),
            points_feedback_level=fbc.PointsFeedbackLevel.show_breakdown
        )

        actual = fbc.AutograderTestCaseFeedbackConfiguration.get_max_feedback()

        self.assertEqual(expected, actual)

# -----------------------------------------------------------------------------


class StudentTestSuiteFeedbackConfigurationTestCase(TestCase):
    def setUp(self):
        self.json_starter = {
            'visibility_level': 'show_to_students',
            'student_test_validity_feedback_level': 'show_valid_or_invalid',
            'compilation_feedback_level': 'success_or_failure_only',
            'buggy_implementations_exposed_feedback_level': (
                'list_implementations_exposed_overall'),
            'points_feedback_level': 'show_total',
        }

        self.medium_feedback = fbc.StudentTestSuiteFeedbackConfiguration(
            visibility_level=fbc.VisibilityLevel.show_to_students,
            compilation_feedback_level=(
                fbc.CompilationFeedbackLevel.success_or_failure_only),
            student_test_validity_feedback_level=(
                fbc.StudentTestCaseValidityFeedbackLevel.show_valid_or_invalid),
            buggy_implementations_exposed_feedback_level=(
                (fbc.BuggyImplementationsExposedFeedbackLevel
                    .list_implementations_exposed_overall)),
            points_feedback_level=fbc.PointsFeedbackLevel.show_total
        )

    def test_valid_init_all_defaults(self):
        expected = fbc.StudentTestSuiteFeedbackConfiguration(
            visibility_level=fbc.VisibilityLevel.hide_from_students,
            compilation_feedback_level=(
                fbc.CompilationFeedbackLevel.no_feedback),
            student_test_validity_feedback_level=(
                fbc.StudentTestCaseValidityFeedbackLevel.no_feedback),
            buggy_implementations_exposed_feedback_level=(
                fbc.BuggyImplementationsExposedFeedbackLevel.no_feedback),
            points_feedback_level=fbc.PointsFeedbackLevel.hide
        )

        default = fbc.StudentTestSuiteFeedbackConfiguration()

        self.assertEqual(expected, default)

    def test_valid_init_from_strings_no_defaults(self):
        expected = self.medium_feedback

        actual = fbc.StudentTestSuiteFeedbackConfiguration(
            **self.json_starter)

        self.assertEqual(expected, actual)

    def test_from_and_to_json(self):
        value = fbc.StudentTestSuiteFeedbackConfiguration.from_json(
            self.json_starter)
        self.assertEqual(self.medium_feedback, value)

        json = value.to_json()
        self.assertEqual(self.json_starter, json)

    def test_setter_type_errors(self):
        default = fbc.StudentTestSuiteFeedbackConfiguration()
        for member_name in self.json_starter:
            with self.assertRaises(ValueError):
                setattr(default, member_name, 'not a valid value')

            with self.assertRaises(ValueError):
                kwargs = {member_name: 'not a value'}
                fbc.StudentTestSuiteFeedbackConfiguration(**kwargs)

    def test_get_max_feedback(self):
        expected = fbc.StudentTestSuiteFeedbackConfiguration(
            visibility_level=fbc.VisibilityLevel.show_to_students,
            compilation_feedback_level=(
                fbc.CompilationFeedbackLevel.show_compiler_output),
            student_test_validity_feedback_level=(
                (fbc.StudentTestCaseValidityFeedbackLevel.
                    show_validity_check_output)),
            buggy_implementations_exposed_feedback_level=(
                (fbc.BuggyImplementationsExposedFeedbackLevel.
                    list_implementations_exposed_per_test)),
            points_feedback_level=fbc.PointsFeedbackLevel.show_breakdown
        )

        actual = fbc.StudentTestSuiteFeedbackConfiguration.get_max_feedback()

        self.assertEqual(expected, actual)

