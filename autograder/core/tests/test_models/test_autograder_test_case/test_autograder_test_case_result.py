import difflib

from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut

from autograder.core.models import (
    Project, Semester, Course, AutograderTestCaseBase,
    CompiledAutograderTestCase, AutograderTestCaseResult,
    SubmissionGroup, Submission)

import autograder.core.shared.feedback_configuration as fbc

_DIFFER = difflib.Differ()


class _SetUpBase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = obj_ut.create_dummy_courses()
        self.semester = obj_ut.create_dummy_semesters(self.course)

        self.project = Project.objects.validate_and_create(
            name='my_project', semester=self.semester,
            required_student_files=['file1.cpp', 'file2.cpp'],
            expected_student_file_patterns=[
                Project.FilePatternTuple('test_*.cpp', 1, 2)])

        self.project.add_project_file(
            SimpleUploadedFile('spam.txt', b'hello there!'))

        self.test_name = 'my_test'

        self.test_case = AutograderTestCaseBase.objects.validate_and_create(
            name=self.test_name, project=self.project)


class AutograderTestCaseResultTestCase(_SetUpBase):
    def test_default_init(self):
        result = AutograderTestCaseResult.objects.create(
            test_case=self.test_case)

        loaded_result = AutograderTestCaseResult.objects.filter(
            test_case=self.test_case)[0]

        self.assertEqual(result, loaded_result)

        self.assertEqual(loaded_result.test_case, self.test_case)
        self.assertIsNone(loaded_result.return_code)
        self.assertEqual(loaded_result.standard_output, '')
        self.assertEqual(loaded_result.standard_error_output, '')
        self.assertFalse(loaded_result.timed_out)
        # self.assertIsNone(loaded_result.time_elapsed)
        self.assertIsNone(loaded_result.valgrind_return_code)
        self.assertEqual(loaded_result.valgrind_output, '')
        self.assertIsNone(loaded_result.compilation_return_code)
        self.assertEqual(loaded_result.compilation_standard_output, '')
        self.assertEqual(loaded_result.compilation_standard_error_output, '')


class ResultOutputCorrectTestCase(_SetUpBase):
    def setUp(self):
        super().setUp()

        self.correct_stdout = 'correct_stdout'
        self.correct_stderr = 'correct stderr'

        self.result = AutograderTestCaseResult(
            test_case=self.test_case
        )

    def _init_expected_output(self):
        self.test_case.expected_standard_output = self.correct_stdout
        self.test_case.expected_standard_error_output = self.correct_stderr

        self.test_case.validate_and_save()

    def test_stdout_right_stderr_right(self):
        self._init_expected_output()

        self.result.standard_output = self.correct_stdout
        self.result.standard_error_output = self.correct_stderr

        self.assertTrue(self.result.standard_output_correct)
        self.assertTrue(self.result.standard_error_output_correct)
        self.assertTrue(self.result.output_correct)

    def test_stdout_right_stderr_wrong(self):
        self._init_expected_output()

        self.result.standard_output = self.correct_stdout
        self.result.standard_error_output = 'wrong'

        self.assertTrue(self.result.standard_output_correct)
        self.assertFalse(self.result.standard_error_output_correct)
        self.assertFalse(self.result.output_correct)

    def test_stdout_wrong_stderr_right(self):
        self._init_expected_output()

        self.result.standard_output = 'wrong'
        self.result.standard_error_output = self.correct_stderr

        self.assertFalse(self.result.standard_output_correct)
        self.assertTrue(self.result.standard_error_output_correct)
        self.assertFalse(self.result.output_correct)

    def test_stdout_wrong_stderr_wrong(self):
        self._init_expected_output()

        self.result.standard_output = 'wrong'
        self.result.standard_error_output = 'wrong'

        self.assertFalse(self.result.standard_output_correct)
        self.assertFalse(self.result.standard_error_output_correct)
        self.assertFalse(self.result.output_correct)

    def test_stdout_right_no_stderr(self):
        self.test_case.expected_standard_output = self.correct_stdout
        self.test_case.validate_and_save()

        self.result.standard_output = self.correct_stdout
        self.result.standard_error_output = "won't be checked"

        self.assertTrue(self.result.standard_output_correct)
        self.assertTrue(self.result.standard_error_output_correct)
        self.assertTrue(self.result.output_correct)

    def test_stdout_wrong_no_stderr(self):
        self.test_case.expected_standard_output = self.correct_stdout
        self.test_case.validate_and_save()

        self.result.standard_output = 'wrong'
        self.result.standard_error_output = "won't be checked"

        self.assertFalse(self.result.standard_output_correct)
        self.assertTrue(self.result.standard_error_output_correct)
        self.assertFalse(self.result.output_correct)

    def test_no_stdout_stderr_right(self):
        self.test_case.expected_standard_error_output = self.correct_stderr
        self.test_case.validate_and_save()

        self.result.standard_output = "won't be checked"
        self.result.standard_error_output = self.correct_stderr

        self.assertTrue(self.result.standard_output_correct)
        self.assertTrue(self.result.standard_error_output_correct)
        self.assertTrue(self.result.output_correct)

    def test_no_stdout_stderr_wrong(self):
        self.test_case.expected_standard_error_output = self.correct_stderr
        self.test_case.validate_and_save()

        self.result.standard_output = "won't be checked"
        self.result.standard_error_output = 'wrong'

        self.assertTrue(self.result.standard_output_correct)
        self.assertFalse(self.result.standard_error_output_correct)
        self.assertFalse(self.result.output_correct)

