import random
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
# from django.core.exceptions import ValidationError

import autograder.core.models as ag_models

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from .utils import (
    SharedSetUpTearDownForRunTestsWithCompilation,
    CppProgramStrs)

import autograder.core.tests.dummy_object_utils as obj_ut


# class _SetUpBase:
#     def setUp(self):
#         super().setUp()

#         self.project = obj_ut.build_project()

#         # self.project = Project.objects.validate_and_create(
#         #     name='my_project', semester=semester,
#         #     required_student_files=['file1.cpp', 'file2.cpp'],
#         #     expected_student_file_patterns=[
#         #         Project.FilePatternTuple('test_*.cpp', 1, 2),
#         #         Project.FilePatternTuple('funsy[0-9].cpp', 0, 2)])

#         self.expected_files_settings = [
#             {
#                 pattern='file1.cpp',
#                 project=self.project,
#             },
#             {
#                 pattern='file2.cpp',
#                 project=self.project,
#             },
#             {

#             },
#             {

#             },
#         ]

#         self.expected_files = [
#             ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
#                 project=self.project,
#                 pattern='file1.cpp',

#             )
#         ]

#         self.project_file_objs = [
#             SimpleUploadedFile('spam.txt', b'hello there!'),
#             SimpleUploadedFile('eggs.cpp', b'egg bacon spam and sausage'),
#             SimpleUploadedFile('sausage.cpp', b'spam egg sausage and spam')
#         ]

#         for file_obj in self.project_file_objs:
#             ag_models.UploadedFile.objects.validate_and_create(
#                 project=self.project,
#                 file_obj=file_obj)

#         self.test_name = 'my_test'

#         self.compiler = 'g++'
#         self.compiler_flags = ['--foo_arg=bar', '-s']

#         self.project_files_to_compile_together = [
#             'spam.txt'
#         ]
#         self.student_files_to_compile_together = [
#             'file1.cpp',  # required student file
#             'test_*.cpp'  # expected student pattern
#         ]
#         self.executable_name = "sausage.exe"

#         self.compiled_test_kwargs = {
#             "test_resource_files": ['spam.txt'],
#             "student_resource_files": ['file1.cpp', 'test_*.cpp'],
#             "compiler": self.compiler,
#             "compiler_flags": self.compiler_flags,
#             "project_files_to_compile_together": self.project_files_to_compile_together,
#             "student_files_to_compile_together": self.student_files_to_compile_together,
#             "executable_name": self.executable_name,
#         }

# -----------------------------------------------------------------------------


# class CompiledAndRunAutograderTestCaseTestCase(_SetUpBase,
#                                                TemporaryFilesystemTestCase):
#     def test_valid_create_custom_values(self):
#         AutograderTestCaseFactory.validate_and_create(
#             'compiled_and_run_test_case',
#             name=self.test_name, project=self.project,
#             **self.compiled_test_kwargs)

#         loaded_test = AutograderTestCaseBase.objects.get(
#             name=self.test_name, project=self.project)

