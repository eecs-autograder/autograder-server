from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from autograder.core.models import (
    Project, Semester, Course)


import unittest

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from autograder.core.tests.test_models.test_autograder_test_case.models import (
    _DummyCompiledAutograderTestCase)


class CompiledAutograderTestCaseTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        course = Course.objects.validate_and_create(name='eecs280')
        semester = Semester.objects.validate_and_create(
            name='f15', course=course)

        self.required_student_files = ['file1.cpp', 'file2.cpp']
        self.project = Project.objects.validate_and_create(
            name='my_project', semester=semester,
            required_student_files=self.required_student_files,
            expected_student_file_patterns=[
                Project.FilePatternTuple('test_*.cpp', 1, 2),
                Project.FilePatternTuple('funsy[0-9].cpp', 0, 2)])

        self.project_files = [
            SimpleUploadedFile('spam.txt', b'hello there!'),
            SimpleUploadedFile('eggs.cpp', b'egg bacon spam and sausage'),
            SimpleUploadedFile('sausage.cpp', b'spam egg sausage and spam')
        ]

        for file_obj in self.project_files:
            self.project.add_project_file(file_obj)

        self.test_name = 'my_test'

        self.compiler = 'g++'
        self.compiler_flags = ['--foo_arg=bar', '-s']

        self.project_files_to_compile_together = [
            'spam.txt'
        ]
        self.student_files_to_compile_together = [
            'file1.cpp',  # required student file
            'test_*.cpp'  # expected student pattern
        ]
        self.executable_name = "sausage.exe"

        self.compiled_test_kwargs = {
            "test_resource_files": ['spam.txt'],
            "student_resource_files": ['file1.cpp', 'test_*.cpp'],
            "compiler": self.compiler,
            "compiler_flags": self.compiler_flags,
            "project_files_to_compile_together": self.project_files_to_compile_together,
            "student_files_to_compile_together": self.student_files_to_compile_together,
            "executable_name": self.executable_name,
        }

    # -------------------------------------------------------------------------

    def test_valid_init_with_defaults(self):
        test = _DummyCompiledAutograderTestCase.objects.validate_and_create(
            name=self.test_name, project=self.project,
            compiler=self.compiler,
            project_files_to_compile_together=self.project_files_to_compile_together,
            student_files_to_compile_together=self.student_files_to_compile_together,
            test_resource_files=self.compiled_test_kwargs.get(
                'test_resource_files'),
            student_resource_files=self.compiled_test_kwargs.get(
                'student_resource_files')
        )

        loaded_test_case = _DummyCompiledAutograderTestCase.objects.get(
            pk=test.pk)

        self.assertEqual(loaded_test_case.compiler, self.compiler)
        self.assertEqual(loaded_test_case.compiler_flags, [])
        self.assertEqual(
            loaded_test_case.project_files_to_compile_together,
            self.project_files_to_compile_together)
        self.assertEqual(
            loaded_test_case.student_files_to_compile_together,
            self.student_files_to_compile_together)
        self.assertEqual(loaded_test_case.executable_name, "compiled_program")

    def test_valid_init_no_defaults(self):
        test = _DummyCompiledAutograderTestCase.objects.validate_and_create(
            name=self.test_name, project=self.project,
            **self.compiled_test_kwargs)

        loaded_test_case = _DummyCompiledAutograderTestCase.objects.get(
            pk=test.pk)

        self.assertEqual(loaded_test_case.compiler, self.compiler)
        self.assertEqual(loaded_test_case.compiler_flags, self.compiler_flags)
        self.assertEqual(
            loaded_test_case.project_files_to_compile_together,
            self.project_files_to_compile_together)
        self.assertEqual(
            loaded_test_case.student_files_to_compile_together,
            self.student_files_to_compile_together)
        self.assertEqual(
            loaded_test_case.executable_name, self.executable_name)

    def test_exception_on_missing_compiler(self):
        self.compiled_test_kwargs.pop('compiler', None)

        with self.assertRaises(ValidationError) as cm:
            _DummyCompiledAutograderTestCase.objects.validate_and_create(
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('compiler' in cm.exception.message_dict)

    def test_exception_on_empty_compiler(self):
        self.compiled_test_kwargs['compiler'] = ''

        with self.assertRaises(ValidationError) as cm:
            _DummyCompiledAutograderTestCase.objects.validate_and_create(
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('compiler' in cm.exception.message_dict)

    def test_exception_on_null_compiler(self):
        self.compiled_test_kwargs['compiler'] = None

        with self.assertRaises(ValidationError) as cm:
            _DummyCompiledAutograderTestCase.objects.validate_and_create(
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('compiler' in cm.exception.message_dict)

    def test_exception_on_unsupported_compiler(self):
        self.compiled_test_kwargs['compiler'] = 'spamcompiler++'

        with self.assertRaises(ValidationError) as cm:
            _DummyCompiledAutograderTestCase.objects.validate_and_create(
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('compiler' in cm.exception.message_dict)

    def test_exception_on_invalid_compiler_flag_values(self):
        self.compiled_test_kwargs['compiler_flags'] = [
            '; echo "haxorz!"#', '', '       ']

        with self.assertRaises(ValidationError) as cm:
            _DummyCompiledAutograderTestCase.objects.validate_and_create(
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('compiler_flags' in cm.exception.message_dict)
        error_list = cm.exception.message_dict['compiler_flags']
        self.assertTrue(error_list[0])
        self.assertTrue(error_list[1])
        self.assertTrue(error_list[2])

    def test_compiler_flag_whitespace_stripped(self):
        self.compiled_test_kwargs['compiler_flags'] = [
            '     spam    ', '   egg  ']

        _DummyCompiledAutograderTestCase.objects.validate_and_create(
            name=self.test_name, project=self.project,
            **self.compiled_test_kwargs)

        loaded_test = _DummyCompiledAutograderTestCase.objects.get(
            name=self.test_name, project=self.project)
        self.assertEqual(loaded_test.compiler_flags, ['spam', 'egg'])

    # -------------------------------------------------------------------------

    # def test_exception_on_missing_files_to_compile_together(self):
    #     self.compiled_test_kwargs.pop('files_to_compile_together', None)

    #     with self.assertRaises(ValidationError) as cm:
    #         _DummyCompiledAutograderTestCase.objects.validate_and_create(
    #             name=self.test_name, project=self.project,
    #             **self.compiled_test_kwargs)

    #     self.assertTrue(
    #         'files_to_compile_together' in cm.exception.message_dict)

    # def test_exception_on_empty_files_to_compile_together(self):
    #     self.compiled_test_kwargs['files_to_compile_together'] = []

    #     with self.assertRaises(ValidationError) as cm:
    #         _DummyCompiledAutograderTestCase.objects.validate_and_create(
    #             name=self.test_name, project=self.project,
    #             **self.compiled_test_kwargs)

    #     self.assertTrue(
    #         'files_to_compile_together' in cm.exception.message_dict)

    # def test_exception_on_null_files_to_compile_together(self):
    #     self.compiled_test_kwargs['files_to_compile_together'] = None

    #     with self.assertRaises(ValidationError) as cm:
    #         _DummyCompiledAutograderTestCase.objects.validate_and_create(
    #             name=self.test_name, project=self.project,
    #             **self.compiled_test_kwargs)

    #     self.assertTrue(
    #         'files_to_compile_together' in cm.exception.message_dict)

    def test_exception_on_empty_name_in_files_to_compile_together(self):
        self.compiled_test_kwargs[
            'project_files_to_compile_together'].append('')
        self.compiled_test_kwargs[
            'student_files_to_compile_together'].append('')

        with self.assertRaises(ValidationError) as cm:
            _DummyCompiledAutograderTestCase.objects.validate_and_create(
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue(
            'project_files_to_compile_together' in cm.exception.message_dict)
        self.assertTrue(
            'student_files_to_compile_together' in cm.exception.message_dict)

    def test_exception_on_None_in_files_to_compile_together(self):
        self.compiled_test_kwargs[
            'project_files_to_compile_together'].append(None)
        self.compiled_test_kwargs[
            'student_files_to_compile_together'].append(None)

        with self.assertRaises(ValidationError) as cm:
            _DummyCompiledAutograderTestCase.objects.validate_and_create(
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue(
            'project_files_to_compile_together' in cm.exception.message_dict)
        self.assertTrue(
            'student_files_to_compile_together' in cm.exception.message_dict)

    def test_exception_on_nonexistant_name_in_files_to_compile_together(self):
        self.compiled_test_kwargs['project_files_to_compile_together'].append(
            'nonexistant_file.txt')
        self.compiled_test_kwargs['student_files_to_compile_together'].append(
            'nonexistant_file.txt')

        with self.assertRaises(ValidationError) as cm:
            _DummyCompiledAutograderTestCase.objects.validate_and_create(
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue(
            'project_files_to_compile_together' in cm.exception.message_dict)
        self.assertTrue(
            'student_files_to_compile_together' in cm.exception.message_dict)

    def test_exception_on_non_test_resource_project_file_to_compile_together(self):
        assert 'eggs.cpp' in self.project.get_project_file_basenames()

        self.compiled_test_kwargs['project_files_to_compile_together'].append(
            'eggs.cpp')  # Project file, but not in test_resource_files

        with self.assertRaises(ValidationError) as cm:
            _DummyCompiledAutograderTestCase.objects.validate_and_create(
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue(
            'project_files_to_compile_together' in cm.exception.message_dict)

    def test_exception_on_non_student_resource_file_to_compile_together(self):
        assert 'file2.cpp' in self.project.required_student_files

        self.compiled_test_kwargs['student_files_to_compile_together'].append(
            'file2.cpp')

        with self.assertRaises(ValidationError) as cm:
            _DummyCompiledAutograderTestCase.objects.validate_and_create(
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue(
            'student_files_to_compile_together' in cm.exception.message_dict)

    def test_exception_on_non_student_resource_pattern_to_compile_together(self):
        assert 'funsy[0-9].cpp' in [
            pat_obj.pattern for pat_obj in
            self.project.expected_student_file_patterns]

        self.compiled_test_kwargs['student_files_to_compile_together'].append(
            'funsy[0-9].cpp')

        with self.assertRaises(ValidationError) as cm:
            _DummyCompiledAutograderTestCase.objects.validate_and_create(
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue(
            'student_files_to_compile_together' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_validation_error_contains_base_and_derived_error_messages(self):
        self.compiled_test_kwargs['compiler'] = 'unsupported_compiler'

        with self.assertRaises(ValidationError) as cm:
            _DummyCompiledAutograderTestCase.objects.validate_and_create(
                name=self.test_name, project=self.project,
                time_limit='spam',
                **self.compiled_test_kwargs)

        self.assertTrue('time_limit' in cm.exception.message_dict)
        self.assertTrue('compiler' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_test_checks_compilation(self):
        test = _DummyCompiledAutograderTestCase.objects.validate_and_create(
            name=self.test_name, project=self.project,
            **self.compiled_test_kwargs)

        self.assertTrue(test.test_checks_compilation())
