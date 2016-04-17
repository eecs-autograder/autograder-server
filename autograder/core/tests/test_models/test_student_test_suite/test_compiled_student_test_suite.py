# import itertools
# from unittest import mock

# from django.core.files.uploadedfile import SimpleUploadedFile
# from django.core.exceptions import ValidationError

# from autograder.core.tests.temporary_filesystem_test_case import (
#     TemporaryFilesystemTestCase)

# import autograder.core.tests.dummy_object_utils as obj_ut

# from autograder.core.models import (
#     StudentTestSuiteFactory, SubmissionGroup, Submission,
#     StudentTestSuiteResult, StudentTestSuiteBase)
# from autograder.security.autograder_sandbox import AutograderSandbox

# from .test_student_test_suite_base import SharedSetUp
# # import autograder.core.shared.utilities as ut
# import autograder.core.shared.global_constants as gc


# class CompiledStudentTestSuiteTestCase(
#         SharedSetUp, TemporaryFilesystemTestCase):
#     def test_valid_initialization_with_defaults(self):
#         suite = StudentTestSuiteFactory.validate_and_create(
#             'compiled_student_test_suite',
#             name=self.suite_name,
#             project=self.project,
#             student_test_case_filename_pattern=self.test_file_pattern.pattern,
#             correct_implementation_filename=self.correct_impl_file.name,
#             compiler='g++')

#         loaded = StudentTestSuiteBase.objects.get(pk=suite.pk)

#         self.assertEqual('g++', loaded.compiler)
#         self.assertEqual([], loaded.compiler_flags)
#         self.assertEqual([], loaded.suite_resource_files_to_compile_together)
#         self.assertTrue(loaded.compile_implementation_files)

#     def test_valid_initialization_custom_values(self):
#         compiler = 'clang++'
#         compiler_flags = ['-Wall', '-Werror', '-pedantic']

#         suite = StudentTestSuiteFactory.validate_and_create(
#             'compiled_student_test_suite',
#             name=self.suite_name,
#             project=self.project,
#             student_test_case_filename_pattern=self.test_file_pattern.pattern,
#             correct_implementation_filename=self.correct_impl_file.name,
#             suite_resource_filenames=self.project_filenames,

#             compiler=compiler,
#             compiler_flags=compiler_flags,
#             suite_resource_files_to_compile_together=self.project_filenames,
#             compile_implementation_files=False
#         )

#         loaded = StudentTestSuiteBase.objects.get(pk=suite.pk)

#         self.assertEqual(compiler, loaded.compiler)
#         self.assertEqual(compiler_flags, loaded.compiler_flags)
#         self.assertEqual(self.project_filenames,
#                          loaded.suite_resource_files_to_compile_together)
#         self.assertFalse(loaded.compile_implementation_files)

#     def test_exception_invalid_compiler(self):
#         with self.assertRaises(ValidationError) as cm:
#             StudentTestSuiteFactory.validate_and_create(
#                 'compiled_student_test_suite',
#                 name=self.suite_name,
#                 project=self.project,
#                 student_test_case_filename_pattern=self.test_file_pattern.pattern,
#                 correct_implementation_filename=self.correct_impl_file.name,
#                 compiler='not_a_compiler++')

#         self.assertTrue('compiler' in cm.exception.message_dict)

#     def test_exception_invalid_characters_in_compiler_flags(self):
#         with self.assertRaises(ValidationError) as cm:
#             StudentTestSuiteFactory.validate_and_create(
#                 'compiled_student_test_suite',
#                 name=self.suite_name,
#                 project=self.project,
#                 student_test_case_filename_pattern=(
#                     self.test_file_pattern.pattern),
#                 correct_implementation_filename=self.correct_impl_file.name,
#                 compiler_flags=['-Wall', ';echo "haxorz" #'])

#         self.assertTrue('compiler_flags' in cm.exception.message_dict)

#         error_list = cm.exception.message_dict['compiler_flags']
#         self.assertEqual('', error_list[0])
#         self.assertTrue(error_list[1])

#     def test_exception_compiler_flag_is_whitespace(self):
#         with self.assertRaises(ValidationError) as cm:
#             StudentTestSuiteFactory.validate_and_create(
#                 'compiled_student_test_suite',
#                 name=self.suite_name,
#                 project=self.project,
#                 student_test_case_filename_pattern=self.test_file_pattern.pattern,
#                 correct_implementation_filename=self.correct_impl_file.name,
#                 compiler_flags=['-Wall', '          '])