#         self.assertEqual(self.compiler, loaded_test.compiler)
#         self.assertEqual(self.compiler_flags, loaded_test.compiler_flags)
#         self.assertEqual(
#             self.project_files_to_compile_together,
#             loaded_test.project_files_to_compile_together)
#         self.assertEqual(
#             self.student_files_to_compile_together,
#             loaded_test.student_files_to_compile_together)
#         self.assertEqual(self.executable_name, loaded_test.executable_name)

    # -------------------------------------------------------------------------



    # def test_executable_name_whitespace_stripped(self):
    #     self.compiled_test_kwargs['executable_name'] = "   spam.exe   "

    #     AutograderTestCaseFactory.validate_and_create(
    #         'compiled_and_run_test_case',
    #         name=self.test_name, project=self.project,
    #         **self.compiled_test_kwargs)

    #     loaded_test = AutograderTestCaseBase.objects.get(
    #         name=self.test_name, project=self.project)
    #     self.assertEqual(loaded_test.executable_name, 'spam.exe')

    # def test_exception_on_executable_name_only_whitespace(self):
    #     self.compiled_test_kwargs['executable_name'] = "     "

    #     with self.assertRaises(ValidationError) as cm:
    #         AutograderTestCaseFactory.validate_and_create(
    #             'compiled_and_run_test_case',
    #             name=self.test_name, project=self.project,
    #             **self.compiled_test_kwargs)

    #     self.assertTrue('executable_name' in cm.exception.message_dict)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class CompiledAutograderTestRunTestCase(
        SharedSetUpTearDownForRunTestsWithCompilation,
        TemporaryFilesystemTestCase):

    def get_ag_test_type_str_for_factory(self):
        return 'compiled_and_run_test_case'

    def test_run_correct_standard_output(self):
        stdout_content = "hello world"
        main_file_content = CppProgramStrs.PRINT_TO_STDOUT_TEMPLATE.format(
            stdout_content)

        # NOTE: Currently, changing the mode on a FieldFile doesn't work
        with open(self.main_file.abspath, 'w') as f:
            f.write(main_file_content)

        self.test_case_starter.validate_and_update(
            expected_standard_output=stdout_content)

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)
        result.save()
        result.refresh_from_db()

        self.assertEqual(result.standard_output, stdout_content)
        self.assertTrue(result.standard_output_correct)

    def test_run_incorrect_standard_output(self):
        cpp_file_content = CppProgramStrs.PRINT_TO_STDOUT_TEMPLATE.format(
            "wrong message")
        with open(self.main_file.abspath, 'w') as f:
            f.write(cpp_file_content)

        expected_stdout_content = "hello world"
        self.test_case_starter.validate_and_update(
            expected_standard_output=expected_stdout_content)

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)
        result.save()
        result.refresh_from_db()

        self.assertNotEqual(result.standard_output, expected_stdout_content)
        self.assertFalse(result.standard_output_correct)

    def test_run_correct_standard_error_output(self):
        stderr_content = "hello world"
        cpp_file_content = CppProgramStrs.PRINT_TO_STDERR_TEMPLATE.format(
            stderr_content)
        with open(self.main_file.abspath, 'w') as f:
            f.write(cpp_file_content)

        self.test_case_starter.validate_and_update(
            expected_standard_error_output=stderr_content)

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)
        result.save()
        result.refresh_from_db()

        self.assertEqual(result.standard_error_output, stderr_content)
        self.assertTrue(result.standard_error_output_correct)

    def test_run_incorrect_standard_error_output(self):
        cpp_file_content = CppProgramStrs.PRINT_TO_STDERR_TEMPLATE.format(
            "wrong output")
        with open(self.main_file.abspath, 'w') as f:
            f.write(cpp_file_content)

        expected_stderr_content = "hello world"
        self.test_case_starter.validate_and_update(
            expected_standard_error_output=expected_stderr_content)

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)
        result.save()
        result.refresh_from_db()

        self.assertNotEqual(
            result.standard_error_output, expected_stderr_content)
        self.assertFalse(result.standard_error_output_correct)

    def test_run_correct_exact_return_code(self):
        expected_return_code = 0
        cpp_file_content = CppProgramStrs.RETURN_ONLY_TEMPLATE.format(
            expected_return_code)
        with open(self.main_file.abspath, 'w') as f:
            f.write(cpp_file_content)

        self.test_case_starter.expected_return_code = expected_return_code
        self.test_case_starter.save()

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)
        result.save()
        result.refresh_from_db()

        self.assertEqual(expected_return_code, result.return_code)
        self.assertTrue(result.return_code_correct)

    def test_run_incorrect_exact_return_code(self):
        cpp_file_content = CppProgramStrs.RETURN_ONLY_TEMPLATE.format(42)
        with open(self.main_file.abspath, 'w') as f:
            f.write(cpp_file_content)

        expected_return_code = 0
        self.test_case_starter.expected_return_code = expected_return_code
        self.test_case_starter.save()

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)
        result.save()
        result.refresh_from_db()

        self.assertNotEqual(expected_return_code, result.return_code)
        self.assertFalse(result.return_code_correct)

    def test_run_correct_nonzero_return_code(self):
        cpp_file_content = CppProgramStrs.RETURN_ONLY_TEMPLATE.format(42)
        with open(self.main_file.abspath, 'w') as f:
            f.write(cpp_file_content)

        self.test_case_starter.expect_any_nonzero_return_code = True
        self.test_case_starter.save()

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)
        result.save()
        result.refresh_from_db()

        self.assertNotEqual(0, result.return_code)
        self.assertTrue(result.return_code_correct)

    def test_run_incorrect_nonzero_return_code(self):
        cpp_file_content = CppProgramStrs.RETURN_ONLY_TEMPLATE.format(0)
        with open(self.main_file.abspath, 'w') as f:
            f.write(cpp_file_content)

        self.test_case_starter.expect_any_nonzero_return_code = True
        self.test_case_starter.save()

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)
        result.save()
        result.refresh_from_db()

        self.assertEqual(0, result.return_code)
        self.assertFalse(result.return_code_correct)

    def test_run_with_cmd_line_args(self):
        cmd_args = ['spam', 'egg', 'sausage']
        with open(self.main_file.abspath, 'w') as f:
            f.write(CppProgramStrs.PRINT_CMD_ARGS)

        expected_output = ' '.join(cmd_args)

        self.test_case_starter.command_line_arguments = cmd_args
        self.test_case_starter.expected_standard_output = expected_output
        self.test_case_starter.save()

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)
        result.save()
        result.refresh_from_db()

        self.assertEqual(expected_output, result.standard_output)
        self.assertTrue(result.standard_output_correct)

    def test_run_with_stdin_contents(self):
        with open(self.main_file.abspath, 'w') as f:
            f.write(CppProgramStrs.PRINT_STDIN_CONTENT)

        expected_output = "egg bacon spam and sausage "

        self.test_case_starter.validate_and_update(
            standard_input=expected_output,
            expected_standard_output=expected_output)

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)
        print(result.standard_output)
        result.save()
        result.refresh_from_db()

        self.assertEqual(expected_output, result.standard_output)
        self.assertTrue(result.standard_output_correct)

    def test_run_with_program_that_reads_from_file(self):
        expected_output = 'spam baked beans lobster sauce '

        input_filename = 'input.in'
        input_file = ag_models.UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=SimpleUploadedFile(input_filename,
                                        expected_output.encode('utf-8')))

        with open(self.main_file.abspath, 'w') as f:
            f.write(CppProgramStrs.PRINT_FILE_CONTENT)

        self.test_case_starter.test_resource_files.add(input_file)

        self.test_case_starter.validate_and_update(
            expected_standard_output=expected_output)

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)
        result.save()
        result.refresh_from_db()

        self.assertEqual(expected_output, result.standard_output)
        self.assertTrue(result.standard_output_correct)

    def test_run_with_timeout(self):
        with open(self.main_file.abspath, 'w') as f:
            f.write(CppProgramStrs.INFINITE_LOOP)

        self.test_case_starter.time_limit = 1
        self.test_case_starter.save()

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)
        result.save()
        result.refresh_from_db()

        self.assertTrue(result.timed_out)
        self.assertNotEqual(result.return_code, 0)

    def test_run_with_valgrind_no_errors(self):
        with open(self.main_file.abspath, 'w') as f:
            f.write(CppProgramStrs.RETURN_ONLY_TEMPLATE.format(0))

        self.test_case_starter.use_valgrind = True
        self.test_case_starter.save()

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)
        result.save()
        result.refresh_from_db()

        self.assertEqual(result.valgrind_return_code, 0)

        # We won't be checking exact valgrind output, but we want
        # to make sure that the output was still recorded.
        self.assertNotEqual(result.valgrind_output, '')
        self.assertFalse(result.valgrind_errors_present)

    def test_run_with_valgrind_with_errors(self):
        with open(self.main_file.abspath, 'w') as f:
            f.write(CppProgramStrs.MEMORY_LEAK)

        self.test_case_starter.use_valgrind = True
        self.test_case_starter.save()

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)
        result.save()
        result.refresh_from_db()

        self.assertNotEqual(result.valgrind_return_code, 0)

        self.assertNotEqual(result.valgrind_output, '')
        self.assertTrue(result.valgrind_errors_present)

    def test_run_compile_error(self):
        with open(self.main_file.abspath, 'w') as f:
            f.write(CppProgramStrs.COMPILE_ERROR)

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)
        result.save()
        result.refresh_from_db()

        self.assertNotEqual(result.compilation_return_code, 0)
        self.assertNotEqual(result.compilation_standard_error_output, '')
        self.assertFalse(result.compilation_succeeded)

    def test_run_everything_correct(self):
        stdout_msg = 'standard spam output'
        stderr_msg = 'standard llama error output'
        cpp_file_content = CppProgramStrs.DO_EVERYTHING.format(
            stdout_str=stdout_msg, stderr_str=stderr_msg, return_code=0)
        with open(self.main_file.abspath, 'w') as f:
            f.write(cpp_file_content)

        file_content = 'stuff to read from file '
        input_filename = 'input.in'

        input_file = ag_models.UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=SimpleUploadedFile(input_filename,
                                        file_content.encode('utf-8')))
        self.test_case_starter.test_resource_files.add(input_file)

        stdin_content = 'some content for stdin '
        cmd_args = ['zomg', 'wtf', 'bbq']
        expected_stdout = (
            ' '.join(cmd_args) + file_content + stdin_content +
            stdout_msg
        )

        self.test_case_starter.validate_and_update(
            command_line_arguments=cmd_args,
            expected_standard_output=expected_stdout,
            expected_standard_error_output=stderr_msg,
            standard_input=stdin_content,
            expected_return_code=0,
            use_valgrind=True,
        )

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)
        result.save()
        result.refresh_from_db()

        self.assertEqual(expected_stdout, result.standard_output)
        self.assertTrue(result.standard_output_correct)

        self.assertEqual(stderr_msg, result.standard_error_output)
        self.assertTrue(result.standard_error_output_correct)

        self.assertEqual(0, result.return_code)
        self.assertTrue(result.return_code_correct)

        self.assertEqual(0, result.valgrind_return_code)
        self.assertFalse(result.valgrind_errors_present)

    def test_run_everything_incorrect(self):
        stdout_msg = '" << new int(42) << "'
        cpp_file_content = CppProgramStrs.DO_EVERYTHING.format(
            stdout_str=stdout_msg, stderr_str='', return_code=1)
        with open(self.main_file.abspath, 'w') as f:
            f.write(cpp_file_content)

        file_content = 'stuff to read from file '
        input_filename = 'input.in'

        input_file = ag_models.UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=SimpleUploadedFile(input_filename,
                                        file_content.encode('utf-8')))

        self.test_case_starter.test_resource_files.add(input_file)

        stdin_content = 'some content for stdin '
        cmd_args = ['zomg', 'wtf', 'bbq']
        expected_stdout = 'spaaaaaaaaaam'

        self.test_case_starter.validate_and_update(
            command_line_arguments=cmd_args,
            expected_standard_output=expected_stdout,
            expected_standard_error_output='stderr_msg',
            standard_input=stdin_content,
            expected_return_code=0,
            use_valgrind=True
        )

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)
        result.save()
        result.refresh_from_db()

        self.assertNotEqual(expected_stdout, result.standard_output)
        self.assertFalse(result.standard_output_correct)

        self.assertNotEqual('stderr_msg', result.standard_error_output)
        self.assertFalse(result.standard_error_output_correct)

        self.assertNotEqual(0, result.return_code)
        self.assertFalse(result.return_code_correct)

        self.assertNotEqual(0, result.valgrind_return_code)
        self.assertTrue(result.valgrind_errors_present)


class CompiledAGTestResourceLimitTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.stack_limit = random.randint(1000, 8000)
        self.virtual_mem_limit = random.randint(100000000, 200000000)
        self.process_limit = random.randint(1, 5)

        project = obj_ut.build_project()

        self.test = ag_models.AutograderTestCaseFactory.validate_and_create(
            'compiled_and_run_test_case',
            name='testy',
            project=project,
            process_spawn_limit=self.process_limit,
            stack_size_limit=self.stack_limit,
            virtual_memory_limit=self.virtual_mem_limit,
            compiler='g++')

    @mock.patch('autograder.security.autograder_sandbox.AutograderSandbox',
                autospec=True)
    def test_resource_limits_set(self, MockSandbox):
        run_cmd_mock_result = mock.Mock()
        type(run_cmd_mock_result).return_code = (
            mock.PropertyMock(return_value=0))

        sandbox = MockSandbox()
        sandbox.run_command.return_value = run_cmd_mock_result
        self.test.run(None, sandbox)

        sandbox.run_command.assert_called_with(
            ['./' + self.test.executable_name],
            input_content='',
            timeout=self.test.time_limit,
            max_num_processes=self.process_limit,
            max_stack_size=self.stack_limit,
            max_virtual_memory=self.virtual_mem_limit)

    @mock.patch('autograder.security.autograder_sandbox.AutograderSandbox',
                autospec=True)
    def test_resource_limits_used_with_valgrind(self, MockSandbox):
        self.test.use_valgrind = True
        self.test.valgrind_flags = ['asdf']
        self.test.save()

        run_cmd_mock_result = mock.Mock()
        type(run_cmd_mock_result).return_code = (
            mock.PropertyMock(return_value=0))

        sandbox = MockSandbox()
        sandbox.run_command.return_value = run_cmd_mock_result
        self.test.run(None, sandbox)

        sandbox.run_command.assert_called_with(
            ['valgrind'] + self.test.valgrind_flags +
            ['./' + self.test.executable_name],
            input_content='',
            timeout=self.test.time_limit,
            max_num_processes=self.process_limit,
            max_stack_size=self.stack_limit,
            max_virtual_memory=self.virtual_mem_limit)
