import copy

from django.core import exceptions

import autograder.core.models as ag_models
from autograder.core import constants
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.utils.testing import UnitTestBase


class AGTestCommandMiscTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.project = obj_build.build_project()

        self.ag_suite = ag_models.AGTestSuite.objects.validate_and_create(
            name='suity', project=self.project)
        self.ag_test = ag_models.AGTestCase.objects.validate_and_create(
            name='testy', ag_test_suite=self.ag_suite)

        self.name = 'cmdy'
        self.cmd = 'echo "waaaluigi"'

    def test_valid_create_as_part_of_ag_test(self):
        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd)

        self.assertEqual(self.name, ag_cmd.name)
        self.assertEqual(self.ag_test, ag_cmd.ag_test_case)
        self.assertEqual(self.cmd, ag_cmd.cmd)

    def test_invalid_create_not_part_of_ag_test_case(self):
        with self.assertRaises(exceptions.ValidationError):
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name, cmd=self.cmd)

    def test_default_vals(self):
        ag_cmd: ag_models.AGTestCommand = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd)

        self.assertEqual(ag_models.StdinSource.none, ag_cmd.stdin_source)
        self.assertEqual('', ag_cmd.stdin_text)
        self.assertIsNone(ag_cmd.stdin_instructor_file)

        self.assertEqual(ag_models.ExpectedReturnCode.none, ag_cmd.expected_return_code)

        self.assertEqual(ag_models.ExpectedOutputSource.none, ag_cmd.expected_stdout_source)
        self.assertEqual('', ag_cmd.expected_stdout_text)
        self.assertIsNone(ag_cmd.expected_stdout_instructor_file)

        self.assertEqual(ag_models.ExpectedOutputSource.none, ag_cmd.expected_stderr_source)
        self.assertEqual('', ag_cmd.expected_stderr_text)
        self.assertIsNone(ag_cmd.expected_stderr_instructor_file)

        self.assertIsNone(ag_cmd.first_failed_test_normal_fdbk_config)

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

    def test_normal_fdbk_default(self):
        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd)

        self.assertTrue(ag_cmd.normal_fdbk_config.visible)
        self.assertEqual(ag_models.ValueFeedbackLevel.no_feedback,
                         ag_cmd.normal_fdbk_config.return_code_fdbk_level)
        self.assertEqual(ag_models.ValueFeedbackLevel.no_feedback,
                         ag_cmd.normal_fdbk_config.stdout_fdbk_level)
        self.assertEqual(ag_models.ValueFeedbackLevel.no_feedback,
                         ag_cmd.normal_fdbk_config.stderr_fdbk_level)
        self.assertFalse(ag_cmd.normal_fdbk_config.show_points)
        self.assertFalse(ag_cmd.normal_fdbk_config.show_actual_return_code)
        self.assertFalse(ag_cmd.normal_fdbk_config.show_actual_stdout)
        self.assertFalse(ag_cmd.normal_fdbk_config.show_actual_stderr)
        self.assertFalse(ag_cmd.normal_fdbk_config.show_whether_timed_out)

    def test_ultimate_fdbk_default(self):
        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd)

        self.assertTrue(ag_cmd.ultimate_submission_fdbk_config.visible)
        self.assertEqual(ag_models.ValueFeedbackLevel.correct_or_incorrect,
                         ag_cmd.ultimate_submission_fdbk_config.return_code_fdbk_level)
        self.assertEqual(ag_models.ValueFeedbackLevel.correct_or_incorrect,
                         ag_cmd.ultimate_submission_fdbk_config.stdout_fdbk_level)
        self.assertEqual(ag_models.ValueFeedbackLevel.correct_or_incorrect,
                         ag_cmd.ultimate_submission_fdbk_config.stderr_fdbk_level)
        self.assertTrue(ag_cmd.ultimate_submission_fdbk_config.show_points)
        self.assertTrue(ag_cmd.ultimate_submission_fdbk_config.show_actual_return_code)
        self.assertFalse(ag_cmd.ultimate_submission_fdbk_config.show_actual_stdout)
        self.assertFalse(ag_cmd.ultimate_submission_fdbk_config.show_actual_stderr)
        self.assertTrue(ag_cmd.ultimate_submission_fdbk_config.show_whether_timed_out)

    def test_past_limit_fdbk_default(self):
        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd)

        self.assertTrue(ag_cmd.past_limit_submission_fdbk_config.visible)
        self.assertEqual(ag_models.ValueFeedbackLevel.no_feedback,
                         ag_cmd.past_limit_submission_fdbk_config.return_code_fdbk_level)
        self.assertEqual(ag_models.ValueFeedbackLevel.no_feedback,
                         ag_cmd.past_limit_submission_fdbk_config.stdout_fdbk_level)
        self.assertEqual(ag_models.ValueFeedbackLevel.no_feedback,
                         ag_cmd.past_limit_submission_fdbk_config.stderr_fdbk_level)
        self.assertFalse(ag_cmd.past_limit_submission_fdbk_config.show_points)
        self.assertFalse(ag_cmd.past_limit_submission_fdbk_config.show_actual_return_code)
        self.assertFalse(ag_cmd.past_limit_submission_fdbk_config.show_actual_stdout)
        self.assertFalse(ag_cmd.past_limit_submission_fdbk_config.show_actual_stderr)
        self.assertFalse(ag_cmd.past_limit_submission_fdbk_config.show_whether_timed_out)

    def test_staff_viewer_fdbk_default(self):
        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd)

        self.assertTrue(ag_cmd.staff_viewer_fdbk_config.visible)
        self.assertEqual(ag_models.ValueFeedbackLevel.expected_and_actual,
                         ag_cmd.staff_viewer_fdbk_config.return_code_fdbk_level)
        self.assertEqual(ag_models.ValueFeedbackLevel.expected_and_actual,
                         ag_cmd.staff_viewer_fdbk_config.stdout_fdbk_level)
        self.assertEqual(ag_models.ValueFeedbackLevel.expected_and_actual,
                         ag_cmd.staff_viewer_fdbk_config.stderr_fdbk_level)
        self.assertTrue(ag_cmd.staff_viewer_fdbk_config.show_points)
        self.assertTrue(ag_cmd.staff_viewer_fdbk_config.show_actual_return_code)
        self.assertTrue(ag_cmd.staff_viewer_fdbk_config.show_actual_stdout)
        self.assertTrue(ag_cmd.staff_viewer_fdbk_config.show_actual_stderr)
        self.assertTrue(ag_cmd.staff_viewer_fdbk_config.show_whether_timed_out)

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

    def test_normal_fdbk_non_default(self):
        fdbk_settings = {
            'return_code_fdbk_level': ag_models.ValueFeedbackLevel.expected_and_actual,
            'stdout_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
            'stderr_fdbk_level': ag_models.ValueFeedbackLevel.expected_and_actual,
            'show_points': False,
            'show_actual_return_code': True,
            'show_actual_stdout': False,
            'show_actual_stderr': True,
            'show_whether_timed_out': False
        }

        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
            normal_fdbk_config=fdbk_settings
        )

        for field_name, value in fdbk_settings.items():
            self.assertEqual(value, getattr(ag_cmd.normal_fdbk_config, field_name))

    def test_first_failure_fdbk_non_default(self):
        fdbk_settings = {
            'return_code_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
            'stdout_fdbk_level': ag_models.ValueFeedbackLevel.expected_and_actual,
            'stderr_fdbk_level': ag_models.ValueFeedbackLevel.expected_and_actual,
            'show_points': True,
            'show_actual_return_code': True,
            'show_actual_stdout': True,
            'show_actual_stderr': False,
            'show_whether_timed_out': False
        }

        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
            first_failed_test_normal_fdbk_config=fdbk_settings
        )

        for field_name, value in fdbk_settings.items():
            self.assertEqual(value,
                             getattr(ag_cmd.first_failed_test_normal_fdbk_config, field_name))

    def test_ultimate_fdbk_non_default(self):
        fdbk_settings = {
            'return_code_fdbk_level': ag_models.ValueFeedbackLevel.expected_and_actual,
            'stdout_fdbk_level': ag_models.ValueFeedbackLevel.no_feedback,
            'stderr_fdbk_level': ag_models.ValueFeedbackLevel.no_feedback,
            'show_points': False,
            'show_actual_return_code': True,
            'show_actual_stdout': True,
            'show_actual_stderr': False,
            'show_whether_timed_out': True
        }

        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
            ultimate_submission_fdbk_config=fdbk_settings
        )

        for field_name, value in fdbk_settings.items():
            self.assertEqual(value, getattr(ag_cmd.ultimate_submission_fdbk_config, field_name))

    def test_staff_viewer_fdbk_non_default(self):
        fdbk_settings = {
            'return_code_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
            'stdout_fdbk_level': ag_models.ValueFeedbackLevel.expected_and_actual,
            'stderr_fdbk_level': ag_models.ValueFeedbackLevel.no_feedback,
            'show_points': True,
            'show_actual_return_code': True,
            'show_actual_stdout': True,
            'show_actual_stderr': False,
            'show_whether_timed_out': False
        }

        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
            past_limit_submission_fdbk_config=fdbk_settings
        )

        for field_name, value in fdbk_settings.items():
            self.assertEqual(value, getattr(ag_cmd.past_limit_submission_fdbk_config, field_name))

    def test_past_limit_fdbk_non_default(self):
        fdbk_settings = {
            'return_code_fdbk_level': ag_models.ValueFeedbackLevel.correct_or_incorrect,
            'stdout_fdbk_level': ag_models.ValueFeedbackLevel.no_feedback,
            'stderr_fdbk_level': ag_models.ValueFeedbackLevel.expected_and_actual,
            'show_points': False,
            'show_actual_return_code': True,
            'show_actual_stdout': False,
            'show_actual_stderr': True,
            'show_whether_timed_out': False
        }

        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
            past_limit_submission_fdbk_config=fdbk_settings
        )

        for field_name, value in fdbk_settings.items():
            self.assertEqual(value, getattr(ag_cmd.past_limit_submission_fdbk_config, field_name))

    def test_ag_test_case_ag_test_commands_reverse_lookup_and_ordering(self):
        ag_cmd1 = ag_models.AGTestCommand.objects.validate_and_create(
            name='cmd1', ag_test_case=self.ag_test, cmd=self.cmd)
        ag_cmd2 = ag_models.AGTestCommand.objects.validate_and_create(
            name='cmd2', ag_test_case=self.ag_test, cmd=self.cmd)

        self.assertCountEqual([ag_cmd1, ag_cmd2], self.ag_test.ag_test_commands.all())

        self.ag_test.set_agtestcommand_order([ag_cmd2.pk, ag_cmd1.pk])
        self.assertSequenceEqual([ag_cmd2.pk, ag_cmd1.pk], self.ag_test.get_agtestcommand_order())

        self.ag_test.set_agtestcommand_order([ag_cmd1.pk, ag_cmd2.pk])
        self.assertSequenceEqual([ag_cmd1.pk, ag_cmd2.pk], self.ag_test.get_agtestcommand_order())

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

    def test_file_io_sources(self):
        stdin = obj_build.make_instructor_file(self.project)
        stdout = obj_build.make_instructor_file(self.project)
        stderr = obj_build.make_instructor_file(self.project)
        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
            stdin_source=ag_models.StdinSource.instructor_file,
            stdin_instructor_file=stdin,
            expected_stdout_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stdout_instructor_file=stdout,
            expected_stderr_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stderr_instructor_file=stderr)

        self.assertEqual(stdin, ag_cmd.stdin_instructor_file)
        self.assertEqual(stdout, ag_cmd.expected_stdout_instructor_file)
        self.assertEqual(stderr, ag_cmd.expected_stderr_instructor_file)

    def test_error_stdin_instructor_file_belongs_to_other_project(self):
        other_project = obj_build.make_project(course=self.project.course)
        other_instructor_file = obj_build.make_instructor_file(project=other_project)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name,
                ag_test_case=self.ag_test,
                cmd='true',
                stdin_source=ag_models.StdinSource.instructor_file,
                stdin_instructor_file=other_instructor_file)

        self.assertIn('stdin_instructor_file', cm.exception.message_dict)

    def test_error_expected_stdout_instructor_file_belongs_to_other_project(self):
        other_project = obj_build.make_project(course=self.project.course)
        other_instructor_file = obj_build.make_instructor_file(project=other_project)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name,
                ag_test_case=self.ag_test,
                cmd='true',
                expected_stdout_source=ag_models.ExpectedOutputSource.instructor_file,
                expected_stdout_instructor_file=other_instructor_file)

        self.assertIn('expected_stdout_instructor_file', cm.exception.message_dict)

    def test_error_expected_stderr_instructor_file_belongs_to_other_project(self):
        other_project = obj_build.make_project(course=self.project.course)
        other_instructor_file = obj_build.make_instructor_file(project=other_project)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name,
                ag_test_case=self.ag_test,
                cmd='true',
                expected_stderr_source=ag_models.ExpectedOutputSource.instructor_file,
                expected_stderr_instructor_file=other_instructor_file)

        self.assertIn('expected_stderr_instructor_file', cm.exception.message_dict)

    def test_error_missing_stdin_instructor_file(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
                stdin_source=ag_models.StdinSource.instructor_file)

        self.assertIn('stdin_instructor_file', cm.exception.message_dict)

    def test_error_missing_expected_stdout_instructor_file(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
                expected_stdout_source=ag_models.ExpectedOutputSource.instructor_file)

        self.assertIn('expected_stdout_instructor_file', cm.exception.message_dict)

    def test_error_missing_expected_stderr_instructor_file(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
                expected_stderr_source=ag_models.ExpectedOutputSource.instructor_file)

        self.assertIn('expected_stderr_instructor_file', cm.exception.message_dict)

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

    def test_error_name_not_unique(self):
        ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd)
        with self.assertRaises(exceptions.ValidationError):
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name, ag_test_case=self.ag_test, cmd=self.cmd)

    def test_error_name_empty_or_null(self):
        for bad_name in ['', None]:
            with self.assertRaises(exceptions.ValidationError) as cm:
                ag_models.AGTestCommand.objects.validate_and_create(
                    name=bad_name, ag_test_case=self.ag_test, cmd=self.cmd)

            self.assertIn('name', cm.exception.message_dict)

    def test_error_empty_cmd(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name, ag_test_case=self.ag_test, cmd='')

        self.assertIn('cmd', cm.exception.message_dict)

    def test_error_invalid_expected_return_code(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
                expected_return_code='forget_about_it')

        self.assertIn('expected_return_code', cm.exception.message_dict)

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
                time_limit=-1,
                stack_size_limit=-1,
                virtual_memory_limit=-1,
                process_spawn_limit=-1,
            )

        self.assertIn('time_limit', cm.exception.message_dict)
        self.assertIn('stack_size_limit', cm.exception.message_dict)
        self.assertIn('virtual_memory_limit', cm.exception.message_dict)
        self.assertIn('process_spawn_limit', cm.exception.message_dict)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGTestCommand.objects.validate_and_create(
                name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
                time_limit=constants.MAX_SUBPROCESS_TIMEOUT + 1,
                stack_size_limit=constants.MAX_STACK_SIZE_LIMIT + 1,
                virtual_memory_limit=constants.MAX_VIRTUAL_MEM_LIMIT + 1,
                process_spawn_limit=constants.MAX_PROCESS_LIMIT + 1)

        self.assertIn('time_limit', cm.exception.message_dict)
        self.assertIn('stack_size_limit', cm.exception.message_dict)
        self.assertIn('virtual_memory_limit', cm.exception.message_dict)
        self.assertIn('process_spawn_limit', cm.exception.message_dict)

    def test_serialize(self):
        expected_keys = [
            'pk',
            'name',
            'ag_test_case',
            'last_modified',
            'cmd',

            'stdin_source',
            'stdin_text',
            'stdin_instructor_file',

            'expected_return_code',

            'expected_stdout_source',
            'expected_stdout_text',
            'expected_stdout_instructor_file',

            'expected_stderr_source',
            'expected_stderr_text',
            'expected_stderr_instructor_file',

            'ignore_case',
            'ignore_whitespace',
            'ignore_whitespace_changes',
            'ignore_blank_lines',

            'points_for_correct_return_code',
            'points_for_correct_stdout',
            'points_for_correct_stderr',
            'deduction_for_wrong_return_code',
            'deduction_for_wrong_stdout',
            'deduction_for_wrong_stderr',

            'normal_fdbk_config',
            'first_failed_test_normal_fdbk_config',
            'ultimate_submission_fdbk_config',
            'past_limit_submission_fdbk_config',
            'staff_viewer_fdbk_config',

            'time_limit',
            'stack_size_limit',
            'virtual_memory_limit',
            'process_spawn_limit',
        ]
        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
            first_failed_test_normal_fdbk_config={}
        )

        cmd_dict = ag_cmd.to_dict()

        self.assertCountEqual(expected_keys, cmd_dict.keys())

        fdbk_config_keys = ['normal_fdbk_config',
                            'first_failed_test_normal_fdbk_config',
                            'ultimate_submission_fdbk_config',
                            'past_limit_submission_fdbk_config',
                            'staff_viewer_fdbk_config']
        for key in fdbk_config_keys:
            self.assertIsInstance(cmd_dict[key], dict)

            self.assertIsInstance(cmd_dict[key]['return_code_fdbk_level'], str)
            self.assertIsInstance(cmd_dict[key]['stdout_fdbk_level'], str)
            self.assertIsInstance(cmd_dict[key]['stderr_fdbk_level'], str)

        self.assertIsInstance(cmd_dict['stdin_source'], str)
        self.assertIsInstance(cmd_dict['expected_return_code'], str)
        self.assertIsInstance(cmd_dict['expected_stdout_source'], str)
        self.assertIsInstance(cmd_dict['expected_stderr_source'], str)

        editable_dict = copy.deepcopy(cmd_dict)
        for non_editable in ['pk', 'last_modified', 'ag_test_case']:
            editable_dict.pop(non_editable)

        ag_cmd.validate_and_update(**editable_dict)

        # Serialize with first_failed_test_normal_fdbk_config = None
        ag_cmd.validate_and_update(first_failed_test_normal_fdbk_config=None)
        self.assertIsNone(ag_cmd.to_dict()['first_failed_test_normal_fdbk_config'])

    def test_file_io_sources_serialized(self):
        stdin = obj_build.make_instructor_file(self.project)
        stdout = obj_build.make_instructor_file(self.project)
        stderr = obj_build.make_instructor_file(self.project)
        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
            stdin_instructor_file=stdin,
            expected_stdout_instructor_file=stdout,
            expected_stderr_instructor_file=stderr)

        cmd_dict = ag_cmd.to_dict()

        self.assertIsInstance(cmd_dict['stdin_instructor_file'], dict)
        self.assertEqual(stdin.pk, cmd_dict['stdin_instructor_file']['pk'])
        self.assertIsInstance(cmd_dict['expected_stdout_instructor_file'], dict)
        self.assertEqual(stdout.pk, cmd_dict['expected_stdout_instructor_file']['pk'])
        self.assertIsInstance(cmd_dict['expected_stderr_instructor_file'], dict)
        self.assertEqual(stderr.pk, cmd_dict['expected_stderr_instructor_file']['pk'])

    def test_file_io_sources_deserialized_on_create(self):
        stdin = obj_build.make_instructor_file(self.project)
        stdout = obj_build.make_instructor_file(self.project)
        stderr = obj_build.make_instructor_file(self.project)

        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
            stdin_source=ag_models.StdinSource.instructor_file,
            stdin_instructor_file=stdin.to_dict(),
            expected_stdout_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stdout_instructor_file=stdout.to_dict(),
            expected_stderr_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stderr_instructor_file=stderr.to_dict())

        self.assertEqual(stdin, ag_cmd.stdin_instructor_file)
        self.assertEqual(stdout, ag_cmd.expected_stdout_instructor_file)
        self.assertEqual(stderr, ag_cmd.expected_stderr_instructor_file)

    def test_file_io_sources_deserialized_on_update(self):
        stdin = obj_build.make_instructor_file(self.project)
        stdout = obj_build.make_instructor_file(self.project)
        stderr = obj_build.make_instructor_file(self.project)

        ag_cmd = ag_models.AGTestCommand.objects.validate_and_create(
            name=self.name, ag_test_case=self.ag_test, cmd=self.cmd,
            stdin_source=ag_models.StdinSource.instructor_file,
            stdin_instructor_file=stdin,
            expected_stdout_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stdout_instructor_file=stdout,
            expected_stderr_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stderr_instructor_file=stderr)

        self.assertEqual(stdin, ag_cmd.stdin_instructor_file)
        self.assertEqual(stdout, ag_cmd.expected_stdout_instructor_file)
        self.assertEqual(stderr, ag_cmd.expected_stderr_instructor_file)

        ag_cmd.validate_and_update(
            stdin_source=ag_models.StdinSource.none,
            stdin_instructor_file=None,
            expected_stdout_source=ag_models.ExpectedOutputSource.none,
            expected_stdout_instructor_file=None,
            expected_stderr_source=ag_models.ExpectedOutputSource.none,
            expected_stderr_instructor_file=None,
        )

        self.assertIsNone(ag_cmd.stdin_instructor_file)
        self.assertIsNone(ag_cmd.expected_stdout_instructor_file)
        self.assertIsNone(ag_cmd.expected_stderr_instructor_file)

        ag_cmd.validate_and_update(
            stdin_source=ag_models.StdinSource.instructor_file,
            stdin_instructor_file=stdin.to_dict(),
            expected_stdout_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stdout_instructor_file=stdout.to_dict(),
            expected_stderr_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stderr_instructor_file=stderr.to_dict())

        self.assertEqual(stdin, ag_cmd.stdin_instructor_file)
        self.assertEqual(stdout, ag_cmd.expected_stdout_instructor_file)
        self.assertEqual(stderr, ag_cmd.expected_stderr_instructor_file)


