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

    # # -------------------------------------------------------------------------

    # def test_exception_on_empty_name(self):
    #     self.fail()

    # # -------------------------------------------------------------------------

    # def test_exception_on_null_name(self):
    #     self.fail()

    # # -------------------------------------------------------------------------

    # def test_exception_on_null_command_line_args(self):
    #     self.fail()

    # # -------------------------------------------------------------------------

    # def test_exception_on_invalid_chars_in_command_line_args(self):
    #     pass

    # # -------------------------------------------------------------------------

    # def test_exception_on_null_test_resource_files_list(self):
    #     self.fail()

    # # -------------------------------------------------------------------------

    # def test_exception_on_test_resource_files_has_nonexistant_file(self):
    #     self.fail()

    # # -------------------------------------------------------------------------

    # def test_exception_on_zero_and_negative_time_limit(self):
    #     self.fail()

    # # -------------------------------------------------------------------------

    # def test_exception_on_use_valgrind_with_null_flags(self):
    #     self.fail()

    # # -------------------------------------------------------------------------

    # def test_exception_on_invalid_chars_in_valgrind_flags(self):
    #     pass
