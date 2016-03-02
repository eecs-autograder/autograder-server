import unittest
import subprocess

from .autograder_sandbox import AutograderSandbox


# class AutograderSandboxTestCase(unittest.TestCase):

class AutograderSandboxInitTestCase(unittest.TestCase):
    def setUp(self):
        self.name = 'awexome_container'
        self.ip_whitelist = ['35.2.65.126']
        self.num_processes_soft = 4
        self.num_processes_hard = 6
        self.stack_size_soft = 20000
        self.stack_size_hard = 40000
        self.virtual_memory_soft = 500000
        self.virtual_memory_hard = 1000000
        self.environment_variables = {'spam': 'egg', 'sausage': 42}

    def test_default_init(self):
        sandbox = AutograderSandbox()
        self.assertIsNone(sandbox.name)
        self.assertCountEqual([], sandbox.ip_address_whitelist)
        self.assertIsNone(sandbox.num_processes_soft_limit)
        self.assertIsNone(sandbox.num_processes_hard_limit)
        self.assertIsNone(sandbox.stack_size_soft_limit)
        self.assertIsNone(sandbox.stack_size_hard_limit)
        self.assertIsNone(sandbox.virtual_memory_soft_limit)
        self.assertIsNone(sandbox.virtual_memory_hard_limit)
        self.assertIsNone(sandbox.environment_variables)

    def test_non_default_init(self):
        sandbox = AutograderSandbox(
            name=self.name,
            ip_address_whitelist=self.ip_whitelist,
            num_processes_soft_limit=self.num_processes_soft,
            num_processes_hard_limit=self.num_processes_hard,
            stack_size_soft_limit=self.stack_size_soft,
            stack_size_hard_limit=self.stack_size_hard,
            virtual_memory_soft_limit=self.virtual_memory_soft,
            virtual_memory_hard_limit=self.virtual_memory_hard,
            environment_variables=self.environment_variables
        )

        self.assertEqual(self.name,
                         sandbox.name)
        self.assertEqual(self.ip_whitelist,
                         sandbox.ip_address_whitelist)
        self.assertEqual(self.num_processes_soft,
                         sandbox.num_processes_soft_limit)
        self.assertEqual(self.num_processes_hard,
                         sandbox.num_processes_hard_limit)
        self.assertEqual(self.stack_size_soft,
                         sandbox.stack_size_soft_limit)
        self.assertEqual(self.stack_size_hard,
                         sandbox.stack_size_hard_limit)
        self.assertEqual(self.virtual_memory_soft,
                         sandbox.virtual_memory_soft_limit)
        self.assertEqual(self.virtual_memory_hard,
                         sandbox.virtual_memory_hard_limit)
        self.assertEqual(self.environment_variables,
                         sandbox.environment_variables)

    def test_init_soft_limits_only(self):
        """
        Makes sure that when only soft limits are specified, the hard limits
        are given the same values.
        """
        sandbox = AutograderSandbox(
            num_processes_soft_limit=self.num_processes_soft,
            stack_size_soft_limit=self.stack_size_soft,
            virtual_memory_soft_limit=self.virtual_memory_soft)

        self.assertEqual(self.num_processes_soft,
                         sandbox.num_processes_soft_limit)
        self.assertEqual(self.num_processes_hard,
                         sandbox.num_processes_hard_limit)
        self.assertEqual(self.stack_size_soft,
                         sandbox.stack_size_soft_limit)
        self.assertEqual(self.stack_size_hard,
                         sandbox.stack_size_hard_limit)
        self.assertEqual(self.virtual_memory_soft,
                         sandbox.virtual_memory_soft_limit)
        self.assertEqual(self.virtual_memory_hard,
                         sandbox.virtual_memory_hard_limit)


class AutograderSandboxBasicRunCommandTestCase(unittest.TestCase):
    def setUp(self):
        self.sandbox = AutograderSandbox()

        self.root_cmd = ["touch", "/"]

    def test_run_legal_command_non_root(self):
        stdout_content = "hello world"
        with self.sandbox:
            cmd_result = self.sandbox.run_command(["echo", stdout_content])
            self.assertEqual(0, cmd_result.return_code)
            self.assertEqual(stdout_content, cmd_result.stdout)

    def test_run_illegal_command_non_root(self):
        with self.sandbox:
            cmd_result = self.sandbox.run_command(self.root_cmd)
            self.assertNotEqual(0, cmd_result.return_code)
            self.assertNotEqual("", cmd_result.stderr)

    def test_run_command_as_root(self):
        with self.sandbox:
            cmd_result = self.sandbox.run_command(self.root_cmd)
            self.assertEqual(0, cmd_result.return_code)
            self.assertEqual("", cmd_result.stderr)

    def test_run_command_timeout_exceeded(self):
        self.fail()

    def test_run_command_raise_on_error(self):
        """
        Tests that an exception is thrown only when raise_on_failure is True
        and the command exits with nonzero status.
        """
        with self.sandbox:
            # No exception should be raised.
            cmd_result = self.sandbox.run_command(self.root_cmd,
                                                  as_root=True,
                                                  raise_on_failure=True)
            self.assertEqual(0, cmd_result.return_code)

            with self.assertRaises(subprocess.CalledProcessError):
                self.sandbox.run_command(self.root_cmd, raise_on_failure=True)


class AutograderSandboxUlimitTestCase(unittest.TestCase):
    def test_non_root_command_exceeds_ulimit(self):
        self.fail()

    def test_multiple_containers_dont_exceed_ulimits(self):
        """
        One quirk of docker containers is that if there are multiple users
        created in different containers but with the same UID, the resource
        usage of all those users will contribute to hitting the same ulimits.
        This test makes sure that users are created with different UIDs
        and don't step on each others' resource limits.
        """
        self.fail()


class AutograderSandboxNetworkAccessTestCase(unittest.TestCase):
    def test_networking_disabled(self):
        self.fail()

    def test_run_command_access_ip_address_whitelist(self):
        self.fail()


class AutograderSandboxCopyFilesTestCase(unittest.TestCase):
    def test_copy_files_into_sandbox(self):
        self.fail()

    def test_copy_and_rename_file_into_sandbox(self):
        self.fail()


class AutograderSandboxMiscTestCase(unittest.TestCase):
    def test_reset(self):
        self.fail()

    def test_context_manager(self):
        self.fail()

    def test_sandbox_environment_variables_set(self):
        self.fail()
