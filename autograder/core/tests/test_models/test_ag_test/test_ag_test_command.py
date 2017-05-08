from django.core import exceptions

import autograder.core.models as ag_models
from autograder.core import constants
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase, generic_data


class _SetUp(generic_data.Project, UnitTestBase):
    def setUp(self):
        super().setUp()

        self.ag_suite = ag_models.AGTestSuite.objects.validate_and_create(
            name='suity', project=self.project)
        self.ag_test = ag_models.AGTestCase.objects.validate_and_create(
            name='testy', ag_test_suite=self.ag_suite)

        self.name = 'cmdy'
        self.cmd = 'echo "waaaluigi"'


class AGTestCommandMiscTestCase(_SetUp):
    def test_valid_create_as_part_of_ag_test(self):
        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd)

        self.assertEqual(self.name, ag_cmd.name)
        self.assertEqual(self.ag_test, ag_cmd.ag_test_case)
        self.assertEqual(self.cmd, ag_cmd.cmd)

    def test_valid_create_as_setup_for_suite(self):
        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_suite_is_setup_for=self.ag_suite, cmd=self.cmd)

        self.assertEqual(self.ag_suite, ag_cmd.ag_test_suite_is_setup_for)

    def test_invalid_create_not_part_of_ag_test_or_setup_for_suite(self):
        with self.assertRaises(exceptions.ValidationError):
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name, cmd=self.cmd)

    def test_default_vals(self):
        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd)

        self.assertEqual(ag_models.StdinSource.none, ag_cmd.stdin_source)
        self.assertIsNone(ag_cmd.stdin_text)
        self.assertIsNone(ag_cmd.stin_project_file)

        self.assertIsNone(ag_cmd.expected_return_code)

        self.assertEqual(ag_models.ExpectedOutputSource.none, ag_cmd.expected_stdout_source)
        self.assertEqual('', ag_cmd.expected_stdout_text)
        self.assertIsNone(ag_cmd.expected_stdout_project_file)

        self.assertEqual(ag_models.ExpectedOutputSource.none, ag_cmd.epected_stderr_source)
        self.assertEqual('', ag_cmd.expected_stderr_text)
        self.assertIsNone(ag_cmd.expected_stderr_project_file)

        self.assertTrue(ag_cmd.normal_fdbk_config.visible)
        self.assertEqual(ag_models.ValueFeedbackLevel.no_feedback,
                         ag_cmd.normal_fdbk_config.return_code_fdbk_level)
        self.assertEqual(ag_models.ValueFeedbackLevel.no_feedback,
                         ag_cmd.normal_fdbk_config.stdout_fdbk_level)
        self.assertEqual(ag_models.ValueFeedbackLevel.no_feedback,
                         ag_cmd.normal_fdbk_config.stderr_fdbk_level)
        self.assertFalse(ag_cmd.normal_fdbk_config.show_points
        self.assertFalse(ag_cmd.normal_fdbk_config.show_actual_return_code
        self.assertFalse(ag_cmd.normal_fdbk_config.show_actual_stdout
        self.assertFalse(ag_cmd.normal_fdbk_config.show_actual_stderr

        self.assertIsNotNone(ag_cmd.ultimate_submission_fdbk_config)
        self.assertIsNotNone(ag_cmd.past_limit_submission_fdbk_config)
        self.assertIsNotNone(ag_cmd.staff_viewer_fdbk_config)

        self.assertFalse(ag_cmd.ignore_case)
        self.assertFalse(ag_cmd.ignore_whitespace)
        self.assertFalse(ag_cmd.ignore_whitespace_changes)
        self.assertFalse(ag_cmd.ignore_blank_lines)

        self.assertEqual(0, ag_cmd.points_for_correct_return_code)
        self.assertEqual(0, ag_cmd.points_for_correct_stdout)
        self.assertEqual(0, ag_cmd.points_for_correct_stderr)
        self.assertEqual(0, ag_cmd.deduction_for_wrong_return_code)
        self.assertEqual(0, ag_cmd.deduction_for_wrong_stdout)
        self.assertEqual(0, ag_cmd.deduction_for_wrong_stderr)

        self.assertEqual(constants.DEFAULT_SUBPROCESS_TIMEOUT, ag_cmd.time_limit)
        self.assertEqual(constants.DEFAULT_STACK_SIZE_LIMIT, ag_cmd.stack_size_limit)
        self.assertEqual(constants.DEFAULT_VIRTUAL_MEM_LIMIT, ag_cmd.virtual_memory_limit)
        self.assertEqual(constants.DEFAULT_PROCESS_LIMIT, ag_cmd.process_spawn_limit)

    def test_some_valid_non_defaults(self):
        points_for_correct_return_code = 1
        points_for_correct_stdout = 2
        points_for_correct_stderr = 3
        deduction_for_wrong_return_code = -1
        deduction_for_wrong_stdout = -2
        deduction_for_wrong_stderr = -3

        expected_return_code = ag_models.ExpectedReturnCode.nonzero

        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
            points_for_correct_return_code=points_for_correct_return_code,
            points_for_correct_stdout=points_for_correct_stdout,
            points_for_correct_stderr=points_for_correct_stderr,
            deduction_for_wrong_return_code=deduction_for_wrong_return_code,
            deduction_for_wrong_stdout=deduction_for_wrong_stdout,
            deduction_for_wrong_stderr=deduction_for_wrong_stderr,
            expected_return_code=expected_return_code)

        self.assertEqual(points_for_correct_return_code, ag_cmd.points_for_correct_return_code)
        self.assertEqual(points_for_correct_stdout, ag_cmd.points_for_correct_stdout)
        self.assertEqual(points_for_correct_stderr, ag_cmd.points_for_correct_stderr)
        self.assertEqual(deduction_for_wrong_return_code, ag_cmd.deduction_for_wrong_return_code)
        self.assertEqual(deduction_for_wrong_stdout, ag_cmd.deduction_for_wrong_stdout)
        self.assertEqual(deduction_for_wrong_stderr, ag_cmd.deduction_for_wrong_stderr)
        self.assertEqual(expected_return_code, ag_cmd.expected_return_code)

    def test_serializable_fields(self):
        self.fail()

    def test_editable_fields(self):
        self.fail()


class ReverseLookupTestCase(_SetUp):
    def test_ag_test_case_ag_test_commands_reverse_lookup_and_ordering(self):
        ag_cmd1 = ag_models.AGTestCommand.objects.validate_and_create(
            name='cmd1', ag_test_case=self.ag_test, cmd=self.cmd)
        ag_cmd2 = ag_models.AGTestCommand.objects.validate_and_create(
            name='cmd2', ag_test_case=self.ag_test, cmd=self.cmd)

        self.assertCountEqual([ag_cmd1, ag_cmd2], self.ag_test.ag_test_commands.all())

        self.ag_test.set_agtestcommand_order([ag_cmd2.pk, ag_cmd1.pk])
        self.assertSequenceEqual([ag_cmd2.pk, ag_cmd1.pk], self.ag_test.get_agtestcommand_order)

        self.ag_test.set_agtestcommand_order([ag_cmd1.pk, ag_cmd2.pk])
        self.assertSequenceEqual([ag_cmd1.pk, ag_cmd2.pk], self.ag_test.get_agtestcommand_order)

    def test_suite_setup_command_reverse_lookup(self):
        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_suite_is_setup_for=self.ag_suite, cmd=self.cmd)
        self.assertEqual(ag_cmd, self.ag_suite.setup_command)


class IOSettingsTestCase(_SetUp):
    def test_text_io_sources(self):
        stdin = 'spam'
        stdout = 'egg'
        stderr = 'sausage'
        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
            stdin_source=ag_models.StdinSource.text,
            stdin_text=stdin,
            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stdout_text=stdout,
            expected_stderr_source=ag_models.ExpectedOutputSource.text.text,
            expected_stderr_text=stderr)

        self.assertEqual(ag_models.StdinSource.text, ag_cmd.stdin_source)
        self.assertEqual(stdin, ag_cmd.stdin_text)
        self.assertEqual(ag_models.ExpectedOutputSource.text, ag_cmd.expected_stdout_source)
        self.assertEqual(stdout, ag_cmd.expected_stdout_text)
        self.assertEqual(ag_models.ExpectedOutputSource.text, ag_cmd.expected_stderr_source)
        self.assertEqual(stderr, ag_cmd.expected_stderr_text)

    def test_error_missing_stdin_project_file(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
                stdin_source=ag_models.StdinSource.project_file)

        self.assertIn('stdin_project_file', cm.exception.message_dict)

    def test_error_missing_expected_stdout_project_file(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
                expected_stdout_source=ag_models.ExpectedOutputSource.project_file)

        self.assertIn('expected_stdout_project_file', cm.exception.message_dict)

    def test_error_missing_expected_stderr_project_file(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
                expected_stderr_source=ag_models.ExpectedOutputSource.project_file)

        self.assertIn('expected_stderr_project_file', cm.exception.message_dict)

    def test_error_invalid_io_options(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
                stdin_source='not_a_source',
                expected_stdout_source='no_way',
                expected_stderr_source='definitely_not')

        self.assertIn('stdin_source', cm.exception.message_dict)
        self.assertIn('expected_stdout_source', cm.exception.message_dict)
        self.assertIn('expected_stderr_source', cm.exception.message_dict)

    # TODO: add setting for max file size, enforce in UploadedFile
    def test_error_expected_output_text_too_large(self):
        too_much_text = 'A' * (constants.MAX_OUTPUT_LENGTH + 1)
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
                expected_stdout_source=ag_models.ExpectedOutputSource.text,
                expected_stdout_text=too_much_text,
                expected_stderr_source=ag_models.ExpectedOutputSource.text.text,
                expected_stderr_text=too_much_text)

        self.assertIn('expected_stdout_text', cm.exception.message_dict)
        self.assertIn('expected_stderr_text', cm.exception.message_dict)