#         self.assertTrue('compiler_flags' in cm.exception.message_dict)

#     def test_exception_some_suite_resource_files_to_compile_together_not_suite_resource_files(self):
#         suite_resource_filenames = self.project_filenames[:1]
#         with self.assertRaises(ValidationError) as cm:
#             StudentTestSuiteFactory.validate_and_create(
#                 'compiled_student_test_suite',
#                 name=self.suite_name,
#                 project=self.project,
#                 student_test_case_filename_pattern=self.test_file_pattern.pattern,
#                 suite_resource_filenames=suite_resource_filenames,
#                 correct_implementation_filename=self.correct_impl_file.name,
#                 suite_resource_files_to_compile_together=(
#                     suite_resource_filenames + ['not_a_suite_resource_file']))

#         self.assertTrue('suite_resource_files_to_compile_together'
#                         in cm.exception.message_dict)

# # -----------------------------------------------------------------------------
# # -----------------------------------------------------------------------------


# class _EvaluateTestCaseSetUpBase:
#     def setUp(self):
#         super().setUp()

#         self.test_file_pattern = 'test_*.cpp'
#         self.group = obj_ut.build_submission_group(
#             project_kwargs={
#                 'allow_submissions_from_non_enrolled_students': True,
#                 'expected_student_file_patterns': [
#                     (self.test_file_pattern, 1, 3)],
#             }
#         )
#         self.project = self.group.project
#         for file_ in PROJECT_FILES:
#             self.project.add_project_file(file_)

#         print(self.project.get_project_file_basenames())

#         self.suite = StudentTestSuiteFactory.validate_and_create(
#             'compiled_student_test_suite',
#             name='suite',
#             project=self.project,
#             student_test_case_filename_pattern=self.test_file_pattern,
#             correct_implementation_filename=CORRECT_IMPLEMENTATION.name,
#             suite_resource_filenames=[HEADER_FILE.name, UTIL_FILE.name],
#             compiler='g++',
#             compiler_flags=['-Wall', '-pedantic'],
#             suite_resource_files_to_compile_together=[UTIL_FILE.name],
#             buggy_implementation_filenames=[
#                 file_.name for file_ in BUGGY_IMPLEMENTATIONS]
#         )


# class CompiledStudentTestSuiteEvaluationTestCase(_EvaluateTestCaseSetUpBase,
#                                                  TemporaryFilesystemTestCase):
#     def setUp(self):
#         super().setUp()

#         self.sandbox = AutograderSandbox()
#         self.sandbox.__enter__()

#     def tearDown(self):
#         super().tearDown()

#         self.sandbox.__exit__()

#     # -------------------------------------------------------------------------

#     def test_all_buggy_implementations_exposed(self):
#         self.submission = Submission.objects.validate_and_create(
#             submission_group=self.group, submitted_files=[
#                 STUDENT_TEST_RETURN_42, STUDENT_TEST_IS_OVER_9000])

#         result = self.suite.evaluate(self.submission, self.sandbox)
#         result.save()
#         result = StudentTestSuiteResult.objects.get(pk=result.pk)

#         self.assertSetEqual(
#             result.buggy_implementations_exposed,
#             set(file_.name for file_ in BUGGY_IMPLEMENTATIONS))

#     def test_all_buggy_implementations_exposed_but_some_tests_dont_compile(self):
#         self.submission = Submission.objects.validate_and_create(
#             submission_group=self.group, submitted_files=[
#                 STUDENT_TEST_RETURN_42, STUDENT_TEST_IS_OVER_9000,
#                 STUDENT_TEST_THAT_DOESNT_COMPILE])

#         result = self.suite.evaluate(self.submission, self.sandbox)
#         result.save()
#         result = StudentTestSuiteResult.objects.get(pk=result.pk)

#         self.assertSetEqual(
#             result.buggy_implementations_exposed,
#             set(file_.name for file_ in BUGGY_IMPLEMENTATIONS))

#         compilation_failures = set(
#             detail.student_test_case_name for detail in result.detailed_results
#             if not detail.compilation_succeeded)

