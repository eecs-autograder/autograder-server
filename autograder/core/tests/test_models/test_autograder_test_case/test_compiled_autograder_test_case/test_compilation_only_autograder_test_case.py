from django.core.files.uploadedfile import SimpleUploadedFile


from autograder.core.models import (
    AutograderTestCaseBase, AutograderTestCaseFactory)

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

import autograder.core.tests.dummy_object_utils as obj_ut

from .utils import (
    SharedSetUpTearDownForRunTestsWithCompilation,
    CppProgramStrs)


# class CompilationOnlyAGTestMiscTestCase(TemporaryFilesystemTestCase):
#     def setUp(self):
#         super().setUp()

#         self.project = obj_ut.build_project()

    #         required_student_files=['file1.cpp', 'file2.cpp'],
    #         expected_student_file_patterns=[
    #             Project.FilePatternTuple('test_*.cpp', 1, 2),
    #             Project.FilePatternTuple('funsy[0-9].cpp', 0, 2)])

    #     self.project_files = [
    #         SimpleUploadedFile('spam.txt', b'hello there!'),
    #         SimpleUploadedFile('eggs.cpp', b'egg bacon spam and sausage'),
    #         SimpleUploadedFile('sausage.cpp', b'spam egg sausage and spam')
    #     ]

    #     for file_obj in self.project_files:
    #         self.project.add_project_file(file_obj)

    #     self.test_name = 'my_test'

    #     self.compiler = 'g++'
    #     self.compiler_flags = ['--foo_arg=bar', '-s']

    #     self.project_files_to_compile_together = [
    #         'spam.txt'
    #     ]
    #     self.student_files_to_compile_together = [
    #         'file1.cpp',  # required student file
    #         'test_*.cpp'  # expected student pattern
    #     ]
    #     self.executable_name = "sausage.exe"

    #     self.compiled_test_kwargs = {
    #         "test_resource_files": ['spam.txt'],
    #         "student_resource_files": ['file1.cpp', 'test_*.cpp'],
    #         "compiler": self.compiler,
    #         "compiler_flags": self.compiler_flags,
    #         "project_files_to_compile_together": self.project_files_to_compile_together,
    #         "student_files_to_compile_together": self.student_files_to_compile_together,
    #         "executable_name": self.executable_name,
    #     }

    # def test_valid_create_custom_values(self):
    #     self.compiled_test_kwargs.pop('executable_name')
    #     AutograderTestCaseFactory.validate_and_create(
    #         'compilation_only_test_case',
    #         name=self.test_name, project=self.project,
    #         **self.compiled_test_kwargs)

    #     loaded_test = AutograderTestCaseBase.objects.get(
    #         name=self.test_name, project=self.project)

    #     self.assertEqual(self.compiler, loaded_test.compiler)
    #     self.assertEqual(self.compiler_flags, loaded_test.compiler_flags)
    #     self.assertEqual(
    #         self.project_files_to_compile_together,
    #         loaded_test.project_files_to_compile_together)
    #     self.assertEqual(
    #         self.student_files_to_compile_together,
    #         loaded_test.student_files_to_compile_together)

    # def test_test_checks_return_code(self):
    #     test = AutograderTestCaseFactory.validate_and_create(
    #         'compilation_only_test_case',
    #         name='steve',
    #         project=self.project,
    #         compiler='g++')

    #     self.assertFalse(test.test_checks_return_code())

    # def test_test_checks_output(self):
    #     test = AutograderTestCaseFactory.validate_and_create(
    #         'compilation_only_test_case',
    #         name='stove',
    #         project=self.project,
    #         compiler='g++')

    #     self.assertFalse(test.test_checks_output())


class CompilationOnlyAutograderTestRunTestCase(
        SharedSetUpTearDownForRunTestsWithCompilation,
        TemporaryFilesystemTestCase):

    def get_ag_test_type_str_for_factory(self):
        return 'compilation_only_test_case'

    def test_compilation_success(self):
        cpp_file_content = CppProgramStrs.RETURN_ONLY_TEMPLATE.format(42)
        with open(self.main_file.abspath, 'w') as f:
            f.write(cpp_file_content)

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)

        self.assertTrue(result.compilation_succeeded)

    def test_compilation_failure(self):
        with open(self.main_file.abspath, 'w') as f:
            f.write(CppProgramStrs.COMPILE_ERROR)

        result = self.test_case_starter.run(
            submission=self.submission, autograder_sandbox=self.sandbox)

        self.assertFalse(result.compilation_succeeded)