# -----------------------------------------------------------------------------


class CompiledAutograderTestCaseResultSerializerTestCase(
        TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None

        self.course = Course.objects.validate_and_create(name='eecs280')
        self.semester = Semester.objects.validate_and_create(
            name='f15', course=self.course)

        self.project = Project.objects.validate_and_create(
            name='my_project', semester=self.semester,
            required_student_files=['spam.cpp', 'egg.cpp'])

        self.test_case = CompiledAutograderTestCase.objects.validate_and_create(
            name='test',
            project=self.project,
            expected_return_code=0,
            expected_standard_output='stdout\nspam\n',
            expected_standard_error_output='stderr\negg\n',
            use_valgrind=True,
            valgrind_flags=['--leak-check=full', '--error-exitcode=42'],
            compiler='g++',
            compiler_flags=['-Wall'],
            student_resource_files=['spam.cpp', 'egg.cpp'],
            files_to_compile_together=['spam.cpp', 'egg.cpp'],
            executable_name='prog',
            points_for_correct_return_code=1,
            points_for_correct_output=2,
            deduction_for_valgrind_errors=2,
            points_for_compilation_success=4)

        self.correct_test_result = AutograderTestCaseResult.objects.create(
            test_case=self.test_case,
            return_code=0,
            standard_output='stdout\nspam\n',
            standard_error_output='stderr\negg\n',
            timed_out=False,
            valgrind_return_code=0,
            valgrind_output='clean',
            compilation_return_code=0,
            compilation_standard_output='win',
            compilation_standard_error_output='')

        self.compile_fail_test_result = AutograderTestCaseResult.objects.create(
            test_case=self.test_case,
            compilation_return_code=42,
            compilation_standard_output='',
            compilation_standard_error_output='lose')

        self.incorrect_test_result = AutograderTestCaseResult.objects.create(
            test_case=self.test_case,
            return_code=42,
            standard_output='wrong',
            standard_error_output='wrong',
            timed_out=False,
            valgrind_return_code=42,
            valgrind_output='error',
            compilation_return_code=0,
            compilation_standard_output='hello',
            compilation_standard_error_output='woah')

        self.valgrind_error_result = AutograderTestCaseResult.objects.create(
            test_case=self.test_case,
            return_code=0,
            standard_output='stdout\nspam\n',
            standard_error_output='stderr\negg\n',
            timed_out=False,
            valgrind_return_code=42,
            valgrind_output='error',
            compilation_return_code=0,
            compilation_standard_output='win',
            compilation_standard_error_output='')

        self.timed_out_result = AutograderTestCaseResult.objects.create(
            test_case=self.test_case,
            return_code=0,
            standard_output='stdout\nspam\n',
            standard_error_output='stderr\negg\n',
            timed_out=True,
            valgrind_return_code=0,
            valgrind_output='clean',
            compilation_return_code=0,
            compilation_standard_output='win',
            compilation_standard_error_output='')

        student = obj_ut.create_dummy_users()
        self.semester.add_enrolled_students(student)
        self.submission_group = SubmissionGroup.objects.validate_and_create(
            members=[student.username], project=self.project)

        self.submission = Submission.objects.validate_and_create(
            submission_group=self.submission_group,
            submitted_files=[
                SimpleUploadedFile('spam.cpp', b'spaaaaam'),
                SimpleUploadedFile('egg.cpp', b'egg')]
        )

        self.medium_config = fbc.AutograderTestCaseFeedbackConfiguration(
            return_code_feedback_level=(
                fbc.ReturnCodeFeedbackLevel.correct_or_incorrect_only),
            output_feedback_level=(
                fbc.OutputFeedbackLevel.correct_or_incorrect_only),
            compilation_feedback_level=(
                fbc.CompilationFeedbackLevel.success_or_failure_only),
            valgrind_feedback_level=(
                fbc.ValgrindFeedbackLevel.errors_or_no_errors_only),
            points_feedback_level=fbc.PointsFeedbackLevel.show_total
        )

    def test_serialize_results_low_feedback(self):
        self.assertEqual(
            {
                'test_name': self.test_case.name,
                'timed_out': False
            },
            self.correct_test_result.to_json())

        self.assertEqual(
            {
                'test_name': self.test_case.name,
                'timed_out': False
            },
            self.incorrect_test_result.to_json())

        self.assertEqual(
            {
                'test_name': self.test_case.name,
                'timed_out': False
            },
            self.valgrind_error_result.to_json())

        self.assertEqual(
            {
                'test_name': self.test_case.name,
                'timed_out': True
            },
            self.timed_out_result.to_json())

    def test_serialize_results_medium_feedback(self):
        self.test_case.feedback_configuration = self.medium_config
        self.test_case.save()

        expected_correct = {
            'test_name': self.test_case.name,
            'return_code_correct': True,
            'output_correct': True,
            'valgrind_errors_present': False,
            'compilation_succeeded': True,
            'total_points_awarded': 7,
            'total_points_possible': 7,

            'timed_out': False
        }

        expected_incorrect = {
            'test_name': self.test_case.name,
            'return_code_correct': False,
            'output_correct': False,
            'valgrind_errors_present': True,
            'compilation_succeeded': True,
            # deduction for valgrind errors only subtracts from output
            # and return code points awarded
            'total_points_awarded': 4,
            'total_points_possible': 7,

            'timed_out': False
        }

        expected_valgrind_errors = {
            'test_name': self.test_case.name,
            'return_code_correct': True,
            'output_correct': True,
            'valgrind_errors_present': True,
            'compilation_succeeded': True,
            # deduction for valgrind errors only subtracts from output
            # and return code points awarded
            'total_points_awarded': 5,
            'total_points_possible': 7,

            'timed_out': False
        }

        self.assertEqual(
            expected_correct,
            self.correct_test_result.to_json())

        self.assertEqual(
            expected_incorrect,
            self.incorrect_test_result.to_json())

        self.assertEqual(
            expected_valgrind_errors,
            self.valgrind_error_result.to_json())

        self.assertEqual(
            {
                'test_name': self.test_case.name,
                'timed_out': True,
                'compilation_succeeded': True,
                'total_points_awarded': 4,
                'total_points_possible': 7
            },
            self.timed_out_result.to_json())

    def test_serialize_results_high_feedback(self):
        self.test_case.feedback_configuration = (
            fbc.AutograderTestCaseFeedbackConfiguration.get_max_feedback())
        self.test_case.save()

        expected_correct = {
            'test_name': self.test_case.name,
            'return_code_correct': True,
            'expected_return_code': 0,
            'actual_return_code': 0,


            'output_correct': True,
            'stdout_diff': list(_DIFFER.compare(
                self.test_case.expected_standard_output.splitlines(
                    keepends=True),
                self.correct_test_result.standard_output.splitlines(
                    keepends=True))),
            'stderr_diff': list(_DIFFER.compare(
                self.test_case.expected_standard_error_output.splitlines(
                    keepends=True),
                self.correct_test_result.standard_error_output.splitlines(
                    keepends=True))),


            'valgrind_errors_present': False,
            'valgrind_output': 'clean',


            'compilation_succeeded': True,
            'compilation_stdout': 'win',
            'compilation_stderr': '',


            'return_code_points_awarded': 1,
            'return_code_points_possible': 1,
            'output_points_awarded': 2,
            'output_points_possible': 2,
            'valgrind_points_deducted': 0,
            'compilation_points_awarded': 4,
            'compilation_points_possible': 4,

            'total_points_awarded': 7,
            'total_points_possible': 7,


            'timed_out': False
        }

        actual = self.correct_test_result.to_json()
        self.assertEqual(expected_correct, actual)

        expected_compile_fail = {
            'test_name': self.test_case.name,
            'compilation_succeeded': False,
            'compilation_stdout': '',
            'compilation_stderr': 'lose',

            'compilation_points_awarded': 0,
            'compilation_points_possible': 4,

            'return_code_points_awarded': 0,
            'return_code_points_possible': 1,

            'output_points_awarded': 0,
            'output_points_possible': 2,

            'valgrind_points_deducted': 0,

            'total_points_awarded': 0,
            'total_points_possible': 7
        }

        self.assertEqual(
            expected_compile_fail,
            self.compile_fail_test_result.to_json())

        expected_incorrect = {
            'test_name': self.test_case.name,
            'return_code_correct': False,
            'expected_return_code': 0,
            'actual_return_code': 42,


            'output_correct': False,
            'stdout_diff': list(_DIFFER.compare(
                self.test_case.expected_standard_output.splitlines(
                    keepends=True),
                self.incorrect_test_result.standard_output.splitlines(
                    keepends=True))),
            'stderr_diff': list(_DIFFER.compare(
                self.test_case.expected_standard_error_output.splitlines(
                    keepends=True),
                self.incorrect_test_result.standard_error_output.splitlines(
                    keepends=True))),


            'valgrind_errors_present': True,
            'valgrind_output': 'error',


            'compilation_succeeded': True,
            'compilation_stdout': 'hello',
            'compilation_stderr': 'woah',


            'return_code_points_awarded': 0,
            'return_code_points_possible': 1,
            'output_points_awarded': 0,
            'output_points_possible': 2,
            'valgrind_points_deducted': 2,
            'compilation_points_awarded': 4,
            'compilation_points_possible': 4,

            'total_points_awarded': 4,
            'total_points_possible': 7,


            'timed_out': False
        }

        self.assertEqual(
            expected_incorrect, self.incorrect_test_result.to_json())

        expected_valgrind_errors = {
            'test_name': self.test_case.name,
            'return_code_correct': True,
            'expected_return_code': 0,
            'actual_return_code': 0,


            'output_correct': True,
            'stdout_diff': list(_DIFFER.compare(
                self.test_case.expected_standard_output.splitlines(
                    keepends=True),
                self.correct_test_result.standard_output.splitlines(
                    keepends=True))),
            'stderr_diff': list(_DIFFER.compare(
                self.test_case.expected_standard_error_output.splitlines(
                    keepends=True),
                self.correct_test_result.standard_error_output.splitlines(
                    keepends=True))),


            'valgrind_errors_present': True,
            'valgrind_output': 'error',


            'compilation_succeeded': True,
            'compilation_stdout': 'win',
            'compilation_stderr': '',


            'return_code_points_awarded': 1,
            'return_code_points_possible': 1,
            'output_points_awarded': 2,
            'output_points_possible': 2,
            'valgrind_points_deducted': 2,
            'compilation_points_awarded': 4,
            'compilation_points_possible': 4,

            'total_points_awarded': 5,
            'total_points_possible': 7,


            'timed_out': False
        }

        self.assertEqual(
            expected_valgrind_errors, self.valgrind_error_result.to_json())

        expected_timeout = {
            'test_name': self.test_case.name,
            'compilation_succeeded': True,
            'compilation_stdout': 'win',
            'compilation_stderr': '',

            'compilation_points_awarded': 4,
            'compilation_points_possible': 4,

            'return_code_points_awarded': 0,
            'return_code_points_possible': 1,

            'output_points_awarded': 0,
            'output_points_possible': 2,

            'valgrind_points_deducted': 0,

            'total_points_awarded': 4,
            'total_points_possible': 7,

            'timed_out': True
        }
        actual = self.timed_out_result.to_json()
        self.assertEqual(expected_timeout, actual)

    def test_serialize_results_with_submission_no_feedback_override(self):
        self.correct_test_result.submission = self.submission
        self.assertEqual(
            {
                'test_name': self.test_case.name,
                'timed_out': False
            },
            self.correct_test_result.to_json())

    # OBSOLETE
    # def test_serialize_results_with_submission_feedback_override(self):
    #     override = fbc.AutograderTestCaseFeedbackConfiguration(
    #         return_code_feedback_level=(
    #             fbc.ReturnCodeFeedbackLevel.correct_or_incorrect_only))

    #     self.submission.test_case_feedback_config_override = override
    #     self.submission.save()

    #     self.correct_test_result.submission = self.submission
    #     self.correct_test_result.save()

    #     self.assertEqual(
    #         {
    #             'test_name': self.test_case.name,
    #             'timed_out': False,
    #             'return_code_correct': True
    #         },
    #         self.correct_test_result.to_json())

    def test_serialize_results_with_manual_feedback_override(self):
        override = fbc.AutograderTestCaseFeedbackConfiguration(
            return_code_feedback_level=(
                fbc.ReturnCodeFeedbackLevel.correct_or_incorrect_only))

        self.assertEqual(
            {
                'test_name': self.test_case.name,
                'timed_out': False,
                'return_code_correct': True
            },
            self.correct_test_result.to_json(override_feedback=override))

    # OBSOLETE
    # def test_serialize_results_with_submission_and_manual_feedback_override(self):
    #     submission_override = fbc.AutograderTestCaseFeedbackConfiguration(
    #         return_code_feedback_level=(
    #             fbc.ReturnCodeFeedbackLevel.correct_or_incorrect_only))

    #     self.submission.test_case_feedback_config_override = submission_override
    #     self.submission.save()

    #     self.correct_test_result.submission = self.submission
    #     self.correct_test_result.save()

    #     manual_override = fbc.AutograderTestCaseFeedbackConfiguration(
    #         return_code_feedback_level=(
    #             fbc.ReturnCodeFeedbackLevel.correct_or_incorrect_only))

    #     self.assertEqual(
    #         {
    #             'test_name': self.test_case.name,
    #             'timed_out': False,
    #             'return_code_correct': True
    #         },
    #         self.correct_test_result.to_json(
    #             override_feedback=manual_override))

    def test_checking_output_with_show_output_feedback_level(self):
        feedback = self.medium_config
        feedback.output_feedback_level = (
            fbc.OutputFeedbackLevel.show_program_output)

        expected = {
            'test_name': self.test_case.name,
            'return_code_correct': True,
            'output_correct': True,
            'standard_output': (
                self.correct_test_result.standard_output),
            'standard_error_output': (
                self.correct_test_result.standard_error_output),
            'valgrind_errors_present': False,
            'compilation_succeeded': True,
            'total_points_awarded': 7,
            'total_points_possible': 7,

            'timed_out': False
        }

        self.assertEqual(
            expected,
            self.correct_test_result.to_json(override_feedback=feedback))

    def test_not_checking_output_but_show_output_set(self):
        self.test_case.expected_standard_output = ''
        self.test_case.expected_standard_error_output = ''

        feedback = self.medium_config
        feedback.output_feedback_level = (
            fbc.OutputFeedbackLevel.show_program_output)

        expected = {
            'test_name': self.test_case.name,
            'return_code_correct': True,
            'standard_output': (
                self.correct_test_result.standard_output),
            'standard_error_output': (
                self.correct_test_result.standard_error_output),
            'valgrind_errors_present': False,
            'compilation_succeeded': True,
            'total_points_awarded': 5,
            'total_points_possible': 5,

            'timed_out': False
        }

        self.assertEqual(
            expected,
            self.correct_test_result.to_json(override_feedback=feedback))

    def test_mixed_feedback_points_breakdown(self):
        feedback = self.medium_config
        feedback.points_feedback_level = fbc.PointsFeedbackLevel.show_breakdown
        expected = {
            'test_name': self.test_case.name,
            'return_code_correct': True,
            'output_correct': True,
            'valgrind_errors_present': False,
            'compilation_succeeded': True,

            'return_code_points_awarded': 1,
            'return_code_points_possible': 1,
            'output_points_awarded': 2,
            'output_points_possible': 2,
            'valgrind_points_deducted': 0,
            'compilation_points_awarded': 4,
            'compilation_points_possible': 4,

            'total_points_awarded': 7,
            'total_points_possible': 7,

            'timed_out': False
        }
        self.assertEqual(expected, self.correct_test_result.to_json(feedback))

        feedback.return_code_feedback_level = (
            fbc.ReturnCodeFeedbackLevel.no_feedback)
        expected = {
            'test_name': self.test_case.name,
            'output_correct': True,
            'valgrind_errors_present': False,
            'compilation_succeeded': True,

            'output_points_awarded': 2,
            'output_points_possible': 2,
            'valgrind_points_deducted': 0,
            'compilation_points_awarded': 4,
            'compilation_points_possible': 4,

            'total_points_awarded': 6,
            'total_points_possible': 6,

            'timed_out': False
        }
        self.assertEqual(expected, self.correct_test_result.to_json(feedback))

        feedback.valgrind_feedback_level = (
            fbc.ValgrindFeedbackLevel.no_feedback)
        expected = {
            'test_name': self.test_case.name,
            'output_correct': True,
            'compilation_succeeded': True,

            'output_points_awarded': 2,
            'output_points_possible': 2,
            'compilation_points_awarded': 4,
            'compilation_points_possible': 4,

            'total_points_awarded': 6,
            'total_points_possible': 6,

            'timed_out': False
        }
        self.assertEqual(
            expected, self.valgrind_error_result.to_json(feedback))

        feedback.compilation_feedback_level = (
            fbc.CompilationFeedbackLevel.no_feedback)
        expected = {
            'test_name': self.test_case.name,
            'output_correct': True,

            'output_points_awarded': 2,
            'output_points_possible': 2,

            'total_points_awarded': 2,
            'total_points_possible': 2,

            'timed_out': False
        }
        self.assertEqual(
            expected, self.valgrind_error_result.to_json(feedback))

        feedback.output_feedback_level = (
            fbc.OutputFeedbackLevel.no_feedback)
        feedback.return_code_feedback_level = (
            fbc.ReturnCodeFeedbackLevel.correct_or_incorrect_only)
        expected = {
            'test_name': self.test_case.name,
            'return_code_correct': True,

            'return_code_points_awarded': 1,
            'return_code_points_possible': 1,

            'total_points_awarded': 1,
            'total_points_possible': 1,

            'timed_out': False
        }
        self.assertEqual(
            expected, self.valgrind_error_result.to_json(feedback))

    def test_not_checking_return_code(self):
        self.test_case.expected_return_code = None
        self.test_case.validate_and_save()

        expected_medium = {
            'test_name': self.test_case.name,
            'output_correct': True,
            'valgrind_errors_present': False,
            'compilation_succeeded': True,
            'total_points_awarded': 6,
            'total_points_possible': 6,

            'timed_out': False
        }

        self.assertEqual(
            expected_medium,
            self.correct_test_result.to_json(self.medium_config))

        expected_high = {
            'test_name': self.test_case.name,

            'output_correct': True,
            'stdout_diff': list(_DIFFER.compare(
                self.test_case.expected_standard_output.splitlines(
                    keepends=True),
                self.correct_test_result.standard_output.splitlines(
                    keepends=True))),
            'stderr_diff': list(_DIFFER.compare(
                self.test_case.expected_standard_error_output.splitlines(
                    keepends=True),
                self.correct_test_result.standard_error_output.splitlines(
                    keepends=True))),

            'valgrind_errors_present': False,
            'valgrind_output': 'clean',

            'compilation_succeeded': True,
            'compilation_stdout': 'win',
            'compilation_stderr': '',

            'output_points_awarded': 2,
            'output_points_possible': 2,
            'valgrind_points_deducted': 0,
            'compilation_points_awarded': 4,
            'compilation_points_possible': 4,

            'total_points_awarded': 6,
            'total_points_possible': 6,

            'timed_out': False
        }

        self.assertEqual(expected_high, self.correct_test_result.to_json(
            fbc.AutograderTestCaseFeedbackConfiguration.get_max_feedback()))

    def test_not_checking_output(self):
        self.test_case.expected_standard_output = ''
        self.test_case.expected_standard_error_output = ''
        self.test_case.validate_and_save()

        expected_medium = {
            'test_name': self.test_case.name,
            'return_code_correct': True,
            'valgrind_errors_present': False,
            'compilation_succeeded': True,
            'total_points_awarded': 5,
            'total_points_possible': 5,

            'timed_out': False
        }

        self.assertEqual(
            expected_medium,
            self.correct_test_result.to_json(self.medium_config))

        expected_high = {
            'test_name': self.test_case.name,
            'return_code_correct': True,
            'expected_return_code': 0,
            'actual_return_code': 0,

            'valgrind_errors_present': False,
            'valgrind_output': 'clean',

            'compilation_succeeded': True,
            'compilation_stdout': 'win',
            'compilation_stderr': '',

            'return_code_points_awarded': 1,
            'return_code_points_possible': 1,
            'valgrind_points_deducted': 0,
            'compilation_points_awarded': 4,
            'compilation_points_possible': 4,

            'total_points_awarded': 5,
            'total_points_possible': 5,

            'timed_out': False
        }

        self.assertEqual(expected_high, self.correct_test_result.to_json(
            fbc.AutograderTestCaseFeedbackConfiguration.get_max_feedback()))

    def test_not_using_valgrind(self):
        self.test_case.use_valgrind = False
        self.test_case.validate_and_save()

        expected_medium = {
            'test_name': self.test_case.name,
            'return_code_correct': True,
            'output_correct': True,
            'compilation_succeeded': True,
            'total_points_awarded': 7,
            'total_points_possible': 7,

            'timed_out': False
        }

        self.assertEqual(
            expected_medium,
            self.valgrind_error_result.to_json(self.medium_config))

        expected_high = {
            'test_name': self.test_case.name,
            'return_code_correct': True,
            'expected_return_code': 0,
            'actual_return_code': 0,


            'output_correct': True,
            'stdout_diff': list(_DIFFER.compare(
                self.test_case.expected_standard_output.splitlines(
                    keepends=True),
                self.correct_test_result.standard_output.splitlines(
                    keepends=True))),
            'stderr_diff': list(_DIFFER.compare(
                self.test_case.expected_standard_error_output.splitlines(
                    keepends=True),
                self.correct_test_result.standard_error_output.splitlines(
                    keepends=True))),

            'compilation_succeeded': True,
            'compilation_stdout': 'win',
            'compilation_stderr': '',

            'return_code_points_awarded': 1,
            'return_code_points_possible': 1,
            'output_points_awarded': 2,
            'output_points_possible': 2,
            'compilation_points_awarded': 4,
            'compilation_points_possible': 4,

            'total_points_awarded': 7,
            'total_points_possible': 7,


            'timed_out': False
        }

        self.assertEqual(
            expected_high,
            self.valgrind_error_result.to_json(
                fbc.AutograderTestCaseFeedbackConfiguration.get_max_feedback()))