#         self.assertSetEqual(
#             compilation_failures,
#             set([STUDENT_TEST_THAT_DOESNT_COMPILE.name]))

#     def test_all_buggy_implementations_exposed_but_some_tests_invalid(self):
#         self.submission = Submission.objects.validate_and_create(
#             submission_group=self.group, submitted_files=[
#                 STUDENT_TEST_RETURN_42, STUDENT_TEST_IS_OVER_9000,
#                 STUDENT_TEST_THAT_IS_INVALID])

#         result = self.suite.evaluate(self.submission, self.sandbox)
#         result.save()
#         result = StudentTestSuiteResult.objects.get(pk=result.pk)

#         self.assertSetEqual(
#             result.buggy_implementations_exposed,
#             set(file_.name for file_ in BUGGY_IMPLEMENTATIONS))

#         invalid_tests = set(
#             detail.student_test_case_name for detail in result.detailed_results
#             if not detail.valid)

#         self.assertSetEqual(
#             invalid_tests,
#             set([STUDENT_TEST_THAT_IS_INVALID.name]))

#     def test_some_buggy_implementations_exposed(self):
#         self.submission = Submission.objects.validate_and_create(
#             submission_group=self.group, submitted_files=[
#                 STUDENT_TEST_RETURN_42, STUDENT_TEST_THAT_CATCHES_NONE])

#         result = self.suite.evaluate(self.submission, self.sandbox)
#         result.save()
#         result = StudentTestSuiteResult.objects.get(pk=result.pk)

#         self.assertSetEqual(
#             result.buggy_implementations_exposed,
#             set([BUGGY_IMPLEMENTATION_RETURN_42.name]))

#     def test_no_buggy_implementation_exposed_but_test_valid(self):
#         self.submission = Submission.objects.validate_and_create(
#             submission_group=self.group, submitted_files=[
#                 STUDENT_TEST_THAT_CATCHES_NONE])

#         result = self.suite.evaluate(self.submission, self.sandbox)
#         self.assertCountEqual(result.buggy_implementations_exposed, [])
#         result.save()
#         result = StudentTestSuiteResult.objects.get(pk=result.pk)

#         self.assertTrue(result.detailed_results[0].valid)
#         self.assertSetEqual(result.buggy_implementations_exposed, set())

#     def test_no_buggy_implementations_exposed_because_compile_error(self):
#         self.submission = Submission.objects.validate_and_create(
#             submission_group=self.group, submitted_files=[
#                 STUDENT_TEST_THAT_DOESNT_COMPILE])

#         result = self.suite.evaluate(self.submission, self.sandbox)
#         result.save()
#         result = StudentTestSuiteResult.objects.get(pk=result.pk)

#         self.assertFalse(result.detailed_results[0].compilation_succeeded)
#         self.assertSetEqual(result.buggy_implementations_exposed, set())

#     def test_no_buggy_implementations_exposed_because_invalid_test(self):
#         self.submission = Submission.objects.validate_and_create(
#             submission_group=self.group, submitted_files=[
#                 STUDENT_TEST_THAT_IS_INVALID])

#         result = self.suite.evaluate(self.submission, self.sandbox)
#         result.save()
#         result = StudentTestSuiteResult.objects.get(pk=result.pk)

#         self.assertFalse(result.detailed_results[0].valid)
#         self.assertFalse(result.detailed_results[0].timed_out)
#         self.assertSetEqual(result.buggy_implementations_exposed, set())

#     def test_no_buggy_implementations_exposed_because_timeout(self):
#         self.submission = Submission.objects.validate_and_create(
#             submission_group=self.group, submitted_files=[
#                 STUDENT_TEST_THAT_INFINITE_LOOPS])

#         result = self.suite.evaluate(self.submission, self.sandbox)
#         result.save()
#         result = StudentTestSuiteResult.objects.get(pk=result.pk)

#         self.assertFalse(result.detailed_results[0].valid)
#         self.assertTrue(result.detailed_results[0].timed_out)
#         self.assertSetEqual(result.buggy_implementations_exposed, set())

