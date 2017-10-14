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
        self.assertEqual(ag_models.StdinSource.none, cmd.stdin_source)
        self.assertEqual('', cmd.stdin_text)
        self.assertIsNone(cmd.stdin_project_file)
        self.assertEqual(constants.DEFAULT_SUBPROCESS_TIMEOUT, cmd.time_limit)
        self.assertEqual(constants.DEFAULT_STACK_SIZE_LIMIT, cmd.stack_size_limit)
        self.assertEqual(constants.DEFAULT_VIRTUAL_MEM_LIMIT, cmd.virtual_memory_limit)
        self.assertEqual(constants.DEFAULT_PROCESS_LIMIT, cmd.process_spawn_limit)

    def test_stdin_sources(self):
        cmd = ag_models.AGCommand.objects.validate_and_create(
            cmd=self.cmd
        )  # type: ag_models.AGCommand
        project_file = obj_build.make_uploaded_file(obj_build.make_project())

        cmd.validate_and_update(stdin_source=ag_models.StdinSource.project_file,
                                stdin_project_file=project_file)

        cmd.refresh_from_db()

        self.assertEqual(project_file, cmd.stdin_project_file)
        self.assertEqual(ag_models.StdinSource.project_file, cmd.stdin_source)

        stdin_text = 'weeeeee'
        cmd.validate_and_update(stdin_source=ag_models.StdinSource.text, stdin_text=stdin_text)

        self.assertEqual(stdin_text, cmd.stdin_text)
        self.assertEqual(ag_models.StdinSource.text, cmd.stdin_source)

    def test_error_cmd_empty(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGCommand.objects.validate_and_create()

        self.assertIn('cmd', cm.exception.message_dict)

        cmd = ag_models.AGCommand.objects.validate_and_create(cmd=self.cmd)
        with self.assertRaises(exceptions.ValidationError) as cm:
            cmd.validate_and_update(cmd='')

        self.assertIn('cmd', cm.exception.message_dict)

    def test_error_stdin_project_file_none_stdin_source_project_file(self):
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.AGCommand.objects.validate_and_create(
                cmd=self.cmd,
                stdin_source=ag_models.StdinSource.project_file)

        self.assertIn('stdin_project_file', cm.exception.message_dict)

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
            'stdin_source',
            'stdin_text',
            'stdin_project_file',
            'time_limit',
            'stack_size_limit',
            'virtual_memory_limit',
            'process_spawn_limit',
        ]

        cmd = ag_models.AGCommand.objects.validate_and_create(
            cmd=self.cmd)  # type: ag_models.AGCommand
        self.assertCountEqual(expected_fields, cmd.to_dict().keys())

        self.assertIsNone(cmd.to_dict()['stdin_project_file'])

        proj_file = obj_build.make_uploaded_file(obj_build.make_project())
        cmd.stdin_project_file = proj_file

        self.assertEqual(proj_file.to_dict(), cmd.to_dict()['stdin_project_file'])

        update_dict = cmd.to_dict()
        cmd.validate_and_update(**update_dict)

    def test_deserialize_stdin_project_file_from_pk(self):
        proj = obj_build.make_project()
        proj_file = obj_build.make_uploaded_file(proj)
        cmd = ag_models.AGCommand.objects.validate_and_create(
            cmd=self.cmd,
            stdin_source=ag_models.StdinSource.project_file,
            stdin_project_file=proj_file.pk,
        )  # type: ag_models.AGCommand
        self.assertEqual(proj_file, cmd.stdin_project_file)

        other_proj_file = obj_build.make_uploaded_file(proj)
        cmd.validate_and_update(stdin_project_file=other_proj_file.pk)
        self.assertEqual(other_proj_file, cmd.stdin_project_file)

    def test_deserialize_stdin_project_file_from_dict(self):
        proj = obj_build.make_project()
        proj_file = obj_build.make_uploaded_file(proj)
        cmd = ag_models.AGCommand.objects.validate_and_create(
            cmd=self.cmd,
            stdin_source=ag_models.StdinSource.project_file,
            stdin_project_file=proj_file.to_dict(),
        )  # type: ag_models.AGCommand
        self.assertEqual(proj_file, cmd.stdin_project_file)

        other_proj_file = obj_build.make_uploaded_file(proj)
        cmd.validate_and_update(stdin_project_file=other_proj_file.to_dict())
        self.assertEqual(other_proj_file, cmd.stdin_project_file)
