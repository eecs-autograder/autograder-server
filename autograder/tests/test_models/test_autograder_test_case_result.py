import difflib

from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.tests.dummy_object_utils as obj_ut

from autograder.models import (
    Project, Semester, Course, AutograderTestCaseBase,
    CompiledAutograderTestCase, AutograderTestCaseResultBase,
    CompiledAutograderTestCaseResult, SubmissionGroup, Submission)
from autograder.models.fields import FeedbackConfiguration

_DIFFER = difflib.Differ()


class AutograderTestCaseResultTestCase(TemporaryFilesystemTestCase):
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

        self.TEST_NAME = 'my_test'

        self.test_case = AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project)

    # -------------------------------------------------------------------------

    def test_default_init(self):
        result = AutograderTestCaseResultBase.objects.create(
            test_case=self.test_case)

        loaded_result = AutograderTestCaseResultBase.objects.filter(
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
            files_to_compile_together=['spam.cpp', 'egg.cpp'],
            executable_name='prog',
            points_for_correct_return_code=1,
            points_for_correct_output=2,
            points_for_no_valgrind_errors=3,
            points_for_compilation_success=4)

        self.correct_test_result = AutograderTestCaseResultBase.objects.create(
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

        self.compile_fail_test_result = AutograderTestCaseResultBase.objects.create(
            test_case=self.test_case,
            compilation_return_code=42,
            compilation_standard_output='',
            compilation_standard_error_output='lose')

        self.incorrect_test_result = AutograderTestCaseResultBase.objects.create(
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

        self.timed_out_result = AutograderTestCaseResultBase.objects.create(
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
                'timed_out': True
            },
            self.timed_out_result.to_json())

    def test_serialize_results_medium_feedback(self):
        self.project.test_case_feedback_configuration = FeedbackConfiguration(
            return_code_feedback_level='correct_or_incorrect_only',
            output_feedback_level='correct_or_incorrect_only',
            compilation_feedback_level='success_or_failure_only',
            valgrind_feedback_level='errors_or_no_errors_only',
            points_feedback_level='show_total'
        )
        self.project.save()

        expected_correct = {
            'test_name': self.test_case.name,
            'return_code_correct': True,
            'output_correct': True,
            'valgrind_errors_present': False,
            'compilation_succeeded': True,
            'total_points': 10,

            'timed_out': False
        }

        expected_incorrect = {
            'test_name': self.test_case.name,
            'return_code_correct': False,
            'output_correct': False,
            'valgrind_errors_present': True,
            'compilation_succeeded': True,
            'total_points': 4,

            'timed_out': False
        }

        self.assertEqual(
            expected_correct,
            self.correct_test_result.to_json())

        self.assertEqual(
            expected_incorrect,
            self.incorrect_test_result.to_json())

        self.assertEqual(
            {
                'test_name': self.test_case.name,
                'timed_out': True,
                'compilation_succeeded': True,
                'total_points': 4
            },
            self.timed_out_result.to_json())

    def test_serialize_results_high_feedback(self):
        self.project.test_case_feedback_configuration = (
            FeedbackConfiguration.get_max_feedback())
        self.project.save()

        expected_correct = {
            'test_name': self.test_case.name,
            'return_code_correct': True,
            'expected_return_code': 0,
            'actual_return_code': 0,


            'output_correct': True,
            'stdout_diff': list(_DIFFER.compare(
                self.test_case.expected_standard_output.splitlines(keepends=True),
                self.correct_test_result.standard_output.splitlines(keepends=True))),
            'stderr_diff': list(_DIFFER.compare(
                self.test_case.expected_standard_error_output.splitlines(keepends=True),
                self.correct_test_result.standard_error_output.splitlines(keepends=True))),


            'valgrind_errors_present': False,
            'valgrind_output': 'clean',


            'compilation_succeeded': True,
            'compilation_stdout': 'win',
            'compilation_stderr': '',


            'return_code_points': 1,
            'output_points': 2,
            'valgrind_points': 3,
            'compilation_points': 4,

            'total_points': 10,


            'timed_out': False
        }

        actual = self.correct_test_result.to_json()
        self.assertEqual(expected_correct, actual)

        expected_compile_fail = {
            'test_name': self.test_case.name,
            'compilation_succeeded': False,
            'compilation_stdout': '',
            'compilation_stderr': 'lose',

            'compilation_points': 0,

            'total_points': 0,
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
                self.test_case.expected_standard_output.splitlines(keepends=True),
                self.incorrect_test_result.standard_output.splitlines(keepends=True))),
            'stderr_diff': list(_DIFFER.compare(
                self.test_case.expected_standard_error_output.splitlines(keepends=True),
                self.incorrect_test_result.standard_error_output.splitlines(keepends=True))),


            'valgrind_errors_present': True,
            'valgrind_output': 'error',


            'compilation_succeeded': True,
            'compilation_stdout': 'hello',
            'compilation_stderr': 'woah',


            'return_code_points': 0,
            'output_points': 0,
            'valgrind_points': 0,
            'compilation_points': 4,

            'total_points': 4,


            'timed_out': False
        }

        self.assertEqual(
            expected_incorrect,
            self.incorrect_test_result.to_json())

        expected_timeout = {
            'test_name': self.test_case.name,
            'compilation_succeeded': True,
            'compilation_stdout': 'win',
            'compilation_stderr': '',

            'compilation_points': 4,

            'total_points': 4,

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

    def test_serialize_results_with_submission_feedback_override(self):
        override = FeedbackConfiguration(
            return_code_feedback_level='correct_or_incorrect_only')
        override.validate()

        self.submission.test_case_feedback_config_override = override
        self.submission.save()

        self.correct_test_result.submission = self.submission
        self.correct_test_result.save()

        self.assertEqual(
            {
                'test_name': self.test_case.name,
                'timed_out': False,
                'return_code_correct': True
            },
            self.correct_test_result.to_json())

    def test_serialize_results_with_manual_feedback_override(self):
        override = FeedbackConfiguration(
            return_code_feedback_level='correct_or_incorrect_only')
        override.validate()

        self.assertEqual(
            {
                'test_name': self.test_case.name,
                'timed_out': False,
                'return_code_correct': True
            },
            self.correct_test_result.to_json(override_feedback=override))

    # def test_output_diff_html_escaped(self):
    #     self.incorrect_test_result.stdout = '<div>hello</div>'
    #     self.incorrect_test_result.stderr = (
    #         '<script type=text/javascript>haxorz</script>')
    #     self.incorrect_test_result.save()

    #     override = FeedbackConfiguration(
    #         output_feedback_level='show_expected_and_actual_values')
    #     override.validate()

    #     self.submission.test_case_feedback_config_override = override
    #     self.submission.save()

    #     self.incorrect_test_result.submission = self.submission
    #     self.incorrect_test_result.save()

    #     result = self.incorrect_test_result.to_json()

    #     expected = _DIFFER.compare(
    #         self.test_case.expected_standard_output.splitlines(keepends=True),
    #         self.incorrect_test_result.standard_output.splitlines(keepends=True)
    #     )
    #     self.assertEqual(list(expected), result['stdout_diff'])

    #     expected = _DIFFER.compare(
    #         self.test_case.expected_standard_error_output.splitlines(keepends=True),
    #         self.incorrect_test_result.standard_error_output.splitlines(keepends=True)
    #     )
    #     self.assertEqual(list(expected), result['stderr_diff'])

    import unittest

    @unittest.skip('todo')
    def test_points_breakdown_feedback(self):
        self.fail()

    @unittest.skip('todo')
    def test_not_using_valgrind(self):
        self.fail()
