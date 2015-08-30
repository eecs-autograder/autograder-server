from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from autograder.models import (
    Project, Semester, Course, AutograderTestCaseBase)

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
        self.assertEqual(loaded_test_case.student_resource_files, [])
        self.assertEqual(loaded_test_case.time_limit, 10)
        self.assertIsNone(loaded_test_case.expected_return_code)
        self.assertFalse(loaded_test_case.expect_any_nonzero_return_code)
        self.assertEqual("", loaded_test_case.expected_standard_output)
        self.assertEqual("", loaded_test_case.expected_standard_error_output)
        self.assertFalse(loaded_test_case.use_valgrind)
        self.assertIsNone(loaded_test_case.valgrind_flags)

        self.assertEqual(0, loaded_test_case.points_for_correct_return_code)
        self.assertEqual(0, loaded_test_case.points_for_correct_output)
        self.assertEqual(0, loaded_test_case.points_for_no_valgrind_errors)
        self.assertEqual(0, loaded_test_case.points_for_compilation_success)

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
        project_resource_files = ['spam.txt']
        student_resource_files = ['file1.cpp', 'file2.cpp']
        time = 5
        ret_code = 0
        valgrind_flags = ['--leak-check=yes', '--error-exitcode=9000']

        new_test_case = AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project,
            hide_from_students=False,
            command_line_arguments=cmd_args,
            standard_input=input_stream_content,
            test_resource_files=project_resource_files,
            student_resource_files=student_resource_files,
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
            loaded_test_case.test_resource_files, project_resource_files)

        self.assertEqual(
            loaded_test_case.student_resource_files, student_resource_files)

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

    # Note: Filenames in test_resource_files and student_resource_files
    # are restricted to filenames validated by a Project. Therefore we
    # can assume that the only legal choices for those fields have
    # valid filenames.

    def test_exception_on_null_test_resource_files_list(self):
        with self.assertRaises(ValidationError):
            AutograderTestCaseBase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                test_resource_files=None)

    def test_exception_on_test_resource_files_has_wrong_file(self):
        # student_file.txt is a student file, not a project file
        self.project.required_student_files.append('student_file.txt')
        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseBase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                test_resource_files=['student_file.txt'])

        self.assertTrue('test_resource_files' in cm.exception.message_dict)
        error_list = cm.exception.message_dict['test_resource_files']
        self.assertTrue(error_list[0])

    def test_exception_on_null_student_resource_files_list(self):
        with self.assertRaises(ValidationError):
            AutograderTestCaseBase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                student_resource_files=None)

    def test_exception_on_student_resource_files_has_wrong_file(self):
        # spam.txt is a project file, not a student file
        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseBase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                student_resource_files=['spam.txt'])

        self.assertTrue('student_resource_files' in cm.exception.message_dict)
        error_list = cm.exception.message_dict['student_resource_files']
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

    # -------------------------------------------------------------------------

    def test_exception_on_negative_point_distributions(self):
        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseBase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                points_for_correct_return_code=-1,
                points_for_correct_output=-1,
                points_for_no_valgrind_errors=-1,
                points_for_compilation_success=-1)

        self.assertTrue(
            'points_for_correct_return_code' in cm.exception.message_dict)
        self.assertTrue(
            'points_for_correct_output' in cm.exception.message_dict)
        self.assertTrue(
            'points_for_no_valgrind_errors' in cm.exception.message_dict)
        self.assertTrue(
            'points_for_compilation_success' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_test_checks_return_code(self):
        test = AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project)
        self.assertFalse(test.test_checks_return_code())

        test.expect_any_nonzero_return_code = True
        self.assertTrue(test.test_checks_return_code())

        test.expect_any_nonzero_return_code = False
        self.assertFalse(test.test_checks_return_code())

        test.expected_return_code = 0
        self.assertTrue(test.test_checks_return_code())

    def test_test_checks_output(self):
        test = AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project)

        self.assertFalse(test.test_checks_output())

        test.expected_standard_output = 'spam'
        test.validate_and_save()
        self.assertTrue(test.test_checks_output())

        test.expected_standard_output = ''
        test.validate_and_save()
        self.assertFalse(test.test_checks_output())

        test.expected_standard_error_output = 'eggs'
        test.validate_and_save()
        self.assertTrue(test.test_checks_output())

        test.expected_standard_output = 'spam'
        test.validate_and_save()
        self.assertTrue(test.test_checks_output())

        test.expected_standard_output = ''
        test.expected_standard_error_output = ''
        test.validate_and_save()
        self.assertFalse(test.test_checks_output())

    def test_test_checks_compilation(self):
        test = AutograderTestCaseBase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project)

        self.assertFalse(test.test_checks_compilation())

        test.compiler = 'g++'
        self.assertTrue(test.test_checks_compilation())
