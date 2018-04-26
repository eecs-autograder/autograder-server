from django.core import exceptions

import autograder.core.models as ag_models
from autograder.core import constants
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class AGCommandTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.cmd = 'echo spam'

    def test_init_default_values(self):
        cmd = ag_models.AGCommand.objects.validate_and_create(
            cmd=self.cmd
        )  # type: ag_models.AGCommand

        self.assertEqual('', cmd.name)
        self.assertEqual(self.cmd, cmd.cmd)
        self.assertEqual(constants.DEFAULT_SUBPROCESS_TIMEOUT, cmd.time_limit)
        self.assertEqual(constants.DEFAULT_STACK_SIZE_LIMIT, cmd.stack_size_limit)
        self.assertEqual(constants.DEFAULT_VIRTUAL_MEM_LIMIT, cmd.virtual_memory_limit)
        self.assertEqual(constants.DEFAULT_PROCESS_LIMIT, cmd.process_spawn_limit)

    def test_error_cmd_empty(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGCommand.objects.validate_and_create()

        self.assertIn('cmd', cm.exception.message_dict)

        cmd = ag_models.AGCommand.objects.validate_and_create(cmd=self.cmd)
        with self.assertRaises(exceptions.ValidationError) as cm:
            cmd.validate_and_update(cmd='')

        self.assertIn('cmd', cm.exception.message_dict)

    def test_error_stdin_instructor_file_none_stdin_source_instructor_file(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGCommand.objects.validate_and_create(
                cmd=self.cmd,
                stdin_source=ag_models.StdinSource.project_file)

        self.assertIn('stdin_instructor_file', cm.exception.message_dict)

    def test_error_time_limt_out_of_range(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGCommand.objects.validate_and_create(
                cmd=self.cmd,
                time_limit=constants.MAX_SUBPROCESS_TIMEOUT + 1)

        self.assertIn('time_limit', cm.exception.message_dict)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGCommand.objects.validate_and_create(time_limit=-1)

        self.assertIn('time_limit', cm.exception.message_dict)

    def test_error_stack_size_limit_out_of_range(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGCommand.objects.validate_and_create(
                cmd=self.cmd,
                stack_size_limit=constants.MAX_STACK_SIZE_LIMIT + 1)

        self.assertIn('stack_size_limit', cm.exception.message_dict)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGCommand.objects.validate_and_create(cmd=self.cmd, stack_size_limit=0)

        self.assertIn('stack_size_limit', cm.exception.message_dict)

    def test_error_virtual_memory_limit_out_of_range(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGCommand.objects.validate_and_create(
                cmd=self.cmd,
                virtual_memory_limit=constants.MAX_VIRTUAL_MEM_LIMIT + 1)

        self.assertIn('virtual_memory_limit', cm.exception.message_dict)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGCommand.objects.validate_and_create(cmd=self.cmd, virtual_memory_limit=0)

        self.assertIn('virtual_memory_limit', cm.exception.message_dict)

    def test_error_process_spawn_limit_out_of_range(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGCommand.objects.validate_and_create(
                cmd=self.cmd,
                process_spawn_limit=constants.MAX_PROCESS_LIMIT + 1)

        self.assertIn('process_spawn_limit', cm.exception.message_dict)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGCommand.objects.validate_and_create(cmd=self.cmd, process_spawn_limit=-1)

        self.assertIn('process_spawn_limit', cm.exception.message_dict)

    def test_serialize(self):
        expected_fields = [
            'name',
            'cmd',
            'time_limit',
            'stack_size_limit',
            'virtual_memory_limit',
            'process_spawn_limit',
        ]

        cmd = ag_models.AGCommand.objects.validate_and_create(
            cmd=self.cmd)  # type: ag_models.AGCommand
        self.assertCountEqual(expected_fields, cmd.to_dict().keys())

        self.assertIsNone(cmd.to_dict()['stdin_instructor_file'])

        instructor_file = obj_build.make_instructor_file(obj_build.make_project())
        cmd.stdin_instructor_file = instructor_file

        self.assertEqual(instructor_file.to_dict(), cmd.to_dict()['stdin_instructor_file'])

        update_dict = cmd.to_dict()
        cmd.validate_and_update(**update_dict)