#     def test_implementation_header_file_alias(self):
#         self.suite.implementation_file_alias = 'impl.h'
#         self.suite.buggy_implementation_filenames = [BUGGY_IMPL_HEADER.name]
#         self.suite.correct_implementation_filename = CORRECT_IMPL_HEADER.name
#         self.suite.compile_implementation_files = False
#         self.suite.validate_and_save()

#         self.submission = Submission.objects.validate_and_create(
#             submission_group=self.group, submitted_files=[
#                 STUDENT_TEST_IMPL_HEADER])

#         result = self.suite.evaluate(self.submission, self.sandbox)
#         result.save()
#         result = StudentTestSuiteResult.objects.get(pk=result.pk)

#         self.assertTrue(result.detailed_results[0].compilation_succeeded)
#         self.assertTrue(result.detailed_results[0].valid)
#         self.assertSetEqual(
#             result.buggy_implementations_exposed,
#             set([BUGGY_IMPL_HEADER.name]))

#     def test_implementation_non_header_file_alias(self):
#         self.suite.implementation_file_alias = 'alias.cpp'
#         self.buggy_implementation_filenames = [
#             BUGGY_IMPLEMENTATION_RETURN_42.name
#         ]
#         self.suite.validate_and_save()

#         self.submission = Submission.objects.validate_and_create(
#             submission_group=self.group, submitted_files=[
#                 STUDENT_TEST_THAT_TRIES_TO_OPEN_ALIASED_FILE])

#         result = self.suite.evaluate(self.submission, self.sandbox)
#         result.save()
#         result = StudentTestSuiteResult.objects.get(pk=result.pk)

#         self.assertTrue(result.detailed_results[0].compilation_succeeded)
#         self.assertTrue(result.detailed_results[0].valid)
#         self.assertSetEqual(
#             result.buggy_implementations_exposed,
#             set([BUGGY_IMPLEMENTATION_RETURN_42.name]))

# # -----------------------------------------------------------------------------


# class CompiledStudentTestSuiteEvaluateResourceLimitTestCase(
#         _EvaluateTestCaseSetUpBase, TemporaryFilesystemTestCase):
#     def setUp(self):
#         super().setUp()

#         self.suite.buggy_implementation_filenames = (
#             self.suite.buggy_implementation_filenames[:1])
#         self.suite.validate_and_save()

#         self.submission = Submission.objects.validate_and_create(
#             submission_group=self.group, submitted_files=[
#                 STUDENT_TEST_RETURN_42])

#     @mock.patch('autograder.security.autograder_sandbox.AutograderSandbox',
#                 autospec=True)
#     def test_resource_limits_applied(self, MockSandbox):
#         run_cmd_mock_result = mock.Mock()
#         type(run_cmd_mock_result).return_code = (
#             mock.PropertyMock(return_value=0))
#         type(run_cmd_mock_result).timed_out = (
#             mock.PropertyMock(return_value=False))

#         sandbox = MockSandbox()
#         sandbox.run_command.return_value = run_cmd_mock_result
#         self.suite.evaluate(self.submission, sandbox)

#         print(sandbox.run_command.mock_calls)
#         assert len(self.submission.submitted_filenames) == 1
#         assert len(self.suite.buggy_implementation_filenames) == 1
#         expected_num_progs_run = 2
#         calls = list(itertools.repeat(
#             mock.call(
#                 ['./prog'],
#                 timeout=self.suite.time_limit,
#                 max_num_processes=gc.DEFAULT_PROCESS_LIMIT,
#                 max_stack_size=gc.DEFAULT_STACK_SIZE_LIMIT,
#                 max_virtual_memory=gc.DEFAULT_VIRTUAL_MEM_LIMIT
#             ),
#             expected_num_progs_run
#         ))

#         sandbox.run_command.assert_has_calls(calls, any_order=True)


# # -----------------------------------------------------------------------------

# HEADER_FILE = SimpleUploadedFile(
#     'header.h',
#     b'''
# int return42();
# bool is_over_9000(int num);
# ''')

# UTIL_FILE = SimpleUploadedFile(
#     'util.cpp',
#     b'''const int spam = 42;
# ''')

# CORRECT_IMPLEMENTATION = SimpleUploadedFile(
#     'impl.cpp',
#     b'''
# #include "header.h"

# int return42()
# {
#     return 42;
# }

# bool is_over_9000(int num)
# {
#     return num > 9000;
# }
# ''')

