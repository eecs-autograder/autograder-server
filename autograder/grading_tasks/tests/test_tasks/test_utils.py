from unittest import mock

from autograder_sandbox import AutograderSandbox
from django.db.utils import IntegrityError
from django.test import tag

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.grading_tasks import tasks
from autograder.utils.retry import (
    retry, retry_ag_test_cmd, retry_should_recover, MaxRetriesExceeded)
from autograder.utils.testing import UnitTestBase


class RetryDecoratorTestCase(UnitTestBase):
    def test_retry_and_succeed(self):
        arg_val = 42
        kwarg_val = "cheese"
        return_val = "winzorz!"

        should_throw = True

        @retry(max_num_retries=1, retry_delay_start=0, retry_delay_end=0)
        def func_to_retry(test_case, arg, kwarg=None):
            test_case.assertEqual(arg_val, arg)
            test_case.assertEqual(kwarg_val, kwarg)

            nonlocal should_throw
            if should_throw:
                should_throw = False
                raise Exception('Throooooow')

            return return_val

        self.assertEqual(return_val, func_to_retry(self, arg_val, kwarg_val))

    def test_max_retries_exceeded(self):
        @retry(max_num_retries=10, retry_delay_start=0, retry_delay_end=0)
        def func_to_retry():
            raise Exception('Errrrror')

        with self.assertRaises(MaxRetriesExceeded):
            func_to_retry()

    @mock.patch('autograder.utils.retry.sleep')
    def test_retry_delay(self, mocked_sleep):
        max_num_retries = 3
        min_delay = 2
        max_delay = 6
        delay_step = 2

        @retry(max_num_retries=max_num_retries,
               retry_delay_start=min_delay, retry_delay_end=max_delay,
               retry_delay_step=delay_step)
        def func_to_retry():
            raise Exception

        with self.assertRaises(MaxRetriesExceeded):
            func_to_retry()

        mocked_sleep.assert_has_calls(
            [mock.call(delay) for delay in range(min_delay, max_delay, delay_step)])

    @mock.patch('autograder.utils.retry.sleep')
    def test_retry_zero_delay(self, mocked_sleep):
        max_num_retries = 1

        @retry(max_num_retries=max_num_retries, retry_delay_start=0, retry_delay_end=0)
        def func_to_retry():
            raise Exception

        with self.assertRaises(MaxRetriesExceeded):
            func_to_retry()

        mocked_sleep.assert_has_calls([mock.call(0) for i in range(max_num_retries)])

    @mock.patch('autograder.utils.retry.sleep')
    def test_immediatedly_reraise_on(self, sleep_mock) -> None:
        @retry(max_num_retries=1, immediately_reraise_on=(ValueError, TypeError))
        def func_to_retry(type_to_throw):
            raise type_to_throw

        with self.assertRaises(ValueError):
            func_to_retry(ValueError)

        with self.assertRaises(TypeError):
            func_to_retry(TypeError)

        sleep_mock.assert_not_called()

        with self.assertRaises(MaxRetriesExceeded):
            func_to_retry(RuntimeError)

    @mock.patch('autograder.utils.retry.sleep')
    def test_immediately_reraise_retry_should_recover(self, sleep_mock) -> None:
        @retry_should_recover
        def func():
            raise IntegrityError

        with self.assertRaises(IntegrityError):
            func()

        sleep_mock.assert_not_called()

    @mock.patch('autograder.utils.retry.sleep')
    def test_immediately_reraise_retry_ad_test_cmd(self, sleep_mock) -> None:
        @retry_ag_test_cmd
        def func():
            raise IntegrityError

        with self.assertRaises(IntegrityError):
            func()

        sleep_mock.assert_not_called()


