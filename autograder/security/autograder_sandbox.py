import os
import subprocess
import uuid
import tempfile


SANDBOX_HOME_DIR_NAME = '/home/autograder'
SANDBOX_WORKING_DIR_NAME = os.path.join(SANDBOX_HOME_DIR_NAME, 'working_dir')
LINUX_USERNAME = 'autograder'

DEFAULT_PROCESS_LIMIT = 0
DEFAULT_STACK_LIMIT = 8000000  # 8 MB
DEFAULT_VIRTUAL_MEM_LIMIT = 500000000  # 500 MB
DEFAULT_TIMEOUT = 10  # seconds


class AutograderSandbox:
    """
    This class wraps Docker functionality to provide an interface for
    running untrusted programs in a secure, isolated environment.

    Docker documentation and installation instructions can be
    found at: https://www.docker.com/

    Instances of this class are intended to be used with a context manager.
    """
    def __init__(self, name=None, ip_address_whitelist=[],
                 max_num_processes=DEFAULT_PROCESS_LIMIT,
                 max_stack_size=DEFAULT_STACK_LIMIT,
                 max_virtual_memory=DEFAULT_VIRTUAL_MEM_LIMIT,
                 environment_variables=None):
        """
        Params:
            name -- A human-readable name that can be used to identify
                this sandbox instance. This value must be unique across
                all sandbox instances, otherwise starting the sandbox
                will fail. If no value is specified, a random name will
                be generated automatically.

            ip_address_whitelist -- A list of IP addresses that programs
                running inside this container should be allowed to access.
                Access to all other IP addresses will be blocked.

            max_num_processes -- The maximum number of processes a program
                run inside the sandbox is allowed to spawn.

            max_stack_size -- The maximum stack size, in bytes, allowed for
                programs run inside the sandbox.

            max_virtual_memory -- The maximum amount of memory, in bytes,
                allowed for programs run inside the sandbox.

            environment_variables -- A dictionary of variable_name: value
                pairs that should be set as environment variables inside
                the sandbox.
        """
        if name is None:
            self._name = 'sandbox-{}'.format(uuid.uuid4().hex)
        else:
            self._name = name

        self._ip_address_whitelist = ip_address_whitelist

        self._max_num_processes = max_num_processes
        self._max_stack_size = max_stack_size
        self._max_virtual_memory = max_virtual_memory

        self._environment_variables = environment_variables

    def __enter__(self):
        create_args = [
            'docker', 'run',
            '--name=' + self.name,
            # '-a', 'STDOUT', '-a', 'STDERR', '-a', 'STDIN',  # Attach streams
            '-i',  # Run in interactive mode (needed for input redirection)
            '-t',  # Allocate psuedo tty
            '-d',  # Detached
            # Create the container with no network stack
            '--net', 'none',
        ]

        if self.environment_variables:
            for key, value in self.environment_variables.items():
                create_args += [
                    '-e', "{}={}".format(key, value)
                ]

        create_args += [
            'autograder',  # Image to use
            # 'bash',  # Command to be run in the container
        ]

        subprocess.check_call(create_args, timeout=10)

    def __exit__(self, *args):
        pass

    @property
    def name(self):
        return self._name

    @property
    def ip_address_whitelist(self):
        return self._ip_address_whitelist

    @property
    def max_num_processes(self):
        return self._max_num_processes

    @property
    def max_stack_size(self):
        return self._max_stack_size

    @property
    def max_virtual_memory(self):
        return self._max_virtual_memory

    @property
    def environment_variables(self):
        return self._environment_variables

    def run_command(self, args, input_content=None, timeout=DEFAULT_TIMEOUT,
                    as_root=False, raise_on_failure=False):
        cmd = ['docker', 'exec', '-i']
        if not as_root:
            cmd.append('--user={}'.format(LINUX_USERNAME))
        cmd.append(self.name)
        cmd += [
            'timeout_script.py', str(timeout), str(self.max_num_processes),
            str(self.max_stack_size), str(self.max_virtual_memory)
        ]
        cmd += args

        print('running: {}'.format(cmd))

        if input_content is None:
            input_content = ''
        return _SubprocessRunner(cmd, raise_on_failure=raise_on_failure,
                                 stdin_content=input_content)


