import itertools
import random

from django.core import exceptions

from django.core.files.uploadedfile import SimpleUploadedFile

import autograder.core.models as ag_models
from autograder.core.models.autograder_test_case.feedback_config import (
    FeedbackConfig)

import autograder.core.constants as const
import autograder.sandbox.constants as sandbox_const

from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build

from .models import _DummyAutograderTestCase

from autograder.sandbox.autograder_sandbox import AutograderSandbox


class _Shared:
    def setUp(self):
        super().setUp()
        self.project = obj_build.build_project()

        self.TEST_NAME = 'my_test'
        self.fdbk = ag_models.FeedbackConfig.objects.validate_and_create()

    def _random_fdbk(self):
        return obj_build.random_fdbk()


class AutograderTestCaseBaseMiscTestCase(_Shared, UnitTestBase):
    def test_valid_initialization_with_defaults(self):
        new_test_case = _DummyAutograderTestCase.objects.validate_and_create(
            name=self.TEST_NAME,
            project=self.project)

        new_test_case.refresh_from_db()

        self.assertEqual(new_test_case, new_test_case)
        self.assertEqual(self.TEST_NAME, new_test_case.name)
        self.assertEqual(self.project, new_test_case.project)

        self.assertFalse(new_test_case.deferred)

        self.assertEqual(new_test_case.command_line_arguments, [])
        self.assertEqual(new_test_case.standard_input, "")

        self.assertEqual(new_test_case.time_limit, 10)
        self.assertFalse(new_test_case.allow_network_connections)
        self.assertEqual(new_test_case.stack_size_limit,
                         sandbox_const.DEFAULT_STACK_SIZE_LIMIT)
        self.assertEqual(new_test_case.virtual_memory_limit,
                         sandbox_const.DEFAULT_VIRTUAL_MEM_LIMIT)
        self.assertEqual(new_test_case.process_spawn_limit,
                         sandbox_const.DEFAULT_PROCESS_LIMIT)

        self.assertIsNone(new_test_case.expected_return_code)
        self.assertFalse(new_test_case.expect_any_nonzero_return_code)
        self.assertEqual("", new_test_case.expected_standard_output)
        self.assertEqual("", new_test_case.expected_standard_error_output)
        self.assertFalse(new_test_case.use_valgrind)
        self.assertEqual(const.DEFAULT_VALGRIND_FLAGS,
                         new_test_case.valgrind_flags)

        self.assertEqual(0, new_test_case.points_for_correct_return_code)
        self.assertEqual(0, new_test_case.points_for_correct_stdout)
        self.assertEqual(0, new_test_case.points_for_correct_stderr)
        self.assertEqual(0, new_test_case.deduction_for_valgrind_errors)
        self.assertEqual(0, new_test_case.points_for_compilation_success)

        self.assertEqual(
            self.fdbk.to_dict(),
            new_test_case.feedback_configuration.to_dict())
        self.assertFalse(new_test_case.visible_to_students)

        self.assertEqual(
            FeedbackConfig.create_ultimate_submission_default().to_dict(),
            new_test_case.ultimate_submission_fdbk_conf.to_dict())
        self.assertTrue(new_test_case.visible_in_ultimate_submission)

        self.assertEqual(
            FeedbackConfig().to_dict(),
            new_test_case.past_submission_limit_fdbk_conf.to_dict())
        self.assertFalse(new_test_case.visible_in_past_limit_submission)

        self.assertEqual(FeedbackConfig.create_with_max_fdbk().to_dict(),
                         new_test_case.staff_viewer_fdbk_conf.to_dict())

    def test_valid_initialization_custom_values(self):
        vals = {
            'name': self.TEST_NAME,
            'project': self.project,

            'deferred': True,

            'command_line_arguments': [
                'spam', '--eggs', '--sausage=spam', '-p', 'input.in'],
            'standard_input': "spameggsausagespam",
            'expected_standard_output': "standardspaminputspam",
            'expected_standard_error_output': "errorzspam",

            'time_limit': random.randint(1, 60),
            'stack_size_limit': random.randint(
                1, sandbox_const.MAX_STACK_SIZE_LIMIT),
            'virtual_memory_limit': random.randint(
                1, sandbox_const.MAX_VIRTUAL_MEM_LIMIT),
            'process_spawn_limit': random.randint(
                1, sandbox_const.MAX_PROCESS_LIMIT),
            'allow_network_connections': random.choice([True, False]),

            'expected_return_code': random.randint(-3, 10),
            'expect_any_nonzero_return_code': random.choice([True, False]),

            'valgrind_flags': ['--leak-check=yes', '--error-exitcode=9000'],
            'use_valgrind': random.choice([True, False]),

            'points_for_correct_return_code': random.randint(1, 15),
            'points_for_correct_stdout': random.randint(1, 15),
            'points_for_correct_stderr': random.randint(1, 15),
            'deduction_for_valgrind_errors': random.randint(1, 5),
            'points_for_compilation_success': random.randint(1, 15),

            'feedback_configuration': self._random_fdbk(),
            'ultimate_submission_fdbk_conf': self._random_fdbk(),
            'past_submission_limit_fdbk_conf': self._random_fdbk(),
            'staff_viewer_fdbk_conf': self._random_fdbk(),

            'visible_to_students': random.choice([True, False]),
            'visible_in_ultimate_submission': random.choice([True, False]),
            'visible_in_past_limit_submission': random.choice([True, False]),
        }

        new_test_case = _DummyAutograderTestCase.objects.validate_and_create(
            **vals)

        new_test_case.refresh_from_db()

        for key, value in vals.items():
            self.assertEqual(value, getattr(new_test_case, key))

    def test_to_dict_default_fields(self):
        expected_fields = [
            'type_str',

            'name',
            'project',

            'deferred',

            'command_line_arguments',
            'standard_input',

            'time_limit',
            'allow_network_connections',
            'stack_size_limit',
            'virtual_memory_limit',
            'process_spawn_limit',

            'expected_return_code',
            'expect_any_nonzero_return_code',
            'expected_standard_output',
            'expected_standard_error_output',

            'use_valgrind',
            'valgrind_flags',

            'points_for_correct_return_code',
            'points_for_correct_stdout',
            'points_for_correct_stderr',
            'deduction_for_valgrind_errors',

            'feedback_configuration',
            'visible_to_students',

            'ultimate_submission_fdbk_conf',
            'visible_in_ultimate_submission',

            'past_submission_limit_fdbk_conf',
            'visible_in_past_limit_submission',

            'staff_viewer_fdbk_conf',

            'compiler',
            'compiler_flags',
            'executable_name',
            'points_for_compilation_success',

            'interpreter',
            'interpreter_flags',
            'entry_point_filename'
        ]

        self.assertCountEqual(
            expected_fields,
            ag_models.AutograderTestCaseBase.get_default_to_dict_fields())

        ag_test = _DummyAutograderTestCase.objects.validate_and_create(
            name='steve',
            project=self.project,
            feedback_configuration=self.fdbk)
        self.assertTrue(ag_test.to_dict())

    def test_to_dict_feedback_expanded(self):
        self.assertCountEqual(
            ['feedback_configuration', 'ultimate_submission_fdbk_conf',
             'past_submission_limit_fdbk_conf', 'staff_viewer_fdbk_conf'],
            ag_models.AutograderTestCaseBase.FBDK_FIELD_NAMES)
        ag_test = _DummyAutograderTestCase.objects.validate_and_create(
            name=self.TEST_NAME,
            project=self.project,
            feedback_configuration=self.fdbk,
            ultimate_submission_fdbk_conf=self._random_fdbk(),
            past_submission_limit_fdbk_conf=self._random_fdbk(),
            staff_viewer_fdbk_conf=self._random_fdbk())

        for fdbk_field in ag_models.AutograderTestCaseBase.FBDK_FIELD_NAMES:
            self.assertEqual(getattr(ag_test, fdbk_field).to_dict(),
                             ag_test.to_dict()[fdbk_field])

            fdbk_excluded = ag_test.to_dict(exclude_fields=[fdbk_field])

            self.assertNotIn(fdbk_field, fdbk_excluded)

    def test_editable_fields(self):
        expected = [
            'name',

            'deferred',

            'command_line_arguments',
            'standard_input',

            'time_limit',
            'allow_network_connections',
            'stack_size_limit',
            'virtual_memory_limit',
            'process_spawn_limit',

            'expected_return_code',
            'expect_any_nonzero_return_code',
            'expected_standard_output',
            'expected_standard_error_output',

            'use_valgrind',
            'valgrind_flags',

            'points_for_correct_return_code',
            'points_for_correct_stdout',
            'points_for_correct_stderr',
            'deduction_for_valgrind_errors',

            'feedback_configuration',
            'visible_to_students',

            'ultimate_submission_fdbk_conf',
            'visible_in_ultimate_submission',

            'past_submission_limit_fdbk_conf',
            'visible_in_past_limit_submission',

            'staff_viewer_fdbk_conf',

            'compiler',
            'compiler_flags',
            'executable_name',
            'points_for_compilation_success',

            'interpreter',
            'interpreter_flags',
            'entry_point_filename',
        ]

        self.assertCountEqual(
            expected,
            ag_models.AutograderTestCaseBase.get_editable_fields())

    def test_exception_on_negative_point_distributions(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                points_for_correct_return_code=-1,
                points_for_correct_stdout=-1,
                points_for_correct_stderr=-1,
                deduction_for_valgrind_errors=-1,
                points_for_compilation_success=-1)

        self.assertTrue(
            'points_for_correct_return_code' in cm.exception.message_dict)
        self.assertTrue(
            'points_for_correct_stdout' in cm.exception.message_dict)
        self.assertTrue(
            'points_for_correct_stderr' in cm.exception.message_dict)
        self.assertTrue(
            'deduction_for_valgrind_errors' in cm.exception.message_dict)
        self.assertTrue(
            'points_for_compilation_success' in cm.exception.message_dict)

    def test_invalid_test_type(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AutograderTestCaseFactory.validate_and_create(
                'not_a_test_type')

        self.assertIn('type_str', cm.exception.message_dict)


class AGTestCaseNameExceptionTestCase(_Shared, UnitTestBase):
    def test_exception_on_non_unique_name_within_project(self):
        _DummyAutograderTestCase.objects.validate_and_create(
            name=self.TEST_NAME,
            project=self.project)

        with self.assertRaises(exceptions.ValidationError):
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME,
                project=self.project)

    def test_no_exception_same_name_different_project(self):
        _DummyAutograderTestCase.objects.validate_and_create(
            name=self.TEST_NAME,
            project=self.project)

        other_project = obj_build.build_project()
        _DummyAutograderTestCase.objects.validate_and_create(
            name=self.TEST_NAME,
            project=other_project)

    def test_exception_on_empty_name(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name='',
                project=self.project)

        self.assertTrue('name' in cm.exception.message_dict)

    def test_exception_on_null_name(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=None,
                project=self.project)

        self.assertTrue('name' in cm.exception.message_dict)