# BUGGY_IMPLEMENTATION_RETURN_42 = SimpleUploadedFile(
#     'buggy_return42.cpp',
#     b'''
# #include "header.h"

# int return42()
# {
#     return 43;
# }

# bool is_over_9000(int num)
# {
#     return num > 9000;
# }
# ''')
# BUGGY_IMPLEMENTATION_IS_OVER_9000 = SimpleUploadedFile(
#     'buggy_over9000.cpp',
#     b'''
# #include "header.h"

# int return42()
# {
#     return 42;
# }

# bool is_over_9000(int num)
# {
#     return num < 9000;
# }
# ''')

# STUDENT_TEST_RETURN_42 = SimpleUploadedFile(
#     'test_return42.cpp',
#     b'''
# #include "header.h"

# int main()
# {
#     if (return42() != 42)
#     {
#         return 1;
#     }
#     return 0;
# }
# ''')
# STUDENT_TEST_IS_OVER_9000 = SimpleUploadedFile(
#     'test_is_over9000.cpp',
#     b'''
# #include "header.h"

# int main()
# {
#     if (is_over_9000(8000))
#     {
#         return 2;
#     }
#     return 0;
# }
# ''')

# STUDENT_TEST_THAT_CATCHES_NONE = SimpleUploadedFile(
#     'test_catch_none.cpp',
#     b'''
#     int main() { return 0; }
# ''')
# STUDENT_TEST_THAT_DOESNT_COMPILE = SimpleUploadedFile(
#     'test_no_compile.cpp',
#     b'''
# askldfjl;aksdjf;kjdsf
# ''')
# STUDENT_TEST_THAT_IS_INVALID = SimpleUploadedFile(
#     'test_invalid.cpp',
#     b'''
# int main() { return 1; }
# ''')
# STUDENT_TEST_THAT_INFINITE_LOOPS = SimpleUploadedFile(
#     'test_infinite_loop.cpp',
#     b'''
# int main() { while (true); return 0; }
# ''')
# STUDENT_TEST_THAT_TRIES_TO_OPEN_ALIASED_FILE = SimpleUploadedFile(
#     'test_open_file.cpp',
#     b'''
# #include "header.h"
# #include <iostream>
# #include <fstream>

# using namespace std;

# int main()
# {
#     ifstream ifs("alias.cpp");
#     if (!ifs.is_open())
#     {
#         return 9;
#     }

#     if (return42() != 42)
#     {
#         return 1;
#     }

#     return 0;
# }
# ''')

# CORRECT_IMPL_HEADER = SimpleUploadedFile(
#     'correct_impl.h',
#     b'''
# #ifndef IMPL_H
# #define IMPL_H

# int return42() { return 42; }

# #endif
# '''
# )

# BUGGY_IMPL_HEADER = SimpleUploadedFile(
#     'buggy_impl.h',
#     b'''
# #ifndef IMPL_H
# #define IMPL_H

# int return42() { return 43; }

# #endif
# '''
# )

# STUDENT_TEST_IMPL_HEADER = SimpleUploadedFile(
#     'test_impl_header.cpp',
#     b'''
# #include "impl.h"

# int main()
# {
#     if (return42() != 42)
#     {
#         return 3;
#     }
#     return 0;
# }
# '''
# )

# # -----------------------------------------------------------------------------

# PROJECT_FILES = [
#     HEADER_FILE,
#     UTIL_FILE,
#     CORRECT_IMPLEMENTATION,
#     BUGGY_IMPLEMENTATION_RETURN_42,
#     BUGGY_IMPLEMENTATION_IS_OVER_9000,
#     CORRECT_IMPL_HEADER,
#     BUGGY_IMPL_HEADER
# ]

# BUGGY_IMPLEMENTATIONS = [
#     BUGGY_IMPLEMENTATION_RETURN_42,
#     BUGGY_IMPLEMENTATION_IS_OVER_9000,
# ]

# # -----------------------------------------------------------------------------

# # STUDENT_TESTS = [
# #     STUDENT_TEST_RETURN_42,
# #     STUDENT_TEST_IS_OVER_9000,
# #     STUDENT_TEST_THAT_DOESNT_COMPILE,
# #     STUDENT_TEST_THAT_IS_INVALID,
# # ]
# #