@tag('slow', 'sandbox')
class RunCommandTestCase(UnitTestBase):
    def test_shell_parse_error(self):
        with AutograderSandbox() as sandbox:
            command = ag_models.Command(cmd='echo hello"')
            result = tasks.run_command_from_args(
                command.cmd, sandbox,
                block_process_spawn=False,
                max_virtual_memory=command.virtual_memory_limit,
                timeout=command.time_limit,
            )
            self.assertNotEqual(0, result.return_code)
            print(result.stdout.read())
            print(result.stderr.read())

    def test_command_not_found(self):
        with AutograderSandbox() as sandbox:
            command = ag_models.Command(cmd='not_a_command')
            result = tasks.run_command_from_args(
                command.cmd, sandbox,
                block_process_spawn=False,
                max_virtual_memory=command.virtual_memory_limit,
                timeout=command.time_limit,
            )
            self.assertNotEqual(0, result.return_code)
            print(result.stdout.read())
            print(result.stderr.read())

    def test_file_not_found(self):
        with AutograderSandbox() as sandbox:
            command = ag_models.Command(cmd='./not_a_file')
            result = tasks.run_command_from_args(
                command.cmd, sandbox,
                block_process_spawn=False,
                max_virtual_memory=command.virtual_memory_limit,
                timeout=command.time_limit,
            )
            self.assertNotEqual(0, result.return_code)
            print(result.stdout.read())
            print(result.stderr.read())

    def test_permission_denied(self):
        with AutograderSandbox() as sandbox:
            sandbox.run_command(['touch', 'not_executable'], check=True)
            sandbox.run_command(['chmod', '666', 'not_executable'], check=True)
            command = ag_models.Command(cmd='./not_executable')
            result = tasks.run_command_from_args(
                command.cmd, sandbox,
                block_process_spawn=False,
                max_virtual_memory=command.virtual_memory_limit,
                timeout=command.time_limit,
            )
            self.assertNotEqual(0, result.return_code)
            print(result.stdout.read())
            print(result.stderr.read())

    def test_block_process_spawn(self):
        # Make sure that wrapping commands in bash -c doesn't spawn a process.
        with AutograderSandbox() as sandbox:
            command = ag_models.Command(cmd='echo hello', block_process_spawn=True)
            result = tasks.run_ag_command(command, sandbox)
            self.assertEqual(0, result.return_code)
            print(result.stdout.read())
            print(result.stderr.read())

            extra_bash_dash_c = ag_models.Command(
                cmd='bash -c "echo hello"', block_process_spawn=True)
            result = tasks.run_ag_command(extra_bash_dash_c, sandbox)
            self.assertEqual(0, result.return_code)
            print(result.stdout.read())
            print(result.stderr.read())

            spawns_extra = ag_models.Command(
                cmd='echo "echo hello" | bash', block_process_spawn=True, time_limit=1)
            result = tasks.run_ag_command(spawns_extra, sandbox)
            self.assertTrue(result.timed_out)
            print(result.stdout.read())
            stderr = result.stderr.read()
            print(stderr)
            self.assertIn('No child processes', stderr.decode())

    def test_shell_output_redirection(self):
        with AutograderSandbox() as sandbox:
            command = ag_models.Command(cmd='printf "spam" > file', process_spawn_limit=0)
            tasks.run_command_from_args(
                command.cmd, sandbox,
                block_process_spawn=False,
                max_virtual_memory=command.virtual_memory_limit,
                timeout=command.time_limit,
            )
            result = sandbox.run_command(['cat', 'file'], check=True)
            self.assertEqual(0, result.return_code)
            self.assertEqual('spam', result.stdout.read().decode())

    def test_no_stdin_specified_redirects_devnull(self):
        # If no stdin is redirected, this command will time out.
        # If /dev/null is redirected it should terminate normally.
        # This behavior is handled by the autograder_sandbox library.
        cmd = 'python3 -c "import sys; sys.stdin.read(); print(\'done\')"'

        # Run command from args
        with AutograderSandbox() as sandbox:
            result = tasks.run_command_from_args(
                cmd,
                sandbox,
                block_process_spawn=False,
                max_virtual_memory=500000000,
                timeout=2
            )
            self.assertFalse(result.timed_out)
            self.assertEqual(0, result.return_code)
            self.assertEqual('done\n', result.stdout.read().decode())

        # Run ag command
        with AutograderSandbox() as sandbox:
            ag_command = ag_models.Command(
                cmd=cmd,
                time_limit=2
            )
            result = tasks.run_ag_command(ag_command, sandbox)
            self.assertFalse(result.timed_out)
            self.assertEqual(0, result.return_code)
            self.assertEqual('done\n', result.stdout.read().decode())

        project = obj_build.make_project()
        ag_test_suite = ag_models.AGTestSuite.objects.validate_and_create(
            name='Suite', project=project)
        ag_test_case = ag_models.AGTestCase.objects.validate_and_create(
            name='Case', ag_test_suite=ag_test_suite)
        # Run ag test command
        with AutograderSandbox() as sandbox:
            ag_test_command = ag_models.AGTestCommand.objects.validate_and_create(
                ag_test_case=ag_test_case,
                name='Read stdin',
                cmd=cmd,
                stdin_source=ag_models.StdinSource.none,
                time_limit=2,
            )
            result = tasks.run_ag_test_command(ag_test_command, sandbox, ag_test_suite)
            self.assertFalse(result.timed_out)
            self.assertEqual(0, result.return_code)
            self.assertEqual('done\n', result.stdout.read().decode())
