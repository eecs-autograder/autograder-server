from django.db.utils import IntegrityError

from autograder.models import Project, Semester, Course, AutograderTestCaseBase

import autograder.shared.utilities as ut
import autograder.shared.global_constants as gc

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)


class AutograderTestCaseBaseTestCase(TemporaryFilesystemTestCase):
    """
    To the reader: I apologize for the strangeness of writing test cases
    for a class that is another type of test case. You can distinguish
    between them by the packages in which they are kept.
    """
    def setUp(self):
        super().setUp()
        self.course = Course.objects.create(name='eecs280')
        self.semester = Semester.objects.create(name='f15', course=self.course)
        self.project = Project.objects.create(
            name='my_project', semester=self.semester)
        self.project.add_project_file("spam.txt", "hello there!")

        self.TEST_NAME = 'my_test'

    # -------------------------------------------------------------------------

    def test_valid_initialization_with_defaults(self):
        new_test_case = AutograderTestCaseBase.objects.create(
            name=self.TEST_NAME, project=self.project)

        loaded_test_case = AutograderTestCaseBase.get_by_composite_key(
            self.TEST_NAME, self.project)

        self.assertEqual(new_test_case, loaded_test_case)
        self.assertEqual(self.TEST_NAME, loaded_test_case.name)
        self.assertEqual(self.project, loaded_test_case.project)

        self.assertEqual(loaded_test_case.command_line_arguments, [])
        self.assertEqual(loaded_test_case.standard_input_stream_contents, "")
        self.assertEqual(loaded_test_case.test_resource_files, [])
        self.assertEqual(loaded_test_case.time_limit, 30)
        self.assertIsNone(loaded_test_case.expected_program_return_code)
        self.assertFalse(loaded_test_case.expect_any_nonzero_return_code)
        self.assertEqual(
            loaded_test_case.expected_program_standard_output_stream_content,
            "")
        self.assertEqual(
            loaded_test_case.expected_program_standard_error_stream_content,
            "")
        self.assertFalse(loaded_test_case.use_valgrind)
        self.assertIsNone(loaded_test_case.valgrind_flags)

    # -------------------------------------------------------------------------

    def test_valid_initialization_custom_values(self):
        cmd_args = ['spam', '--eggs', '--sausage=spam', '-p']
        input_stream_content = "spameggsausagespam"
        out_stream_content = "standardspaminputspam"
        err_stream_content = "errorzspam"
        resource_files = ['spam.txt']
        time = 5
        ret_code = 0
        valgrind_flags = ['--leak-check=yes', '--error-exitcode=9000']

        new_test_case = AutograderTestCaseBase.objects.create(
            name=self.TEST_NAME, project=self.project,
            command_line_arguments=cmd_args,
            standard_input_stream_contents=input_stream_content,
            test_resource_files=resource_files,
            time_limit=time,
            expected_program_return_code=ret_code,
            expected_program_standard_output_stream_content=out_stream_content,
            expected_program_standard_error_stream_content=err_stream_content,
            use_valgrind=True,
            valgrind_flags=valgrind_flags
        )

        loaded_test_case = AutograderTestCaseBase.get_by_composite_key(
            self.TEST_NAME, self.project)

        self.assertEqual(new_test_case, loaded_test_case)
        self.assertEqual(self.TEST_NAME, loaded_test_case.name)
        self.assertEqual(self.project, loaded_test_case.project)

        self.assertEqual(loaded_test_case.command_line_arguments, cmd_args)
        self.assertEqual(
            loaded_test_case.standard_input_stream_contents,
            input_stream_content)
        self.assertEqual(loaded_test_case.test_resource_files, resource_files)
        self.assertEqual(loaded_test_case.time_limit, time)
        self.assertEqual(
            loaded_test_case.expected_program_return_code, ret_code)
        self.assertEqual(
            loaded_test_case.expected_program_standard_output_stream_content,
            out_stream_content)
        self.assertEqual(
            loaded_test_case.expected_program_standard_error_stream_content,
            err_stream_content)
        self.assertTrue(loaded_test_case.use_valgrind)
        self.assertEqual(loaded_test_case.valgrind_flags, valgrind_flags)

    # -------------------------------------------------------------------------

    def test_exception_on_non_unique_name_within_project(self):
        AutograderTestCaseBase.objects.create(
            name=self.TEST_NAME, project=self.project)

        with self.assertRaises(IntegrityError):
            AutograderTestCaseBase.objects.create(
                name=self.TEST_NAME, project=self.project)

    # -------------------------------------------------------------------------

    def test_no_exception_same_name_different_project(self):
        other_project = Project.objects.create(
            name='other_project', semester=self.semester)

        new_test_case = AutograderTestCaseBase.objects.create(
            name=self.TEST_NAME, project=other_project)

        loaded_test_case = AutograderTestCaseBase.get_by_composite_key(
            self.TEST_NAME, other_project)

        self.assertEqual(new_test_case, loaded_test_case)

    # -------------------------------------------------------------------------

    def test_no_exception_same_name_and_project_name_different_semester(self):
        other_semester = Semester.objects.create(
            name='other_semester', course=self.course)

        other_project = Project.objects.create(
            name=self.project.name, semester=other_semester)

        new_test_case = AutograderTestCaseBase.objects.create(
            name=self.TEST_NAME, project=other_project)

        loaded_test_case = AutograderTestCaseBase.get_by_composite_key(
            self.TEST_NAME, other_project)

        self.assertEqual(new_test_case, loaded_test_case)

    # -------------------------------------------------------------------------

    def test_no_exception_same_name_project_name_and_semester_name_different_course(self):
        other_course = Course.objects.create(
            name='other_course')

        other_semester = Semester.objects.create(
            name=self.semester.name, course=other_course)

        other_project = Project.objects.create(
            name=self.project.name, semester=other_semester)

        new_test_case = AutograderTestCaseBase.objects.create(
            name=self.TEST_NAME, project=other_project)

        loaded_test_case = AutograderTestCaseBase.get_by_composite_key(
            self.TEST_NAME, other_project)

        self.assertEqual(new_test_case, loaded_test_case)

    # -------------------------------------------------------------------------

    def test_exception_on_empty_name(self):
        with self.assertRaises(ValueError):
            AutograderTestCaseBase.objects.create(
                name='', project=self.project)

    # -------------------------------------------------------------------------

    def test_exception_on_null_name(self):
        with self.assertRaises(ValueError):
            AutograderTestCaseBase.objects.create(
                name=None, project=self.project)

    # -------------------------------------------------------------------------

    def test_exception_on_null_command_line_args(self):
        with self.assertRaises(ValueError):
            AutograderTestCaseBase.objects.create(
                name=self.TEST_NAME, project=self.project,
                command_line_arguments=None)

    # -------------------------------------------------------------------------

    def test_exception_on_invalid_chars_in_command_line_args(self):
        with self.assertRaises(ValueError):
            AutograderTestCaseBase.objects.create(
                name=self.TEST_NAME, project=self.project,
                command_line_arguments=["spam", "; echo 'haxorz!'"])

    # -------------------------------------------------------------------------

    def test_exception_on_null_test_resource_files_list(self):
        with self.assertRaises(ValueError):
            AutograderTestCaseBase.objects.create(
                name=self.TEST_NAME, project=self.project,
                test_resource_files=None)

    # -------------------------------------------------------------------------

    def test_exception_on_test_resource_files_has_nonexistant_file(self):
        with self.assertRaises(ValueError):
            AutograderTestCaseBase.objects.create(
                name=self.TEST_NAME, project=self.project,
                test_resource_files=['no_file.txt'])

    # -------------------------------------------------------------------------

    def test_exception_on_zero_and_negative_time_limit(self):
        with self.assertRaises(ValueError):
            AutograderTestCaseBase.objects.create(
                name=self.TEST_NAME, project=self.project,
                time_limit=0)

        with self.assertRaises(ValueError):
            AutograderTestCaseBase.objects.create(
                name=self.TEST_NAME, project=self.project,
                time_limit=-1)

    # -------------------------------------------------------------------------

    def test_nonzero_expected_return_code(self):
        AutograderTestCaseBase.objects.create(
            name=self.TEST_NAME, project=self.project,
            expect_any_nonzero_return_code=True)

        loaded_test_case = AutograderTestCaseBase.get_by_composite_key(
            self.TEST_NAME, self.project)

        self.assertTrue(loaded_test_case.expect_any_nonzero_return_code)

    # -------------------------------------------------------------------------

    def test_exception_on_use_valgrind_with_null_flags(self):
        ag_test = AutograderTestCaseBase.objects.create(
            name=self.TEST_NAME, project=self.project,
            use_valgrind=True)

        ag_test.valgrind_flags = None

        with self.assertRaises(ValueError):
            ag_test.save()

    # -------------------------------------------------------------------------

    def test_use_valgrind_default_flags(self):
        AutograderTestCaseBase.objects.create(
            name=self.TEST_NAME, project=self.project,
            use_valgrind=True)

        loaded_test_case = AutograderTestCaseBase.get_by_composite_key(
            self.TEST_NAME, self.project)

        self.assertTrue(loaded_test_case.use_valgrind)
        self.assertEqual(
            loaded_test_case.valgrind_flags,
            gc.DEFAULT_VALGRIND_FLAGS_WHEN_USED)

    # -------------------------------------------------------------------------

    def test_exception_on_invalid_chars_in_valgrind_flags(self):
        with self.assertRaises(ValueError):
            AutograderTestCaseBase.objects.create(
                name=self.TEST_NAME, project=self.project,
                use_valgrind=True,
                valgrind_flags=['--leak-check=full', "; echo 'haxorz!'"])