class MiscErrorTestCase(_SetUp):
    def test_error_name_not_unique(self):
        self.fail()

    def test_error_name_empty_or_null(self):
        self.fail()

    def test_error_empty_cmd(self):
        self.fail()

    def test_error_points_out_of_range(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
                points_for_correct_return_code=-1,
                points_for_correct_stdout=-1,
                points_for_correct_stderr=-1,
                deduction_for_wrong_return_code=1,
                deduction_for_wrong_stdout=1,
                deduction_for_wrong_stderr=1)

        self.assertIn('points_for_correct_return_code', cm.exception.message_dict)
        self.assertIn('points_for_correct_stdout', cm.exception.message_dict)
        self.assertIn('points_for_correct_stderr', cm.exception.message_dict)
        self.assertIn('deduction_for_wrong_return_code', cm.exception.message_dict)
        self.assertIn('deduction_for_wrong_stdout', cm.exception.message_dict)
        self.assertIn('deduction_for_wrong_stderr', cm.exception.message_dict)

    def test_error_resource_limits_out_of_range(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
                points_for_correct_return_code=-1,
                time_limit=-1,
                stack_size_limit=-1,
                virtual_memory_limit=-1,
                process_spawn_limit=-1,
            )

        self.assertIn('points_for_correct_return_code', cm.exception.message_dict)
        self.assertIn('time_limit', cm.exception.message_dict)
        self.assertIn('stack_size_limit', cm.exception.message_dict)
        self.assertIn('virtual_memory_limit', cm.exception.message_dict)
        self.assertIn('process_spawn_limit', cm.exception.message_dict)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
                points_for_correct_return_code
            time_limit
            stack_size_limit
            virtual_memory_limit
            process_spawn_limit
            )

        self.assertIn('points_for_correct_return_code', cm.exception.message_dict)
        self.assertIn('time_limit', cm.exception.message_dict)
        self.assertIn('stack_size_limit', cm.exception.message_dict)
        self.assertIn('virtual_memory_limit', cm.exception.message_dict)
        self.assertIn('process_spawn_limit', cm.exception.message_dict)

        self.fail()


