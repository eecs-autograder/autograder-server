import os

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from autograder.models import (
    Project, Semester, Course, AutograderTestCaseBase,
    CompiledAutograderTestCase)

# import autograder.shared.utilities as ut
import autograder.shared.global_constants as gc

from autograder.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)


class AutograderTestCaseBaseTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.course = Course.objects.validate_and_create(name='eecs280')
        self.semester = Semester.objects.validate_and_create(
            name='f15', course=self.course)

        self.project = Project.objects.validate_and_create(
            name='my_project', semester=self.semester,
            required_student_files=['file1.cpp', 'file2.cpp'],
            expected_student_file_patterns=[
                Project.FilePatternTuple('test_*.cpp', 1, 2)])

        self.project.add_project_file(
            SimpleUploadedFile('spam.txt', b'hello there!'))

        self.assertTrue(self.project.has_file('spam.txt'))

        self.TEST_NAME = 'my_test'

    # -------------------------------------------------------------------------

    def test_valid_initialization_with_defaults(self):
        new_test_case = AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project)

        loaded_test_case = AutograderTestCaseBase.objects.get(
            name=self.TEST_NAME, project=self.project)

        self.assertEqual(new_test_case, loaded_test_case)
        self.assertEqual(self.TEST_NAME, loaded_test_case.name)
        self.assertEqual(self.project, loaded_test_case.project)

        self.assertEqual(loaded_test_case.hide_from_students, True)

        self.assertEqual(loaded_test_case.command_line_arguments, [])
        self.assertEqual(loaded_test_case.standard_input, "")
        self.assertEqual(loaded_test_case.test_resource_files, [])
        self.assertEqual(loaded_test_case.time_limit, 10)
        self.assertIsNone(loaded_test_case.expected_return_code)
        self.assertFalse(loaded_test_case.expect_any_nonzero_return_code)
        self.assertEqual("", loaded_test_case.expected_standard_output)
        self.assertEqual("", loaded_test_case.expected_standard_error_output)
        self.assertFalse(loaded_test_case.use_valgrind)
        self.assertIsNone(loaded_test_case.valgrind_flags)

        # Fat interface fields
        self.assertEqual(loaded_test_case.compiler, "")
        self.assertEqual(loaded_test_case.compiler_flags, [])
        self.assertEqual(loaded_test_case.files_to_compile_together, [])
        self.assertEqual(loaded_test_case.executable_name, "")

    # -------------------------------------------------------------------------

    def test_valid_initialization_custom_values(self):
        cmd_args = ['spam', '--eggs', '--sausage=spam', '-p', 'input.in']
        input_stream_content = "spameggsausagespam"
        out_stream_content = "standardspaminputspam"
        err_stream_content = "errorzspam"
        resource_files = ['spam.txt']
        time = 5
        ret_code = 0
        valgrind_flags = ['--leak-check=yes', '--error-exitcode=9000']

        new_test_case = AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project,
            hide_from_students=False,
            command_line_arguments=cmd_args,
            standard_input=input_stream_content,
            test_resource_files=resource_files,
            time_limit=time,
            expected_return_code=ret_code,
            expected_standard_output=out_stream_content,
            expected_standard_error_output=err_stream_content,
            use_valgrind=True,
            valgrind_flags=valgrind_flags,
        )

        loaded_test_case = AutograderTestCaseBase.objects.get(
            name=self.TEST_NAME, project=self.project)

        self.assertEqual(new_test_case, loaded_test_case)
        self.assertEqual(self.TEST_NAME, loaded_test_case.name)
        self.assertEqual(self.project, loaded_test_case.project)

        self.assertEqual(loaded_test_case.hide_from_students, False)

        self.assertEqual(
            loaded_test_case.command_line_arguments, cmd_args)

        self.assertEqual(
            loaded_test_case.standard_input,
            input_stream_content)

        self.assertEqual(
            loaded_test_case.test_resource_files, resource_files)

        self.assertEqual(loaded_test_case.time_limit, time)

        self.assertEqual(
            loaded_test_case.expected_return_code, ret_code)

        self.assertEqual(
            loaded_test_case.expected_standard_output,
            out_stream_content)

        self.assertEqual(
            loaded_test_case.expected_standard_error_output,
            err_stream_content)

        self.assertTrue(loaded_test_case.use_valgrind)

        self.assertEqual(loaded_test_case.valgrind_flags, valgrind_flags)

    # -------------------------------------------------------------------------

    def test_exception_on_non_unique_name_within_project(self):
        AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project)

        with self.assertRaises(ValidationError):
            AutograderTestCaseBase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project)

    def test_no_exception_same_name_different_project(self):
        other_project = Project.objects.validate_and_create(
            name='other_project', semester=self.semester)

        new_test_case = AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=other_project)

        loaded_test_case = AutograderTestCaseBase.objects.get(
            name=self.TEST_NAME, project=other_project)

        self.assertEqual(new_test_case, loaded_test_case)

    def test_no_exception_same_name_and_project_name_different_semester(self):
        other_semester = Semester.objects.validate_and_create(
            name='other_semester', course=self.course)

        other_project = Project.objects.validate_and_create(
            name=self.project.name, semester=other_semester)

        new_test_case = AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=other_project)

        loaded_test_case = AutograderTestCaseBase.objects.get(
            name=self.TEST_NAME, project=other_project)

        self.assertEqual(new_test_case, loaded_test_case)

    def test_no_exception_same_name_project_name_and_semester_name_different_course(self):
        other_course = Course.objects.validate_and_create(
            name='other_course')

        other_semester = Semester.objects.validate_and_create(
            name=self.semester.name, course=other_course)

        other_project = Project.objects.validate_and_create(
            name=self.project.name, semester=other_semester)

        new_test_case = AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=other_project)

        loaded_test_case = AutograderTestCaseBase.objects.get(
            name=self.TEST_NAME, project=other_project)

        self.assertEqual(new_test_case, loaded_test_case)

    def test_exception_on_empty_name(self):
        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseBase.objects.validate_and_create(
                name='', project=self.project)

        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_null_name(self):
        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseBase.objects.validate_and_create(
                name=None, project=self.project)

        self.assertTrue('name' in cm.exception.message_dict)

    def test_name_whitespace_stripped(self):
        name = 'test1'
        AutograderTestCaseBase.objects.validate_and_create(
            name='     ' + name + '  ', project=self.project)

        loaded_test_case = AutograderTestCaseBase.objects.get(
            name=name, project=self.project)

        self.assertEqual(name, loaded_test_case.name)

    def test_exception_on_name_only_whitespace(self):
        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseBase.objects.validate_and_create(
                name='     ', project=self.project)

        self.assertTrue('name' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_exception_on_null_command_line_args(self):
        with self.assertRaises(ValidationError):
            AutograderTestCaseBase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                command_line_arguments=None)

    def test_exception_on_empty_value_in_cmd_args(self):
        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseBase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                command_line_arguments=["spam", '', '       '])

        self.assertTrue('command_line_arguments' in cm.exception.message_dict)
        error_list = cm.exception.message_dict['command_line_arguments']
        self.assertFalse(error_list[0])
        self.assertTrue(error_list[1])
        self.assertTrue(error_list[2])

    def test_exception_on_invalid_chars_in_command_line_args(self):
        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseBase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                command_line_arguments=["spam", "; echo 'haxorz!'"])

        self.assertTrue('command_line_arguments' in cm.exception.message_dict)
        error_list = cm.exception.message_dict['command_line_arguments']
        self.assertFalse(error_list[0])
        self.assertTrue(error_list[1])

    def test_cmd_arg_whitespace_stripped(self):
        AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project,
            command_line_arguments=['  spam  ', 'eggs', '  sausage'])

        loaded_test = AutograderTestCaseBase.objects.get(
            name=self.TEST_NAME, project=self.project)

        self.assertEqual(
            loaded_test.command_line_arguments, ['spam', 'eggs', 'sausage'])

    # -------------------------------------------------------------------------

    def test_exception_on_null_test_resource_files_list(self):
        with self.assertRaises(ValidationError):
            AutograderTestCaseBase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                test_resource_files=None)

    def test_exception_on_test_resource_files_has_nonexistant_file(self):
        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseBase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                test_resource_files=['no_file.txt'])

        self.assertTrue('test_resource_files' in cm.exception.message_dict)
        error_list = cm.exception.message_dict['test_resource_files']
        self.assertTrue(error_list[0])

    # -------------------------------------------------------------------------

    def test_exception_on_zero_time_limit(self):
        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseBase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                time_limit=0)

        self.assertTrue('time_limit' in cm.exception.message_dict)

    def test_exception_on_negative_time_limit(self):
        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseBase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                time_limit=-1)

        self.assertTrue('time_limit' in cm.exception.message_dict)

    def test_exception_on_time_limit_not_integer(self):
        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseBase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                time_limit='spam')

        self.assertTrue('time_limit' in cm.exception.message_dict)

    def test_no_exception_on_time_limit_is_parseable_int(self):
        AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project,
            time_limit='2')

        loaded_test = AutograderTestCaseBase.objects.get(
            name=self.TEST_NAME, project=self.project)
        self.assertEqual(loaded_test.time_limit, 2)

    # -------------------------------------------------------------------------

    def test_nonzero_expected_return_code(self):
        AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project,
            expect_any_nonzero_return_code=True)

        loaded_test_case = AutograderTestCaseBase.objects.get(
            name=self.TEST_NAME, project=self.project)

        self.assertTrue(loaded_test_case.expect_any_nonzero_return_code)

    def test_exception_on_expected_return_code_not_integer(self):
        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseBase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                expected_return_code='spam')

        self.assertTrue('expected_return_code' in cm.exception.message_dict)

    def test_no_exception_on_expected_return_code_is_parseable_int(self):
        AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project,
            expected_return_code='2')

        loaded_test = AutograderTestCaseBase.objects.get(
            name=self.TEST_NAME, project=self.project)
        self.assertEqual(loaded_test.expected_return_code, 2)

    # -------------------------------------------------------------------------

    def test_exception_on_use_valgrind_with_null_flags(self):
        ag_test = AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project,
            use_valgrind=True)

        ag_test.valgrind_flags = None

        with self.assertRaises(ValidationError):
            ag_test.validate_and_save()

    def test_exception_on_empty_value_in_valgrind_args(self):
        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseBase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                use_valgrind=True,
                valgrind_flags=['', 'spam', '     '])

        self.assertTrue('valgrind_flags' in cm.exception.message_dict)
        error_list = cm.exception.message_dict['valgrind_flags']
        self.assertTrue(error_list[0])
        self.assertFalse(error_list[1])
        self.assertTrue(error_list[2])

    def test_use_valgrind_default_flags(self):
        AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project,
            use_valgrind=True)

        loaded_test_case = AutograderTestCaseBase.objects.get(
            name=self.TEST_NAME, project=self.project)

        self.assertTrue(loaded_test_case.use_valgrind)
        self.assertEqual(
            loaded_test_case.valgrind_flags,
            gc.DEFAULT_VALGRIND_FLAGS_WHEN_USED)

    def test_exception_on_invalid_chars_in_valgrind_flags(self):
        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseBase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                use_valgrind=True,
                valgrind_flags=["; echo 'haxorz!'", '--leak-check=full'])

        self.assertTrue('valgrind_flags' in cm.exception.message_dict)
        error_list = cm.exception.message_dict['valgrind_flags']
        self.assertTrue(error_list[0])
        self.assertFalse(error_list[1])

    def test_valgrind_flag_whitespace_stripped(self):
        AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project,
            use_valgrind=True,
            valgrind_flags=["      spam    ", '   eggs'])

        loaded_test = AutograderTestCaseBase.objects.get(
            name=self.TEST_NAME, project=self.project)
        self.assertEqual(loaded_test.valgrind_flags, ['spam', 'eggs'])


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class CompiledAutograderTestCaseTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        course = Course.objects.validate_and_create(name='eecs280')
        semester = Semester.objects.validate_and_create(
            name='f15', course=course)

        self.project = Project.objects.validate_and_create(
            name='my_project', semester=semester,
            required_student_files=['file1.cpp', 'file2.cpp'],
            expected_student_file_patterns=[
                Project.FilePatternTuple('test_*.cpp', 1, 2)])

        self.project_files = [
            SimpleUploadedFile('spam.txt', b'hello there!'),
            SimpleUploadedFile('eggs.cpp', b'egg bacon spam and sausage'),
            SimpleUploadedFile('sausage.cpp', b'spam egg sausage and spam')
        ]

        for file_obj in self.project_files:
            self.project.add_project_file(file_obj)

        self.TEST_NAME = 'my_test'

        self.compiler = 'g++'
        self.compiler_flags = ['--foo_arg=bar', '-s']

        self.files_to_compile_together = [
            file_obj.name for file_obj in self.project_files
        ]
        self.files_to_compile_together.append('file1.cpp')  # required file
        self.files_to_compile_together.append('test_*.cpp')  # expected pattern

        self.executable_name = "sausage.exe"

        self.compiled_test_kwargs = {
            "compiler": self.compiler,
            "compiler_flags": self.compiler_flags,
            "files_to_compile_together": self.files_to_compile_together,
            "executable_name": self.executable_name,
        }

    # -------------------------------------------------------------------------

    def test_valid_create_custom_values(self):
        CompiledAutograderTestCase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project,
            **self.compiled_test_kwargs)

        loaded_test = CompiledAutograderTestCase.objects.get(
            name=self.TEST_NAME, project=self.project)

        self.assertEqual(self.compiler, loaded_test.compiler)
        self.assertEqual(self.compiler_flags, loaded_test.compiler_flags)
        self.assertEqual(
            self.files_to_compile_together,
            loaded_test.files_to_compile_together)
        self.assertEqual(self.executable_name, loaded_test.executable_name)

    def test_exception_on_empty_compiler(self):
        self.compiled_test_kwargs['compiler'] = ''

        with self.assertRaises(ValidationError) as cm:
            CompiledAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('compiler' in cm.exception.message_dict)

    def test_exception_on_null_compiler(self):
        self.compiled_test_kwargs['compiler'] = None

        with self.assertRaises(ValidationError) as cm:
            CompiledAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('compiler' in cm.exception.message_dict)

    def test_exception_on_unsupported_compiler(self):
        self.compiled_test_kwargs['compiler'] = 'spamcompiler++'

        with self.assertRaises(ValidationError) as cm:
            CompiledAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('compiler' in cm.exception.message_dict)

    def test_exception_on_invalid_compiler_flag_values(self):
        self.compiled_test_kwargs['compiler_flags'] = [
            '; echo "haxorz!#', '', '       ']

        with self.assertRaises(ValidationError) as cm:
            CompiledAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('compiler_flags' in cm.exception.message_dict)
        error_list = cm.exception.message_dict['compiler_flags']
        self.assertTrue(error_list[0])
        self.assertTrue(error_list[1])
        self.assertTrue(error_list[2])

    def test_compiler_flag_whitespace_stripped(self):
        self.compiled_test_kwargs['compiler_flags'] = [
            '     spam    ', '   egg  ']

        CompiledAutograderTestCase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project,
            **self.compiled_test_kwargs)

        loaded_test = CompiledAutograderTestCase.objects.get(
            name=self.TEST_NAME, project=self.project)
        self.assertEqual(loaded_test.compiler_flags, ['spam', 'egg'])

    # -------------------------------------------------------------------------

    def test_exception_on_empty_files_to_compile_together(self):
        self.compiled_test_kwargs['files_to_compile_together'] = []

        with self.assertRaises(ValidationError) as cm:
            CompiledAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue(
            'files_to_compile_together' in cm.exception.message_dict)

    def test_exception_on_null_files_to_compile_together(self):
        self.compiled_test_kwargs['files_to_compile_together'] = None

        with self.assertRaises(ValidationError) as cm:
            CompiledAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue(
            'files_to_compile_together' in cm.exception.message_dict)

    def test_exception_on_nonexistant_files_to_compile_together(self):
        self.compiled_test_kwargs['files_to_compile_together'].append('')

        with self.assertRaises(ValidationError) as cm:
            CompiledAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue(
            'files_to_compile_together' in cm.exception.message_dict)

        self.compiled_test_kwargs['files_to_compile_together'][-1] = None

        with self.assertRaises(ValidationError) as cm:
            CompiledAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue(
            'files_to_compile_together' in cm.exception.message_dict)

        self.compiled_test_kwargs['files_to_compile_together'][-1] = (
            'nonexistant_file.txt')

        with self.assertRaises(ValidationError) as cm:
            CompiledAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue(
            'files_to_compile_together' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_exception_on_empty_executable_name(self):
        self.compiled_test_kwargs['executable_name'] = ''

        with self.assertRaises(ValidationError) as cm:
            CompiledAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('executable_name' in cm.exception.message_dict)

    def test_exception_on_null_executable_name(self):
        self.compiled_test_kwargs['executable_name'] = None

        with self.assertRaises(ValidationError) as cm:
            CompiledAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('executable_name' in cm.exception.message_dict)

    def test_exception_on_invalid_chars_in_executable_name(self):
        self.compiled_test_kwargs['executable_name'] = "../haxorz"

        with self.assertRaises(ValidationError) as cm:
            CompiledAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('executable_name' in cm.exception.message_dict)

    def test_executable_name_whitespace_stripped(self):
        self.compiled_test_kwargs['executable_name'] = "   spam.exe   "

        CompiledAutograderTestCase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project,
            **self.compiled_test_kwargs)

        loaded_test = CompiledAutograderTestCase.objects.get(
            name=self.TEST_NAME, project=self.project)
        self.assertEqual(loaded_test.executable_name, 'spam.exe')

    def test_exception_on_executable_name_only_whitespace(self):
        self.compiled_test_kwargs['executable_name'] = "     "

        with self.assertRaises(ValidationError) as cm:
            CompiledAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('executable_name' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_validation_error_contains_base_and_derived_error_messages(self):
        self.compiled_test_kwargs['executable_name'] = ''

        with self.assertRaises(ValidationError) as cm:
            CompiledAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                time_limit='spam',
                **self.compiled_test_kwargs)

        self.assertTrue('time_limit' in cm.exception.message_dict)
        self.assertTrue('executable_name' in cm.exception.message_dict)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class CompiledAutograderTestRunTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.original_dir = os.getcwd()
        self.new_dir = os.path.join(settings.MEDIA_ROOT, 'working_dir')
        os.mkdir(self.new_dir)
        os.chdir(self.new_dir)

        self.course = Course.objects.validate_and_create(name='eecs280')
        self.semester = Semester.objects.validate_and_create(
            name='f15', course=self.course)

        self.project = Project.objects.validate_and_create(
            name='my_project', semester=self.semester)

        self.cpp_filename = 'main.cpp'
        self.executable_name = 'program.exe'

        # We'll be writing the file manually for these tests, so the
        # "real" file in the project directory doesn't really matter.
        self.project.add_project_file(
            SimpleUploadedFile(self.cpp_filename, b''))

        self.test_case_starter = CompiledAutograderTestCase(
            name='test1', project=self.project,
            compiler='g++',
            compiler_flags=['-Wall', '-pedantic'],
            files_to_compile_together=[self.cpp_filename],
            executable_name=self.executable_name
        )

    # -------------------------------------------------------------------------

    def tearDown(self):
        super().tearDown()

        os.chdir(self.original_dir)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def test_run_correct_standard_output(self):
        stdout_content = "hello world"
        cpp_file_content = _CPP_PROGRAM_PRINT_TO_STDOUT_TEMPLATE.format(
            stdout_content)
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        self.test_case_starter.expected_standard_output = (
            stdout_content)
        self.test_case_starter.save()

        result = self.test_case_starter.run()

        self.assertEqual(result.standard_output, stdout_content)
        self.assertTrue(result.standard_output_correct)

    # -------------------------------------------------------------------------

    def test_run_incorrect_standard_output(self):
        cpp_file_content = _CPP_PROGRAM_PRINT_TO_STDOUT_TEMPLATE.format(
            "wrong message")
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        expected_stdout_content = "hello world"
        self.test_case_starter.expected_standard_output = (
            expected_stdout_content)
        self.test_case_starter.save()

        result = self.test_case_starter.run()

        self.assertNotEqual(result.standard_output, expected_stdout_content)
        self.assertFalse(result.standard_output_correct)

    # -------------------------------------------------------------------------

    def test_run_correct_standard_error_output(self):
        stderr_content = "hello world"
        cpp_file_content = _CPP_PROGRAM_PRINT_TO_STDERR_TEMPLATE.format(
            stderr_content)
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        self.test_case_starter.expected_standard_error_output = (
            stderr_content)
        self.test_case_starter.save()

        result = self.test_case_starter.run()

        self.assertEqual(result.standard_error_output, stderr_content)
        self.assertTrue(result.standard_error_output_correct)

    # -------------------------------------------------------------------------

    def test_run_incorrect_standard_error_output(self):
        cpp_file_content = _CPP_PROGRAM_PRINT_TO_STDERR_TEMPLATE.format(
            "wrong output")
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        expected_stderr_content = "hello world"
        self.test_case_starter.expected_standard_error_output = (
            expected_stderr_content)
        self.test_case_starter.save()

        result = self.test_case_starter.run()

        self.assertNotEqual(
            result.standard_error_output, expected_stderr_content)
        self.assertFalse(result.standard_error_output_correct)

    # -------------------------------------------------------------------------

    def test_run_correct_exact_return_code(self):
        expected_return_code = 0
        cpp_file_content = _CPP_PROGRAM_RETURN_ONLY_TEMPLATE.format(
            expected_return_code)
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        self.test_case_starter.expected_return_code = expected_return_code
        self.test_case_starter.save()

        result = self.test_case_starter.run()

        self.assertEqual(expected_return_code, result.return_code)
        self.assertTrue(result.return_code_correct)

    # -------------------------------------------------------------------------

    def test_run_incorrect_exact_return_code(self):
        cpp_file_content = _CPP_PROGRAM_RETURN_ONLY_TEMPLATE.format(42)
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        expected_return_code = 0
        self.test_case_starter.expected_return_code = expected_return_code
        self.test_case_starter.save()

        result = self.test_case_starter.run()

        self.assertNotEqual(expected_return_code, result.return_code)
        self.assertFalse(result.return_code_correct)

    # -------------------------------------------------------------------------

    def test_run_correct_nonzero_return_code(self):
        cpp_file_content = _CPP_PROGRAM_RETURN_ONLY_TEMPLATE.format(42)
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        self.test_case_starter.expect_any_nonzero_return_code = True
        self.test_case_starter.save()

        result = self.test_case_starter.run()

        self.assertNotEqual(0, result.return_code)
        self.assertTrue(result.return_code_correct)

    # -------------------------------------------------------------------------

    def test_run_incorrect_nonzero_return_code(self):
        cpp_file_content = _CPP_PROGRAM_RETURN_ONLY_TEMPLATE.format(0)
        with open(self.cpp_filename, 'w') as f:
            f.write(cpp_file_content)

        self.test_case_starter.expect_any_nonzero_return_code = True
        self.test_case_starter.save()

        result = self.test_case_starter.run()

        self.assertEqual(0, result.return_code)
        self.assertFalse(result.return_code_correct)

    # -------------------------------------------------------------------------

    def test_run_with_cmd_line_args(self):
        cmd_args = ['spam', 'egg', 'sausage']
        with open(self.cpp_filename, 'w') as f:
            f.write(_CPP_PROGRAM_PRINT_CMD_ARGS)

        expected_output = ' '.join(cmd_args)

        self.test_case_starter.command_line_arguments = cmd_args
        self.test_case_starter.expected_standard_output = expected_output
        self.test_case_starter.save()

        result = self.test_case_starter.run()

        self.assertEqual(expected_output, result.standard_output)
        self.assertTrue(result.standard_output_correct)

    # -------------------------------------------------------------------------

    def test_run_with_stdin_contents(self):
        with open(self.cpp_filename, 'w') as f:
            f.write(_CPP_PROGRAM_PRINT_STDIN_CONTENT)

        expected_output = "egg bacon spam and sausage "

        self.test_case_starter.standard_input = expected_output
        self.test_case_starter.expected_standard_output = expected_output
        self.test_case_starter.save()

        result = self.test_case_starter.run()

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
            f.write(_CPP_PROGRAM_PRINT_FILE_CONTENT)

        self.test_case_starter.expected_standard_output = expected_output
        self.test_case_starter.save()

        result = self.test_case_starter.run()

        self.assertEqual(expected_output, result.standard_output)
        self.assertTrue(result.standard_output_correct)

    # -------------------------------------------------------------------------

    def test_run_with_timeout(self):
        with open(self.cpp_filename, 'w') as f:
            f.write(_CPP_INFINITE_LOOP_PROGRAM)

        self.test_case_starter.time_limit = 1
        self.test_case_starter.save()

        result = self.test_case_starter.run()

        self.assertTrue(result.timed_out)
        self.assertNotEqual(result.return_code, 0)

    # -------------------------------------------------------------------------

    def test_run_with_valgrind_no_errors(self):
        with open(self.cpp_filename, 'w') as f:
            f.write(_CPP_PROGRAM_RETURN_ONLY_TEMPLATE.format(0))

        self.test_case_starter.use_valgrind = True
        self.test_case_starter.save()

        result = self.test_case_starter.run()

        self.assertEqual(result.valgrind_return_code, 0)

        # We won't be checking exact valgrind output, but we want
        # to make sure that the output was still recorded.
        self.assertNotEqual(result.valgrind_output, '')
        self.assertFalse(result.valgrind_errors_present)

    # -------------------------------------------------------------------------

    def test_run_with_valgrind_with_errors(self):
        with open(self.cpp_filename, 'w') as f:
            f.write(_CPP_MEMORY_LEAK_PROGRAM)

        self.test_case_starter.use_valgrind = True
        self.test_case_starter.save()

        result = self.test_case_starter.run()

        self.assertNotEqual(result.valgrind_return_code, 0)

        self.assertNotEqual(result.valgrind_output, '')
        self.assertTrue(result.valgrind_errors_present)

    # -------------------------------------------------------------------------

    def test_run_compile_error(self):
        with open(self.cpp_filename, 'w') as f:
            f.write(_CPP_COMPILE_ERROR_PROGRAM)

        self.test_case_starter.save()

        result = self.test_case_starter.run()

        self.assertNotEqual(result.compilation_return_code, 0)
        self.assertNotEqual(result.compilation_standard_error_output, '')
        self.assertFalse(result.compilation_succeeded)

    # -------------------------------------------------------------------------

    def test_run_everything_correct(self):
        stdout_msg = 'standard spam output'
        stderr_msg = 'standard llama error output'
        cpp_file_content = _CPP_PROGRAM_DO_EVERYTHING.format(
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
        result = self.test_case_starter.run()

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
        cpp_file_content = _CPP_PROGRAM_DO_EVERYTHING.format(
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
        result = self.test_case_starter.run()

        self.assertNotEqual(expected_stdout, result.standard_output)
        self.assertFalse(result.standard_output_correct)

        self.assertNotEqual('stderr_msg', result.standard_error_output)
        self.assertFalse(result.standard_error_output_correct)

        self.assertNotEqual(0, result.return_code)
        self.assertFalse(result.return_code_correct)

        self.assertNotEqual(0, result.valgrind_return_code)
        self.assertTrue(result.valgrind_errors_present)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

_CPP_PROGRAM_PRINT_TO_STDOUT_TEMPLATE = r"""#include <iostream>

using namespace std;

int main()
{{
    cout << "{}" << flush;
    return 0;
}}
"""

_CPP_PROGRAM_PRINT_TO_STDERR_TEMPLATE = """#include <iostream>

using namespace std;

int main()
{{
    cerr << "{}" << flush;
    return 0;
}}
"""

_CPP_PROGRAM_RETURN_ONLY_TEMPLATE = """
int main()
{{
    return {};
}}
"""

_CPP_PROGRAM_PRINT_CMD_ARGS = """#include <iostream>

using namespace std;

int main(int argc, char** argv)
{{
    for (int i = 1; i < argc - 1; ++i)
    {{
        cout << argv[i] << " ";
    }}
    cout << argv[argc - 1] << flush;

    return 0;
}}
"""

_CPP_PROGRAM_PRINT_STDIN_CONTENT = """#include <iostream>
#include <string>

using namespace std;

int main()
{{
    string spam;
    while (cin >> spam)
    {{
        cout << spam << ' ' << flush;
    }}

    return 0;
}}
"""

_CPP_PROGRAM_PRINT_FILE_CONTENT = """#include <iostream>
#include <fstream>
#include <string>

using namespace std;

int main()
{{
    string spam;
    ifstream ifs("input.in");
    while (ifs >> spam)
    {{
        cout << spam << ' ' << flush;
    }}

    return 0;
}}
"""

_CPP_INFINITE_LOOP_PROGRAM = """int main()
{{
    while (true);
    return 0;
}}
"""

_CPP_MEMORY_LEAK_PROGRAM = """int main()
{{
    new int(42);
    return 0;
}}
"""

_CPP_COMPILE_ERROR_PROGRAM = """int main()
{{
    spameggsausagespam
}}
"""

_CPP_PROGRAM_DO_EVERYTHING = """#include <iostream>
#include <fstream>
#include <string>

using namespace std;

int main(int argc, char** argv)
{{
    for (int i = 1; i < argc - 1; ++i)
    {{
        cout << argv[i] << " ";
    }}
    cout << argv[argc - 1] << flush;

    string spam;
    ifstream ifs("input.in");
    while (ifs >> spam)
    {{
        cout << spam << ' ' << flush;
    }}

    while (cin >> spam)
    {{
        cout << spam << ' ' << flush;
    }}

    cout << "{stdout_str}" << flush;
    cerr << "{stderr_str}" << flush;

    return {return_code};
}}
"""
