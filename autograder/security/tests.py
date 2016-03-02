import unittest
import subprocess
import uuid

from autograder.security import autograder_sandbox
from .autograder_sandbox import AutograderSandbox


# class AutograderSandboxTestCase(unittest.TestCase):

class AutograderSandboxInitTestCase(unittest.TestCase):
    def setUp(self):
        self.name = 'awexome_container'
        self.ip_whitelist = ['35.2.65.126']
        self.max_num_processes = 2
        self.max_stack_size = 60000000
        self.max_virtual_memory = 1000000000000
        self.environment_variables = {'spam': 'egg', 'sausage': 42}

    def test_default_init(self):
        sandbox = AutograderSandbox()
        self.assertIsNotNone(sandbox.name)
        self.assertCountEqual([], sandbox.ip_address_whitelist)
        self.assertEqual(autograder_sandbox.DEFAULT_PROCESS_LIMIT,
                         sandbox.max_num_processes)
        self.assertEqual(autograder_sandbox.DEFAULT_STACK_LIMIT,
                         sandbox.max_stack_size)
        self.assertEqual(autograder_sandbox.DEFAULT_VIRTUAL_MEM_LIMIT,
                         sandbox.max_virtual_memory)

        self.assertIsNone(sandbox.environment_variables)

    def test_non_default_init(self):
        sandbox = AutograderSandbox(
            name=self.name,
            ip_address_whitelist=self.ip_whitelist,
            max_num_processes=self.max_num_processes,
            max_stack_size=self.max_stack_size,
            max_virtual_memory=self.max_virtual_memory,
            environment_variables=self.environment_variables
        )

        self.assertEqual(self.name,
                         sandbox.name)
        self.assertEqual(self.ip_whitelist,
                         sandbox.ip_address_whitelist)
        self.assertEqual(self.max_num_processes, sandbox.max_num_processes)
        self.assertEqual(self.max_stack_size, sandbox.max_stack_size)
        self.assertEqual(self.max_virtual_memory, sandbox.max_virtual_memory)
        self.assertEqual(self.environment_variables,
                         sandbox.environment_variables)


class AutograderSandboxBasicRunCommandTestCase(unittest.TestCase):
    def setUp(self):
        self.sandbox = AutograderSandbox()

        self.root_cmd = ["touch", "/"]

    def test_run_legal_command_non_root(self):
        stdout_content = "hello world"
        with self.sandbox:
            cmd_result = self.sandbox.run_command(["echo", stdout_content])
            self.assertEqual(0, cmd_result.return_code)
            self.assertEqual(stdout_content + '\n', cmd_result.stdout)

    def test_run_illegal_command_non_root(self):
        with self.sandbox:
            cmd_result = self.sandbox.run_command(self.root_cmd)
            self.assertNotEqual(0, cmd_result.return_code)
            self.assertNotEqual("", cmd_result.stderr)

    def test_run_command_as_root(self):
        with self.sandbox:
            cmd_result = self.sandbox.run_command(self.root_cmd, as_root=True)
            self.assertEqual(0, cmd_result.return_code)
            self.assertEqual("", cmd_result.stderr)

    def test_run_command_timeout_exceeded(self):
        with self.sandbox:
            cmd_result = self.sandbox.run_command(["sleep", "10"], timeout=1)
            self.assertTrue(cmd_result.timed_out)

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
        name = 'container-{}'.format(uuid.uuid4().hex)
        with AutograderSandbox(name=name):
            # If the container was created successfully, we
            # should get an error if we try to create another
            # container with the same name.
            with self.assertRaises(subprocess.CalledProcessError):
                with AutograderSandbox(name=name):
                    pass

        # The container should have been deleted at this point,
        # so we should be able to create another with the same name.
        with AutograderSandbox(name=name):
            pass

    def test_sandbox_environment_variables_set(self):
        self.fail()