class InstructorFileDeleteBehaviorTestCase(UnitTestBase):
    """
    Regression tests for https://github.com/eecs-autograder/autograder-server/issues/403
    """
    def setUp(self):
        super().setUp()

        self.ag_test_command = obj_build.make_full_ag_test_command(
            set_arbitrary_points=False, set_arbitrary_expected_vals=False)
        self.project = self.ag_test_command.ag_test_case.ag_test_suite.project

        self.instructor_file_to_delete = obj_build.make_instructor_file(self.project)

        self.instructor_file_to_keep = obj_build.make_instructor_file(self.project)

    def test_deleting_instructor_file_does_not_delete_commands_that_use_it_as_stdin(self):
        self.ag_test_command.validate_and_update(
            stdin_source=ag_models.StdinSource.instructor_file,
            stdin_instructor_file=self.instructor_file_to_delete,

            expected_stdout_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stdout_instructor_file=self.instructor_file_to_keep,

            expected_stderr_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stderr_instructor_file=self.instructor_file_to_keep
        )

        self.instructor_file_to_delete.delete()

        self.ag_test_command.refresh_from_db()

        self.assertEqual(ag_models.StdinSource.none, self.ag_test_command.stdin_source)
        self.assertIsNone(self.ag_test_command.stdin_instructor_file)

        self.assertEqual(ag_models.ExpectedOutputSource.instructor_file,
                         self.ag_test_command.expected_stdout_source)
        self.assertIsNotNone(self.ag_test_command.expected_stdout_instructor_file)

        self.assertEqual(ag_models.ExpectedOutputSource.instructor_file,
                         self.ag_test_command.expected_stderr_source)
        self.assertIsNotNone(self.ag_test_command.expected_stderr_instructor_file)

    def test_deleting_instructor_file_does_not_delete_commands_that_use_it_as_stdout(self):
        self.ag_test_command.validate_and_update(
            stdin_source=ag_models.StdinSource.instructor_file,
            stdin_instructor_file=self.instructor_file_to_keep,

            expected_stdout_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stdout_instructor_file=self.instructor_file_to_delete,

            expected_stderr_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stderr_instructor_file=self.instructor_file_to_keep
        )

        self.instructor_file_to_delete.delete()

        self.ag_test_command.refresh_from_db()

        self.assertEqual(ag_models.StdinSource.instructor_file, self.ag_test_command.stdin_source)
        self.assertIsNotNone(self.ag_test_command.stdin_instructor_file)

        self.assertEqual(ag_models.ExpectedOutputSource.none,
                         self.ag_test_command.expected_stdout_source)
        self.assertIsNone(self.ag_test_command.expected_stdout_instructor_file)

        self.assertEqual(ag_models.ExpectedOutputSource.instructor_file,
                         self.ag_test_command.expected_stderr_source)
        self.assertIsNotNone(self.ag_test_command.expected_stderr_instructor_file)

    def test_deleting_instructor_file_does_not_delete_commands_that_use_it_as_stderr(self):
        self.ag_test_command.validate_and_update(
            stdin_source=ag_models.StdinSource.instructor_file,
            stdin_instructor_file=self.instructor_file_to_keep,

            expected_stdout_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stdout_instructor_file=self.instructor_file_to_keep,

            expected_stderr_source=ag_models.ExpectedOutputSource.instructor_file,
            expected_stderr_instructor_file=self.instructor_file_to_delete
        )

        self.instructor_file_to_delete.delete()

        self.ag_test_command.refresh_from_db()

        self.assertEqual(ag_models.StdinSource.instructor_file, self.ag_test_command.stdin_source)
        self.assertIsNotNone(self.ag_test_command.stdin_instructor_file)

        self.assertEqual(ag_models.ExpectedOutputSource.instructor_file,
                         self.ag_test_command.expected_stdout_source)
        self.assertIsNotNone(self.ag_test_command.expected_stdout_instructor_file)

        self.assertEqual(ag_models.ExpectedOutputSource.none,
                         self.ag_test_command.expected_stderr_source)
        self.assertIsNone(self.ag_test_command.expected_stderr_instructor_file)

    def test_stdin_stdout_stderr_source_only_set_to_none_if_source_is_instructor_file(self):
        """
        It's possible for users to set a stdin instructor file even
        if the source is set to something else (like text). This
        test makes sure that the delete() behavior for InstructorFile
        only sets the stdin/stdout/stderr source setting to none
        if it is currently set to instructor_file.
        """
        self.ag_test_command.validate_and_update(
            stdin_source=ag_models.StdinSource.text,
            stdin_instructor_file=self.instructor_file_to_delete,

            expected_stdout_source=ag_models.ExpectedOutputSource.text,
            expected_stdout_instructor_file=self.instructor_file_to_delete,

            expected_stderr_source=ag_models.ExpectedOutputSource.text,
            expected_stderr_instructor_file=self.instructor_file_to_delete
        )

        self.instructor_file_to_delete.delete()

        self.ag_test_command.refresh_from_db()

        self.assertEqual(ag_models.StdinSource.text, self.ag_test_command.stdin_source)
        self.assertIsNone(self.ag_test_command.stdin_instructor_file)

        self.assertEqual(ag_models.ExpectedOutputSource.text,
                         self.ag_test_command.expected_stdout_source)
        self.assertIsNone(self.ag_test_command.expected_stdout_instructor_file)

        self.assertEqual(ag_models.ExpectedOutputSource.text,
                         self.ag_test_command.expected_stderr_source)
        self.assertIsNone(self.ag_test_command.expected_stderr_instructor_file)