# class AutograderSandbox:
#     def __init__(self, name, enable_networking=False,
#                  environment_variables_to_set=None,
#                  database_backend_to_use=None,
#                  database_name=''):
#         self._name = name
#         # self._linux_user_id = linux_user_id
#         # self._linux_username = 'worker{}'.format(self._linux_user_id)
#         self._linux_username = 'autograder'
#         self._networking_enabled = enable_networking

#         self._environment_variables = environment_variables_to_set

#         self._database_backend_to_use = database_backend_to_use
#         self._database_name = database_name

#         self._create_args = [
#             'docker', 'create', '--name=' + self.name,
#             '-a', 'STDOUT', '-a', 'STDERR', '-a', 'STDIN',  # Attach streams
#             '-i',  # Run in interactive mode (needed for input redirection)
#             '-t',  # Allocate psuedo tty
#             '--ulimit', 'nproc=4000',  # Limit number of user processes
#             # Allow or disallow networking
#             '--net', ('default' if enable_networking else 'none'),
#         ]
#         if self.environment_variables:
#             for key, value in self.environment_variables.items():
#                 self._create_args += [
#                     '-e', "{}={}".format(key, value)
#                 ]

#         self._create_args += [
#             'autograder',  # Image to use
#             'bash',  # Command to be run in the container
#         ]

#         subprocess.check_call(self.create_args, timeout=10)

#     def __enter__(self):
#         self.start()
#         return self

#     def __exit__(self, *args):
#         self.stop()

#     def start(self):
#         print('starting container: ' + self.name)
#         try:
#             subprocess.check_call(['docker', 'start', self.name], timeout=10)
#         except subprocess.CalledProcessError:
#             self.stop()
#             raise

#         self.initialize_database()

#     def stop(self):
#         print('stopping container: ' + self.name)
#         subprocess.check_call(['docker', 'stop', self.name])

#     @property
#     def name(self):
#         return self._name

#     @property
#     def networking_enabled(self):
#         return self._networking_enabled

#     @property
#     def environment_variables(self):
#         return self._environment_variables

#     @property
#     def database_backend_to_use(self):
#         return self._database_backend_to_use

#     @property
#     def database_name(self):
#         return self._database_name

#     @property
#     def create_args(self):
#         return self._create_args

#     def copy_into_sandbox(self, *filenames):
#         """
#         Copies the specified files into the working directory of this
#         sandbox.
#         The filenames specified can be absolute paths or relative paths
#         to the current working directory.
#         """
#         for filename in filenames:
#             subprocess.check_call(
#                 ['docker', 'cp', filename,
#                  self.name + ':' + SANDBOX_WORKING_DIR_NAME],
#                 timeout=gc.DEFAULT_SUBPROCESS_TIMEOUT
#             )

#         basenames = [os.path.basename(filename) for filename in filenames]

#         self.run_cmd_success_required(
#             ['chown', self._linux_username + ':' + self._linux_username] +
#             basenames, as_root=True)

#     def copy_and_rename_into_sandbox(self, filename, new_name):
#         """
#         Copies the specified file into the working directory of this sandbox
#         and renames the copy to new_name.
#         new_name must consist of only a filename. Any other path information
#         will be stripped.
#         The filename specified can be an absolute path or a relative path
#         to the current working directory.
#         """
#         copy_destination = self.name + ':' + os.path.join(
#             SANDBOX_WORKING_DIR_NAME, os.path.basename(new_name))

#         print(copy_destination)

#         subprocess.check_call(
#             ['docker', 'cp', filename, copy_destination],
#             timeout=gc.DEFAULT_SUBPROCESS_TIMEOUT)

#         self.run_cmd_success_required(
#             ['chown', self._linux_username + ':' + self._linux_username,
#              new_name], as_root=True)

#     def run_cmd_with_redirected_io(self, cmd_exec_args,
#                                    as_root=False,
#                                    timeout=gc.DEFAULT_SUBPROCESS_TIMEOUT,
#                                    stdin_content=''):
#         args = ['docker', 'exec', '-i']
#         if not as_root:
#             args.append('--user={}'.format(self._linux_username))
#         args.append(self.name)
#         args += ['timeout_script.py', str(timeout)] + cmd_exec_args

