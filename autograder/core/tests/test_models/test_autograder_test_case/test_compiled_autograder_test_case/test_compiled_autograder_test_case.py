import itertools

from django.core.exceptions import ValidationError

from django.core.files.uploadedfile import SimpleUploadedFile

import autograder.core.models as ag_models

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.core.tests.dummy_object_utils as obj_ut
from ..models import _DummyCompiledAutograderTestCase


class CompiledAutograderTestCaseTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.project = obj_ut.build_project()

        self.test_name = 'my_test'

        self.compiler = 'g++'
        self.compiler_flags = ['--foo_arg=bar', '-s']

        self.executable_name = "sausage.exe"

        self.compiled_test_kwargs = {
            "compiler": self.compiler,
            "compiler_flags": self.compiler_flags,
            "executable_name": self.executable_name,
        }

    def test_valid_create_with_defaults(self):
        test = _DummyCompiledAutograderTestCase.objects.validate_and_create(
            name=self.test_name, project=self.project,
            compiler=self.compiler,
        )

        test.refresh_from_db()

        self.assertEqual(test.compiler, self.compiler)
        self.assertEqual(test.compiler_flags, [])
        self.assertNotEqual(test.executable_name, '')
        self.assertRegex(test.executable_name, 'prog-[a-zA-Z0-9]*')

    def test_valid_init_no_defaults(self):
        test = _DummyCompiledAutograderTestCase.objects.validate_and_create(
            name=self.test_name, project=self.project,
            **self.compiled_test_kwargs)

        test.refresh_from_db()

        self.assertEqual(test.compiler, self.compiler)
        self.assertEqual(test.compiler_flags, self.compiler_flags)
        self.assertEqual(
            test.executable_name, self.executable_name)

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

    def test_exception_on_empty_executable_name(self):
        test = _DummyCompiledAutograderTestCase.objects.validate_and_create(
            name=self.test_name, project=self.project,
            **self.compiled_test_kwargs)
        print(test.executable_name)

        with self.assertRaises(ValidationError) as cm:
            test.validate_and_update(executable_name='')
            print(test.executable_name)
            print('waaaa')

        self.assertTrue('executable_name' in cm.exception.message_dict)

    def test_exception_on_invalid_chars_in_executable_name(self):
        self.compiled_test_kwargs['executable_name'] = "../haxorz"

        with self.assertRaises(ValidationError) as cm:
            _DummyCompiledAutograderTestCase.objects.validate_and_create(
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('executable_name' in cm.exception.message_dict)

    def test_validation_error_contains_base_and_derived_error_messages(self):
        self.compiled_test_kwargs['compiler'] = 'unsupported_compiler'

        with self.assertRaises(ValidationError) as cm:
            _DummyCompiledAutograderTestCase.objects.validate_and_create(
                name=self.test_name, project=self.project,
                time_limit='spam',
                **self.compiled_test_kwargs)

        self.assertTrue('time_limit' in cm.exception.message_dict)
        self.assertTrue('compiler' in cm.exception.message_dict)

    def test_test_checks_compilation(self):
        test = _DummyCompiledAutograderTestCase.objects.validate_and_create(
            name=self.test_name, project=self.project,
            **self.compiled_test_kwargs)

        self.assertTrue(test.test_checks_compilation())


class GetCompilationCommandTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.group = obj_ut.build_submission_group()

        # These files should NOT show up in the list of files to compile
        self.uploaded_resource_files = [
            ag_models.UploadedFile.objects.validate_and_create(
                project=self.group.project,
                file_obj=SimpleUploadedFile('steve', b'blah')),
        ]

        self.uploaded_compiled_files = [
            ag_models.UploadedFile.objects.validate_and_create(
                project=self.group.project,
                file_obj=SimpleUploadedFile('stove.cpp', b'bloo')),
            ag_models.UploadedFile.objects.validate_and_create(
                project=self.group.project,
                file_obj=SimpleUploadedFile('stuve.cpp', b'bloo'))
        ]

        # Make sure to submit these files, and verify that they are NOT
        # included in the list of files to compile.
        self.expected_resource_files = [
            ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
                pattern='spam.txt',
                project=self.group.project
            ),
            ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
                pattern='file_*.py',
                project=self.group.project,
                min_num_matches=1,
                max_num_matches=3
            ),
        ]

        self.expected_compiled_files = [
            ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
                pattern='spam.cpp',
                project=self.group.project
            ),
            ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
                pattern='eggs.cpp',
                project=self.group.project
            ),
            ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
                pattern='file_*.cpp',
                project=self.group.project,
                min_num_matches=1,
                max_num_matches=3
            ),
        ]

        self.ag_test = _DummyCompiledAutograderTestCase.objects.validate_and_create(
            project=self.group.project,
            name='testy',
            compiler='g++'
        )

        self.ag_test.test_resource_files.add(*self.uploaded_resource_files)
        self.ag_test.student_resource_files.add(*self.expected_resource_files)

        self.ag_test.project_files_to_compile_together.add(
            *self.uploaded_compiled_files)
        self.ag_test.student_files_to_compile_together.add(
            *self.expected_compiled_files)

        self.resource_files_to_submit = [
            SimpleUploadedFile('spam.txt', b'waaaa'),
            SimpleUploadedFile('file_42.py', b'pypypy'),
            SimpleUploadedFile('file_43.py', b'pypypy')
        ]

        self.compiled_files_to_submit = [
            SimpleUploadedFile('spam.cpp', b'waaaa'),
            SimpleUploadedFile('eggs.cpp', b'weeeee'),
            SimpleUploadedFile('file_42.cpp', b'cppppp'),
            SimpleUploadedFile('file_43.cpp', b'cppppp')
        ]

    def test_all_files_submitted(self):
        self.do_files_to_compile_test(self.compiled_files_to_submit)

    def test_some_required_files_not_submitted(self):
        self.do_files_to_compile_test(self.compiled_files_to_submit[1:])

    def test_not_enough_files_matching_pattern(self):
        self.do_files_to_compile_test(self.compiled_files_to_submit[:-1])

    def do_files_to_compile_test(self, compiled_files_to_submit):
        submission = ag_models.Submission.objects.validate_and_create(
            submission_group=self.group,
            submitted_files=(self.resource_files_to_submit +
                             compiled_files_to_submit)
        )

        # Check for uploaded and student-submitted files to compile.
        expected_compiled_files = itertools.chain(
            (uploaded_file.name for uploaded_file in
             self.uploaded_compiled_files),
            (file_.name for file_ in compiled_files_to_submit)
        )

        self.assertCountEqual(
            expected_compiled_files,
            self.ag_test.get_filenames_to_compile_together(submission))
