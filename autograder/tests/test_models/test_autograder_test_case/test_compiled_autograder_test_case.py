import unittest

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from autograder.models import (
    AutograderTestCaseBase, AutograderTestCaseFactory)

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from .shared_tests_and_setup import (
    SharedTestsAndSetupForTestsWithCompilation,
    SharedSetUpTearDownForRunTestsWithCompilation,
    CppProgramStrs)


class CompiledAutograderTestCaseTestCase(
        SharedTestsAndSetupForTestsWithCompilation,
        TemporaryFilesystemTestCase):

    # def setUp(self):
    #     super().setUp()

    def get_ag_test_type_str_for_factory(self):
        return 'compiled_test_case'

    # -------------------------------------------------------------------------

    def test_valid_create_custom_values(self):
        AutograderTestCaseFactory.validate_and_create(
            'compiled_test_case',
            name=self.test_name, project=self.project,
            **self.compiled_test_kwargs)

        loaded_test = AutograderTestCaseBase.objects.get(
            name=self.test_name, project=self.project)

        self.assertEqual(self.compiler, loaded_test.compiler)
        self.assertEqual(self.compiler_flags, loaded_test.compiler_flags)
        self.assertEqual(
            self.files_to_compile_together,
            loaded_test.files_to_compile_together)
        self.assertEqual(self.executable_name, loaded_test.executable_name)

    # -------------------------------------------------------------------------

    def test_exception_on_empty_executable_name(self):
        self.compiled_test_kwargs['executable_name'] = ''

        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseFactory.validate_and_create(
                'compiled_test_case',
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('executable_name' in cm.exception.message_dict)

    def test_exception_on_null_executable_name(self):
        self.compiled_test_kwargs['executable_name'] = None

        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseFactory.validate_and_create(
                'compiled_test_case',
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('executable_name' in cm.exception.message_dict)

    def test_exception_on_invalid_chars_in_executable_name(self):
        self.compiled_test_kwargs['executable_name'] = "../haxorz"

        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseFactory.validate_and_create(
                'compiled_test_case',
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('executable_name' in cm.exception.message_dict)

    def test_executable_name_whitespace_stripped(self):
        self.compiled_test_kwargs['executable_name'] = "   spam.exe   "

        AutograderTestCaseFactory.validate_and_create(
            'compiled_test_case',
            name=self.test_name, project=self.project,
            **self.compiled_test_kwargs)

        loaded_test = AutograderTestCaseBase.objects.get(
            name=self.test_name, project=self.project)
        self.assertEqual(loaded_test.executable_name, 'spam.exe')

    def test_exception_on_executable_name_only_whitespace(self):
        self.compiled_test_kwargs['executable_name'] = "     "

        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseFactory.validate_and_create(
                'compiled_test_case',
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('executable_name' in cm.exception.message_dict)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


@unittest.skip('too long, needs docker')
class CompiledAutograderTestRunTestCase(
        SharedSetUpTearDownForRunTestsWithCompilation,
        TemporaryFilesystemTestCase):

    def get_ag_test_type_str_for_factory(self):
        return 'compiled_test_case'

    def test_run_correct_standard_output(self):
        stdout_content = "hello world"
        cpp_file_content = CppProgramStrs.PRINT_TO_STDOUT_TEMPLATE.format(
            stdout_content)
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        self.test_case_starter.expected_standard_output = (
            stdout_content)
        self.test_case_starter.save()

        result = self.test_case_starter.run(submission=None)

        self.assertEqual(result.standard_output, stdout_content)
        self.assertTrue(result.standard_output_correct)

    # -------------------------------------------------------------------------

    def test_run_incorrect_standard_output(self):
        cpp_file_content = CppProgramStrs.PRINT_TO_STDOUT_TEMPLATE.format(
            "wrong message")
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        expected_stdout_content = "hello world"
        self.test_case_starter.expected_standard_output = (
            expected_stdout_content)
        self.test_case_starter.save()

        result = self.test_case_starter.run(submission=None)

        self.assertNotEqual(result.standard_output, expected_stdout_content)
        self.assertFalse(result.standard_output_correct)

    # -------------------------------------------------------------------------

    def test_run_correct_standard_error_output(self):
        stderr_content = "hello world"
        cpp_file_content = CppProgramStrs.PRINT_TO_STDERR_TEMPLATE.format(
            stderr_content)
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        self.test_case_starter.expected_standard_error_output = (
            stderr_content)
        self.test_case_starter.save()

        result = self.test_case_starter.run(submission=None)

        self.assertEqual(result.standard_error_output, stderr_content)
        self.assertTrue(result.standard_error_output_correct)

    # -------------------------------------------------------------------------

    def test_run_incorrect_standard_error_output(self):
        cpp_file_content = CppProgramStrs.PRINT_TO_STDERR_TEMPLATE.format(
            "wrong output")
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        expected_stderr_content = "hello world"
        self.test_case_starter.expected_standard_error_output = (
            expected_stderr_content)
        self.test_case_starter.save()

        result = self.test_case_starter.run(submission=None)

        self.assertNotEqual(
            result.standard_error_output, expected_stderr_content)
        self.assertFalse(result.standard_error_output_correct)

    # -------------------------------------------------------------------------

    def test_run_correct_exact_return_code(self):
        expected_return_code = 0
        cpp_file_content = CppProgramStrs.RETURN_ONLY_TEMPLATE.format(
            expected_return_code)
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        self.test_case_starter.expected_return_code = expected_return_code
        self.test_case_starter.save()

        result = self.test_case_starter.run(submission=None)

        self.assertEqual(expected_return_code, result.return_code)
        self.assertTrue(result.return_code_correct)

    # -------------------------------------------------------------------------

    def test_run_incorrect_exact_return_code(self):
        cpp_file_content = CppProgramStrs.RETURN_ONLY_TEMPLATE.format(42)
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        expected_return_code = 0
        self.test_case_starter.expected_return_code = expected_return_code
        self.test_case_starter.save()

        result = self.test_case_starter.run(submission=None)

        self.assertNotEqual(expected_return_code, result.return_code)
        self.assertFalse(result.return_code_correct)

    # -------------------------------------------------------------------------

    def test_run_correct_nonzero_return_code(self):
        cpp_file_content = CppProgramStrs.RETURN_ONLY_TEMPLATE.format(42)
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        self.test_case_starter.expect_any_nonzero_return_code = True
        self.test_case_starter.save()

        result = self.test_case_starter.run(submission=None)

        self.assertNotEqual(0, result.return_code)
        self.assertTrue(result.return_code_correct)

    # -------------------------------------------------------------------------

    def test_run_incorrect_nonzero_return_code(self):
        cpp_file_content = CppProgramStrs.RETURN_ONLY_TEMPLATE.format(0)
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        self.test_case_starter.expect_any_nonzero_return_code = True
        self.test_case_starter.save()

        result = self.test_case_starter.run(submission=None)

        self.assertEqual(0, result.return_code)
        self.assertFalse(result.return_code_correct)

    # -------------------------------------------------------------------------

    def test_run_with_cmd_line_args(self):
        cmd_args = ['spam', 'egg', 'sausage']
        with open(self.cpp_filename, 'w') as f:
            f.write(CppProgramStrs.PRINT_CMD_ARGS)

        expected_output = ' '.join(cmd_args)

        self.test_case_starter.command_line_arguments = cmd_args
        self.test_case_starter.expected_standard_output = expected_output
        self.test_case_starter.save()

        result = self.test_case_starter.run(submission=None)

        self.assertEqual(expected_output, result.standard_output)
        self.assertTrue(result.standard_output_correct)

    # -------------------------------------------------------------------------

    def test_run_with_stdin_contents(self):
        with open(self.cpp_filename, 'w') as f:
            f.write(CppProgramStrs.PRINT_STDIN_CONTENT)

        expected_output = "egg bacon spam and sausage "

        self.test_case_starter.standard_input = expected_output
        self.test_case_starter.expected_standard_output = expected_output
        self.test_case_starter.save()

        result = self.test_case_starter.run(submission=None)

        self.assertEqual(expected_output, result.standard_output)
        self.assertTrue(result.standard_output_correct)

    # -------------------------------------------------------------------------

    def test_run_with_program_that_reads_from_file(self):
        expected_output = 'spam baked beans lobster sauce '

        input_filename = 'input.in'
        self.project.add_project_file(
            SimpleUploadedFile(input_filename, b''))
        with open(input_filename, 'w') as f:
            f.write(expected_output)

        with open(self.cpp_filename, 'w') as f:
            f.write(CppProgramStrs.PRINT_FILE_CONTENT)

        self.test_case_starter.expected_standard_output = expected_output
        self.test_case_starter.save()

        result = self.test_case_starter.run(submission=None)

        self.assertEqual(expected_output, result.standard_output)
        self.assertTrue(result.standard_output_correct)

    # -------------------------------------------------------------------------

    def test_run_with_timeout(self):
        with open(self.cpp_filename, 'w') as f:
            f.write(CppProgramStrs.INFINITE_LOOP)

        self.test_case_starter.time_limit = 1
        self.test_case_starter.save()

        result = self.test_case_starter.run(submission=None)

        self.assertTrue(result.timed_out)
        self.assertNotEqual(result.return_code, 0)

    # -------------------------------------------------------------------------

    def test_run_with_valgrind_no_errors(self):
        with open(self.cpp_filename, 'w') as f:
            f.write(CppProgramStrs.RETURN_ONLY_TEMPLATE.format(0))

        self.test_case_starter.use_valgrind = True
        self.test_case_starter.save()

        result = self.test_case_starter.run(submission=None)

        self.assertEqual(result.valgrind_return_code, 0)

        # We won't be checking exact valgrind output, but we want
        # to make sure that the output was still recorded.
        self.assertNotEqual(result.valgrind_output, '')
        self.assertFalse(result.valgrind_errors_present)

    # -------------------------------------------------------------------------

    def test_run_with_valgrind_with_errors(self):
        with open(self.cpp_filename, 'w') as f:
            f.write(CppProgramStrs.MEMORY_LEAK)

        self.test_case_starter.use_valgrind = True
        self.test_case_starter.save()

        result = self.test_case_starter.run(submission=None)

        self.assertNotEqual(result.valgrind_return_code, 0)

        self.assertNotEqual(result.valgrind_output, '')
        self.assertTrue(result.valgrind_errors_present)

    # -------------------------------------------------------------------------

    def test_run_compile_error(self):
        with open(self.cpp_filename, 'w') as f:
            f.write(CppProgramStrs.COMPILE_ERROR)

        self.test_case_starter.save()

        result = self.test_case_starter.run(submission=None)

        self.assertNotEqual(result.compilation_return_code, 0)
        self.assertNotEqual(result.compilation_standard_error_output, '')
        self.assertFalse(result.compilation_succeeded)

    # -------------------------------------------------------------------------

    def test_run_everything_correct(self):
        stdout_msg = 'standard spam output'
        stderr_msg = 'standard llama error output'
        cpp_file_content = CppProgramStrs.DO_EVERYTHING.format(
            stdout_str=stdout_msg, stderr_str=stderr_msg, return_code=0)
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        file_content = 'stuff to read from file '
        input_filename = 'input.in'
        self.project.add_project_file(
            SimpleUploadedFile(input_filename, b''))
        with open(input_filename, 'w') as f:
            f.write(file_content)

        stdin_content = 'some content for stdin '

        cmd_args = ['zomg', 'wtf', 'bbq']

        expected_stdout = (
            ' '.join(cmd_args) + file_content + stdin_content +
            stdout_msg
        )

        self.test_case_starter.command_line_arguments = cmd_args
        self.test_case_starter.expected_standard_output = expected_stdout
        self.test_case_starter.expected_standard_error_output = stderr_msg
        self.test_case_starter.standard_input = stdin_content
        self.test_case_starter.expected_return_code = 0
        self.test_case_starter.use_valgrind = True

        self.test_case_starter.save()
        result = self.test_case_starter.run(submission=None)

        self.assertEqual(expected_stdout, result.standard_output)
        self.assertTrue(result.standard_output_correct)

        self.assertEqual(stderr_msg, result.standard_error_output)
        self.assertTrue(result.standard_error_output_correct)

        self.assertEqual(0, result.return_code)
        self.assertTrue(result.return_code_correct)

        self.assertEqual(0, result.valgrind_return_code)
        self.assertFalse(result.valgrind_errors_present)

    # -------------------------------------------------------------------------

    def test_run_everything_incorrect(self):
        stdout_msg = '" << new int(42) << "'
        cpp_file_content = CppProgramStrs.DO_EVERYTHING.format(
            stdout_str=stdout_msg, stderr_str='', return_code=1)
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        file_content = 'stuff to read from file '
        input_filename = 'input.in'
        self.project.add_project_file(
            SimpleUploadedFile(input_filename, b''))
        with open(input_filename, 'w') as f:
            f.write(file_content)

        stdin_content = 'some content for stdin '

        cmd_args = ['zomg', 'wtf', 'bbq']

        expected_stdout = 'spaaaaaaaaaam'

        self.test_case_starter.command_line_arguments = cmd_args
        self.test_case_starter.expected_standard_output = expected_stdout
        self.test_case_starter.expected_standard_error_output = 'stderr_msg'
        self.test_case_starter.standard_input = stdin_content
        self.test_case_starter.expected_return_code = 0
        self.test_case_starter.use_valgrind = True

        self.test_case_starter.save()
        result = self.test_case_starter.run(submission=None)

        self.assertNotEqual(expected_stdout, result.standard_output)
        self.assertFalse(result.standard_output_correct)

        self.assertNotEqual('stderr_msg', result.standard_error_output)
        self.assertFalse(result.standard_error_output_correct)

        self.assertNotEqual(0, result.return_code)
        self.assertFalse(result.return_code_correct)

        self.assertNotEqual(0, result.valgrind_return_code)
        self.assertTrue(result.valgrind_errors_present)

    # -------------------------------------------------------------------------

    @unittest.skip('not implemented')
    def test_run_with_pattern_in_files_to_compile(self):
        self.fail()