#         print('running: {}'.format(args))

#         runner = _SubprocessRunner(
#             args, timeout=timeout * 2, stdin_content=stdin_content)
#         return runner

#     def run_cmd_success_required(self, cmd_exec_args, as_root=False,
#                                  timeout=gc.DEFAULT_SUBPROCESS_TIMEOUT,
#                                  return_output=True):
#         args = ['docker', 'exec']
#         if not as_root:
#             args.append('--user={}'.format(self._linux_username))
#         args.append(self.name)
#         args += cmd_exec_args

#         if return_output:
#             return subprocess.check_output(
#                 args, timeout=timeout, universal_newlines=True)

#         subprocess.check_call(args, timeout=timeout)

#     def clear_working_dir(self):
#         working_dir_contents = self.run_cmd_success_required(
#             ['ls', SANDBOX_WORKING_DIR_NAME]
#         ).split()
#         working_dir_contents = [
#             os.path.join(SANDBOX_WORKING_DIR_NAME, filename)
#             for filename in working_dir_contents]

#         backup_dirname = os.path.join(
#             SANDBOX_HOME_DIR_NAME, "old-" + uuid.uuid4().hex)
#         self.run_cmd_success_required(["mkdir", "-p", backup_dirname])

#         self.run_cmd_success_required(
#             ["mv"] + working_dir_contents + [backup_dirname])

#     def initialize_database(self):
#         if not self.database_backend_to_use:
#             return

#         self.run_cmd_success_required(
#             ['initialize_db', self.database_backend_to_use,
#              self.database_name], as_root=True)

#     def reinitialize_database(self):
#         if not self.database_backend_to_use:
#             return

#         self.run_cmd_success_required(
#             ['reinitialize_db', self.database_backend_to_use,
#              self.database_name], as_root=True)


# TODO: Once upgraded to Python 3.5, replace call() with the
# new subprocess.run() method.
class _SubprocessRunner(object):
    """
    Convenience wrapper for calling a subprocess and retrieving the data
    we usually need.
    """
    _TIMEOUT_RETURN_CODE = 124

    def __init__(self, program_args, **kwargs):
        self._args = program_args
        self._timeout = kwargs.get('timeout', None)
        self._stdin_content = kwargs.get('stdin_content', '')
        self._merge_stdout_and_stderr = kwargs.get(
            'merge_stdout_and_stderr', False)
        if kwargs.get('raise_on_failure', False):
            self._subprocess_method = subprocess.check_call
        else:
            self._subprocess_method = subprocess.call

        self._timed_out = False
        self._return_code = None
        self._stdout = None
        self._stderr = None

        self._process = None

        self._run()

    @property
    def timed_out(self):
        return self._timed_out

    @property
    def return_code(self):
        return self._return_code

    @property
    def stdout(self):
        return self._stdout

    @property
    def stderr(self):
        return self._stderr

    @property
    def process(self):
        return self._process

    def _run(self):
        try:
            with tempfile.TemporaryFile() as stdin_content, \
                    tempfile.TemporaryFile() as stdout_dest, \
                    tempfile.TemporaryFile() as stderr_dest:

                # print("Created temp files")
                stdin_content.write(self._stdin_content.encode('utf-8'))
                stdin_content.seek(0)

                try:
                    self._return_code = self._subprocess_method(
                        self._args,
                        stdin=stdin_content,
                        stdout=stdout_dest,
                        stderr=stderr_dest,
                        timeout=self._timeout
                    )
                    print("Finished running: ", self._args)
                    if (self._return_code ==
                            _SubprocessRunner._TIMEOUT_RETURN_CODE):
                        self._timed_out = True
                finally:
                    stdout_dest.seek(0)
                    stderr_dest.seek(0)
                    self._stdout = stdout_dest.read().decode('utf-8')
                    self._stderr = stderr_dest.read().decode('utf-8')

                    print("Return code: ", self._return_code)
                    print(self._stdout)
                    print(self._stderr)
        except UnicodeDecodeError:
            msg = ("Error reading program output: "
                   "non-unicode characters detected")
            self._stdout = msg
            self._stderr = msg