class AGTestCmdArgErrorTestCase(_Shared, UnitTestBase):
    def test_exception_on_empty_value_in_cmd_args(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                command_line_arguments=["spam", '', '       '])

        self.assertTrue('command_line_arguments' in cm.exception.message_dict)
        error_list = cm.exception.message_dict['command_line_arguments']
        self.assertFalse(error_list[0])
        self.assertTrue(error_list[1])
        self.assertTrue(error_list[2])

    def test_exception_on_invalid_chars_in_command_line_args(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                command_line_arguments=["spam", "; echo 'haxorz!'"])

        self.assertTrue('command_line_arguments' in cm.exception.message_dict)
        error_list = cm.exception.message_dict['command_line_arguments']
        self.assertFalse(error_list[0])
        self.assertTrue(error_list[1])


class AGTestResourceLimitErrorTestCase(_Shared, UnitTestBase):
    def test_exception_on_zero_time_limit(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                time_limit=0)

        self.assertTrue('time_limit' in cm.exception.message_dict)

    def test_exception_on_negative_time_limit(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                time_limit=-1)

        self.assertTrue('time_limit' in cm.exception.message_dict)

    def test_exception_on_time_limit_too_large(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                time_limit=sandbox_const.MAX_SUBPROCESS_TIMEOUT + 1)

        self.assertTrue('time_limit' in cm.exception.message_dict)

    def test_exception_on_time_limit_not_integer(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                time_limit='spam')

        self.assertTrue('time_limit' in cm.exception.message_dict)

    def test_no_exception_on_time_limit_is_parseable_int(self):
        ag_test = _DummyAutograderTestCase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project,
            time_limit='2')

        ag_test.refresh_from_db()
        self.assertEqual(ag_test.time_limit, 2)

    # -------------------------------------------------------------------------

    def test_exception_negative_stack_size_limit(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                stack_size_limit=-1)

        self.assertTrue('stack_size_limit' in cm.exception.message_dict)

    def test_exception_zero_stack_size_limit(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                stack_size_limit=0)

        self.assertTrue('stack_size_limit' in cm.exception.message_dict)

    def test_exception_stack_size_limit_too_large(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                stack_size_limit=sandbox_const.MAX_STACK_SIZE_LIMIT + 1)

        self.assertTrue('stack_size_limit' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_exception_negative_virtual_memory_limit(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                virtual_memory_limit=-1)

        self.assertTrue('virtual_memory_limit' in cm.exception.message_dict)

    def test_exception_zero_virtual_memory_limit(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                virtual_memory_limit=0)

        self.assertTrue('virtual_memory_limit' in cm.exception.message_dict)

    def test_exception_virtual_mem_limit_too_large(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                virtual_memory_limit=sandbox_const.MAX_VIRTUAL_MEM_LIMIT + 1)

        self.assertTrue('virtual_memory_limit' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_exception_negative_process_limit(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                process_spawn_limit=-1)

        self.assertTrue('process_spawn_limit' in cm.exception.message_dict)

    def test_exception_process_limit_too_large(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                process_spawn_limit=sandbox_const.MAX_PROCESS_LIMIT + 1)

        self.assertTrue('process_spawn_limit' in cm.exception.message_dict)


class AGTestRetCodeTestCase(_Shared, UnitTestBase):
    def test_nonzero_expected_return_code(self):
        ag_test = _DummyAutograderTestCase.objects.validate_and_create(
            name=self.TEST_NAME,
            project=self.project,
            expect_any_nonzero_return_code=True)

        ag_test.refresh_from_db()
        self.assertTrue(ag_test.expect_any_nonzero_return_code)

    def test_exception_on_expected_return_code_not_integer(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                expected_return_code='spam')

        self.assertTrue('expected_return_code' in cm.exception.message_dict)

    def test_no_exception_on_expected_return_code_is_parseable_int(self):
        ag_test = _DummyAutograderTestCase.objects.validate_and_create(
            name=self.TEST_NAME, project=self.project,
            expected_return_code='2')

        ag_test.refresh_from_db()
        self.assertEqual(ag_test.expected_return_code, 2)


class AGTestValgrindSettingsTestCase(_Shared, UnitTestBase):
    def test_exception_on_empty_value_in_valgrind_args(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                use_valgrind=True,
                valgrind_flags=['', 'spam'])

        self.assertTrue('valgrind_flags' in cm.exception.message_dict)
        error_list = cm.exception.message_dict['valgrind_flags']
        self.assertTrue(error_list[0])
        self.assertFalse(error_list[1])

    def test_exception_on_invalid_chars_in_valgrind_flags(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            _DummyAutograderTestCase.objects.validate_and_create(
                name=self.TEST_NAME, project=self.project,
                use_valgrind=True,
                valgrind_flags=["; echo 'haxorz!'", '--leak-check=full'])

        self.assertTrue('valgrind_flags' in cm.exception.message_dict)
        error_list = cm.exception.message_dict['valgrind_flags']
        self.assertTrue(error_list[0])
        self.assertFalse(error_list[1])


class AddRequiredFilesToSandboxTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.group = obj_build.build_submission_group()

        self.uploaded_resource_files = [
            ag_models.UploadedFile.objects.validate_and_create(
                project=self.group.project,
                file_obj=SimpleUploadedFile('steve', b'blah')),
            ag_models.UploadedFile.objects.validate_and_create(
                project=self.group.project,
                file_obj=SimpleUploadedFile('stave', b'blee'))
        ]
        self.uploaded_compiled_files = [
            ag_models.UploadedFile.objects.validate_and_create(
                project=self.group.project,
                file_obj=SimpleUploadedFile('stove.cpp', b'bloo')),
            ag_models.UploadedFile.objects.validate_and_create(
                project=self.group.project,
                file_obj=SimpleUploadedFile('stuve.cpp', b'bloo'))
        ]

        self.uploaded_files = (self.uploaded_resource_files +
                               self.uploaded_compiled_files)

        self.expected_resource_files = [
            ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
                pattern='spam.txt',
                project=self.group.project
            ),
            ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
                pattern='eggs.txt',
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

        self.expected_files = (self.expected_resource_files +
                               self.expected_compiled_files)

        self.ag_test = _DummyAutograderTestCase.objects.validate_and_create(
            project=self.group.project,
            name='testy'
        )

        self.ag_test.test_resource_files.add(*self.uploaded_resource_files)
        self.ag_test.student_resource_files.add(*self.expected_resource_files)

        self.ag_test.project_files_to_compile_together.add(
            *self.uploaded_compiled_files)
        self.ag_test.student_files_to_compile_together.add(
            *self.expected_compiled_files)

        self.resource_files_to_submit = [
            SimpleUploadedFile('spam.txt', b'waaaa'),
            SimpleUploadedFile('eggs.txt', b'weeeee'),
            SimpleUploadedFile('file_42.py', b'pypypy'),
            SimpleUploadedFile('file_43.py', b'pypypy')
        ]
        self.compiled_files_to_submit = [
            SimpleUploadedFile('spam.cpp', b'waaaa'),
            SimpleUploadedFile('eggs.cpp', b'weeeee'),
            SimpleUploadedFile('file_42.cpp', b'cppppp'),
            SimpleUploadedFile('file_43.cpp', b'cppppp')
        ]

        self.sandbox = AutograderSandbox()
        self.sandbox.__enter__()

    def tearDown(self):
        super().tearDown()

        self.sandbox.__exit__()

    def test_all_files_added(self):
        files_to_submit = (self.resource_files_to_submit +
                           self.compiled_files_to_submit)

        print(files_to_submit)

        self.do_add_files_submitted_test(files_to_submit)

    def test_no_error_no_files_submitted(self):
        self.do_add_files_submitted_test([])

    def test_no_error_some_files_submitted(self):
        files_to_submit = (self.resource_files_to_submit[:1] +
                           self.compiled_files_to_submit[:1])

        self.do_add_files_submitted_test(files_to_submit)

    def do_add_files_submitted_test(self, files_to_submit):
        submission = ag_models.Submission.objects.validate_and_create(
            submission_group=self.group,
            submitted_files=files_to_submit
        )

        self.ag_test.add_needed_files_to_sandbox(submission, self.sandbox)

        files_added = self.sandbox.run_command(['ls']).stdout.split()
        expected_filenames = itertools.chain(
            (file_.name for file_ in files_to_submit),
            (uploaded_file.name for uploaded_file in self.uploaded_files))
        self.assertCountEqual(expected_filenames, files_added)
