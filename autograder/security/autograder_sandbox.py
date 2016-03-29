import os
import subprocess
import uuid
import tempfile
import tarfile

import redis


SANDBOX_HOME_DIR_NAME = '/home/autograder'
SANDBOX_WORKING_DIR_NAME = os.path.join(SANDBOX_HOME_DIR_NAME, 'working_dir')
SANDBOX_USERNAME = 'autograder'


class AutograderSandbox:
    """
    This class wraps Docker functionality to provide an interface for
    running untrusted programs in a secure, isolated environment.

    Docker documentation and installation instructions can be
    found at: https://www.docker.com/

    Instances of this class are intended to be used with a context manager.
    """
    def __init__(self, name=None, allow_network_access=False,
                 environment_variables=None):
        """
        Params:
            name -- A human-readable name that can be used to identify
                this sandbox instance. This value must be unique across
                all sandbox instances, otherwise starting the sandbox
                will fail. If no value is specified, a random name will
                be generated automatically.

            allow_network_access -- When True, programs running inside
                the sandbox will have unrestricted access to external
                IP addresses. When False, programs will not be able
                to contact any external IPs.

            environment_variables -- A dictionary of variable_name: value
                pairs that should be set as environment variables inside
                the sandbox.
        """
        if name is None:
            self._name = 'sandbox-{}'.format(uuid.uuid4().hex)
        else:
            self._name = name

        self._linux_uid = _get_next_linux_uid()

        self._allow_network_access = allow_network_access

        self._environment_variables = environment_variables

        self._is_running = False

    def __enter__(self):
        self._create_and_start()
        return self

    def __exit__(self, *args):
        self._destroy()

    def reset(self):
        """
        Destroys, re-creates, and restarts the sandbox.
        """
        self._destroy()
        self._create_and_start()

    def _create_and_start(self):
        create_args = [
            'docker', 'run',
            '--name=' + self.name,
            '-i',  # Run in interactive mode (needed for input redirection)
            '-t',  # Allocate psuedo tty
            '-d',  # Detached
        ]

        if not self.allow_network_access:
            # Create the container without a network stack.
            create_args += ['--net', 'none']

        if self.environment_variables:
            for key, value in self.environment_variables.items():
                create_args += [
                    '-e', "{}={}".format(key, value)
                ]

        create_args += [
            'autograder',  # Image to use
        ]

        subprocess.check_call(create_args, timeout=10)
        try:
            self.run_command(
                ['usermod', '-u', str(self._linux_uid), SANDBOX_USERNAME],
                as_root=True, raise_on_failure=True)
        except subprocess.CalledProcessError:
            self._destroy()
            raise

        self._is_running = True

    def _destroy(self):
        subprocess.check_call(['docker', 'stop', self.name])
        self._is_running = False
        subprocess.check_call(['docker', 'rm', self.name])

    @property
    def name(self):
        return self._name

    @property
    def allow_network_access(self):
        return self._allow_network_access

    @allow_network_access.setter
    def allow_network_access(self, value):
        """
        Raises ValueError if this sandbox instance is currently running.
        """
        if self._is_running:
            raise ValueError(
                "Cannot change network access settings on a running sandbox")

        self._allow_network_access = value

    @property
    def environment_variables(self):
        return self._environment_variables

    def run_command(self, args, input_content=None,
                    timeout=None,
                    max_num_processes=None,
                    max_stack_size=None,
                    max_virtual_memory=None,
                    as_root=False, raise_on_failure=False):
        """
        Runs a command inside the sandbox.

        Params:
            args -- A list of strings that specify which command should
                be run inside the sandbox.

            input_content -- A string whose contents should be passed to
                the command's standard input stream.

            timeout -- A time limit in seconds.

            max_num_processes -- The maximum number of processes the
                command is allowed to spawn.

            max_stack_size -- The maximum stack size, in bytes, allowed for
                the command.

            max_virtual_memory -- The maximum amount of memory, in bytes,
                allowed for the command.

            as_root -- Whether to run the command as a root user.

            raise_on_failure -- If True, subprocess.CalledProcessError will
                be raised if the command exits with nonzero status.
        """
        cmd = ['docker', 'exec', '-i']
        cmd.append(self.name)

        cmd.append('timeout_script.py')

        if timeout is not None:
            cmd += ['--timeout', str(timeout)]

        if max_num_processes is not None:
            cmd += ['--max_num_processes', str(max_num_processes)]

        if max_stack_size is not None:
            cmd += ['--max_stack_size', str(max_stack_size)]

        if max_virtual_memory is not None:
            cmd += ['--max_virtual_memory', str(max_virtual_memory)]

        if not as_root:
            cmd += ['--linux_user_id', str(self._linux_uid)]

        cmd += args

        print('running: {}'.format(cmd), flush=True)

        if input_content is None:
            input_content = ''
        return _SubprocessRunner(cmd, raise_on_failure=raise_on_failure,
                                 stdin_content=input_content)

    def add_files(self, *filenames):
        """
        Copies the specified files into the working directory of this
        sandbox.
        The filenames specified can be absolute paths or relative paths
        to the current working directory.
        """
        with tempfile.TemporaryFile() as f, \
                tarfile.TarFile(fileobj=f, mode='w') as tar_file:
            for filename in filenames:
                tar_file.add(filename, arcname=os.path.basename(filename))

            f.seek(0)
            subprocess.check_call(
                ['docker', 'cp', '-',
                 self.name + ':' + SANDBOX_WORKING_DIR_NAME],
                stdin=f)
            self._chown_files(
                [os.path.basename(filename) for filename in filenames])

    def add_and_rename_file(self, filename, new_filename):
        """
        Copies the specified file into the working directory of this
        sandbox and renames it to new_filename.
        """
        dest = os.path.join(
            self.name + ':' + SANDBOX_WORKING_DIR_NAME,
            new_filename)
        subprocess.check_call(['docker', 'cp', filename, dest])
        self._chown_files([new_filename])

    def _chown_files(self, filenames):
        chown_cmd = [
            'chown', '{}:{}'.format(SANDBOX_USERNAME, SANDBOX_USERNAME)]
        chown_cmd += filenames
        self.run_command(chown_cmd, as_root=True)


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

                # print("Created temp files", flush=True)
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
                    print("Finished running: ", self._args, flush=True)
                    if (self._return_code ==
                            _SubprocessRunner._TIMEOUT_RETURN_CODE):
                        self._timed_out = True
                finally:
                    stdout_dest.seek(0)
                    stderr_dest.seek(0)
                    self._stdout = stdout_dest.read().decode('utf-8')
                    self._stderr = stderr_dest.read().decode('utf-8')

                    print("Return code: ", self._return_code, flush=True)
                    print(self._stdout, flush=True)
                    print(self._stderr, flush=True)
        except UnicodeDecodeError:
            msg = ("Error reading program output: "
                   "non-unicode characters detected")
            self._stdout = msg
            self._stderr = msg


_NEXT_UID_KEY = 'sandbox_next_uid'


def _get_next_linux_uid():
    redis_conn = redis.StrictRedis()
    return redis_conn.incr(_NEXT_UID_KEY)