# class AGTestOutputLimitTestCase(UnitTestBase):
#     def setUp(self):
#         self.project = obj_build.build_project()
#
#         self.output = 'A' * (const.MAX_OUTPUT_LENGTH + 1)
#
#     def test_expected_stdout_too_long(self):
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             _DummyAutograderTestCase.objects.validate_and_create(
#                 name='Too Much Output :o', project=self.project,
#                 expected_standard_output=self.output)
#
#         self.assertIn('expected_standard_output', cm.exception.message_dict)
#
#     def test_expected_stderr_too_long(self):
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             _DummyAutograderTestCase.objects.validate_and_create(
#                 name='Too Much Error :o', project=self.project,
#                 expected_standard_error_output=self.output)
#
#         self.assertIn('expected_standard_error_output', cm.exception.message_dict)

#
# class AGTestResourceLimitErrorTestCase(_Shared, UnitTestBase):
#     def test_exception_on_zero_time_limit(self):
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             _DummyAutograderTestCase.objects.validate_and_create(
#                 name=self.TEST_NAME, project=self.project,
#                 time_limit=0)
#
#         self.assertTrue('time_limit' in cm.exception.message_dict)
#
#     def test_exception_on_negative_time_limit(self):
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             _DummyAutograderTestCase.objects.validate_and_create(
#                 name=self.TEST_NAME, project=self.project,
#                 time_limit=-1)
#
#         self.assertTrue('time_limit' in cm.exception.message_dict)
#
#     def test_exception_on_time_limit_too_large(self):
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             _DummyAutograderTestCase.objects.validate_and_create(
#                 name=self.TEST_NAME, project=self.project,
#                 time_limit=const.MAX_SUBPROCESS_TIMEOUT + 1)
#
#         self.assertTrue('time_limit' in cm.exception.message_dict)
#
#     def test_exception_on_time_limit_not_integer(self):
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             _DummyAutograderTestCase.objects.validate_and_create(
#                 name=self.TEST_NAME, project=self.project,
#                 time_limit='spam')
#
#         self.assertTrue('time_limit' in cm.exception.message_dict)
#
#     def test_no_exception_on_time_limit_is_parseable_int(self):
#         ag_test = _DummyAutograderTestCase.objects.validate_and_create(
#             name=self.TEST_NAME, project=self.project,
#             time_limit='2')
#
#         ag_test.refresh_from_db()
#         self.assertEqual(ag_test.time_limit, 2)
#
#     # -------------------------------------------------------------------------
#
#     def test_exception_negative_stack_size_limit(self):
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             _DummyAutograderTestCase.objects.validate_and_create(
#                 name=self.TEST_NAME, project=self.project,
#                 stack_size_limit=-1)
#
#         self.assertTrue('stack_size_limit' in cm.exception.message_dict)
#
#     def test_exception_zero_stack_size_limit(self):
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             _DummyAutograderTestCase.objects.validate_and_create(
#                 name=self.TEST_NAME, project=self.project,
#                 stack_size_limit=0)
#
#         self.assertTrue('stack_size_limit' in cm.exception.message_dict)
#
#     def test_exception_stack_size_limit_too_large(self):
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             _DummyAutograderTestCase.objects.validate_and_create(
#                 name=self.TEST_NAME, project=self.project,
#                 stack_size_limit=const.MAX_STACK_SIZE_LIMIT + 1)
#
#         self.assertTrue('stack_size_limit' in cm.exception.message_dict)
#
#     # -------------------------------------------------------------------------
#
#     def test_exception_negative_virtual_memory_limit(self):
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             _DummyAutograderTestCase.objects.validate_and_create(
#                 name=self.TEST_NAME, project=self.project,
#                 virtual_memory_limit=-1)
#
#         self.assertTrue('virtual_memory_limit' in cm.exception.message_dict)
#
#     def test_exception_zero_virtual_memory_limit(self):
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             _DummyAutograderTestCase.objects.validate_and_create(
#                 name=self.TEST_NAME, project=self.project,
#                 virtual_memory_limit=0)
#
#         self.assertTrue('virtual_memory_limit' in cm.exception.message_dict)
#
#     def test_exception_virtual_mem_limit_too_large(self):
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             _DummyAutograderTestCase.objects.validate_and_create(
#                 name=self.TEST_NAME, project=self.project,
#                 virtual_memory_limit=const.MAX_VIRTUAL_MEM_LIMIT + 1)
#
#         self.assertTrue('virtual_memory_limit' in cm.exception.message_dict)
#
#     # -------------------------------------------------------------------------
#
#     def test_exception_negative_process_limit(self):
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             _DummyAutograderTestCase.objects.validate_and_create(
#                 name=self.TEST_NAME, project=self.project,
#                 process_spawn_limit=-1)
#
#         self.assertTrue('process_spawn_limit' in cm.exception.message_dict)
#
#     def test_exception_process_limit_too_large(self):
#         with self.assertRaises(exceptions.ValidationError) as cm:
#             _DummyAutograderTestCase.objects.validate_and_create(
#                 name=self.TEST_NAME, project=self.project,
#                 process_spawn_limit=const.MAX_PROCESS_LIMIT + 1)
#
#         self.assertTrue('process_spawn_limit' in cm.exception.message_dict)
#
