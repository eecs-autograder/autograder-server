import os
import subprocess
import uuid
import tempfile

import autograder.core.shared.global_constants as gc


SANDBOX_HOME_DIR_NAME = '/home/autograder'
SANDBOX_WORKING_DIR_NAME = os.path.join(SANDBOX_HOME_DIR_NAME, 'working_dir')


class AutograderSandbox(object):
    def __init__(self, name, enable_networking=False,
                 environment_variables_to_set=None,
                 database_backend_to_use=None,
                 database_name=''):
        self._name = name
        # self._linux_user_id = linux_user_id
        # self._linux_username = 'worker{}'.format(self._linux_user_id)
        self._linux_username = 'autograder'
        self._networking_enabled = enable_networking

        self._environment_variables = environment_variables_to_set

        self._database_backend_to_use = database_backend_to_use
        self._database_name = database_name

        self._create_args = [
            'docker', 'create', '--name=' + self.name,
            '-a', 'STDOUT', '-a', 'STDERR', '-a', 'STDIN',  # Attach streams
            '-i',  # Run in interactive mode (needed for input redirection)
            '-t',  # Allocate psuedo tty
            '--ulimit', 'nproc=4000',  # Limit number of user processes
            # Allow or disallow networking
            '--net', ('default' if enable_networking else 'none'),
        ]
        if self.environment_variables:
            for key, value in self.environment_variables.items():
                self._create_args += [
                    '-e', "{}={}".format(key, value)
                ]

        self._create_args += [
            'autograder',  # Image to use
            'bash',  # Command to be run in the container
        ]

        subprocess.check_call(self.create_args, timeout=10)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    def start(self):
        print('starting container: ' + self.name)
        try:
            subprocess.check_call(['docker', 'start', self.name], timeout=10)
        except subprocess.CalledProcessError:
            self.stop()
            raise

        self.initialize_database()

    def stop(self):
        print('stopping container: ' + self.name)
        subprocess.check_call(['docker', 'stop', self.name])

    @property
    def name(self):
        return self._name

    @property
    def networking_enabled(self):
        return self._networking_enabled

    @property
    def environment_variables(self):
        return self._environment_variables

    @property
    def database_backend_to_use(self):
        return self._database_backend_to_use

    @property
    def database_name(self):
        return self._database_name

    @property
    def create_args(self):
        return self._create_args

    def copy_into_sandbox(self, *filenames):
        """
        Copies the specified files into the working directory of this
        sandbox.
        The filenames specified can be absolute paths or relative paths
        to the current working directory.
        """
        for filename in filenames:
            subprocess.check_call(
                ['docker', 'cp', filename,
                 self.name + ':' + SANDBOX_WORKING_DIR_NAME],
                timeout=gc.DEFAULT_SUBPROCESS_TIMEOUT
            )

        basenames = [os.path.basename(filename) for filename in filenames]

        self.run_cmd_success_required(
            ['chown', self._linux_username + ':' + self._linux_username] +
            basenames, as_root=True)

    def copy_and_rename_into_sandbox(self, filename, new_name):
        """
        Copies the specified file into the working directory of this sandbox
        and renames the copy to new_name.
        new_name must consist of only a filename. Any other path information
        will be stripped.
        The filename specified can be an absolute path or a relative path
        to the current working directory.
        """
        copy_destination = self.name + ':' + os.path.join(
            SANDBOX_WORKING_DIR_NAME, os.path.basename(new_name))

        print(copy_destination)

        subprocess.check_call(
            ['docker', 'cp', filename, copy_destination],
            timeout=gc.DEFAULT_SUBPROCESS_TIMEOUT)

        self.run_cmd_success_required(
            ['chown', self._linux_username + ':' + self._linux_username,
             new_name], as_root=True)

    def run_cmd_with_redirected_io(self, cmd_exec_args,
                                   as_root=False,
                                   timeout=gc.DEFAULT_SUBPROCESS_TIMEOUT,
                                   stdin_content=''):
        args = ['docker', 'exec', '-i']
        if not as_root:
            args.append('--user={}'.format(self._linux_username))
        args.append(self.name)
        args += ['timeout_script.py', str(timeout)] + cmd_exec_args

        print('running: {}'.format(args))

        runner = _SubprocessRunner(
            args, timeout=timeout * 2, stdin_content=stdin_content)
        return runner

    def run_cmd_success_required(self, cmd_exec_args, as_root=False,
                                 timeout=gc.DEFAULT_SUBPROCESS_TIMEOUT,
                                 return_output=True):
        args = ['docker', 'exec']
        if not as_root:
            args.append('--user={}'.format(self._linux_username))
        args.append(self.name)
        args += cmd_exec_args

        if return_output:
            return subprocess.check_output(
                args, timeout=timeout, universal_newlines=True)

        subprocess.check_call(args, timeout=timeout)

    def clear_working_dir(self):
        working_dir_contents = self.run_cmd_success_required(
            ['ls', SANDBOX_WORKING_DIR_NAME]
        ).split()
        working_dir_contents = [
            os.path.join(SANDBOX_WORKING_DIR_NAME, filename)
            for filename in working_dir_contents]

        backup_dirname = os.path.join(
            SANDBOX_HOME_DIR_NAME, "old-" + uuid.uuid4().hex)
        self.run_cmd_success_required(["mkdir", "-p", backup_dirname])

        self.run_cmd_success_required(
            ["mv"] + working_dir_contents + [backup_dirname])

    def initialize_database(self):
        if not self.database_backend_to_use:
            return

        self.run_cmd_success_required(
            ['initialize_db', self.database_backend_to_use,
             self.database_name], as_root=True)

    def reinitialize_database(self):
        if not self.database_backend_to_use:
            return

        self.run_cmd_success_required(
            ['reinitialize_db', self.database_backend_to_use,
             self.database_name], as_root=True)


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
        self._timeout = kwargs.get('timeout', gc.DEFAULT_SUBPROCESS_TIMEOUT)
        self._stdin_content = kwargs.get('stdin_content', '')
        self._merge_stdout_and_stderr = kwargs.get(
            'merge_stdout_and_stderr', False)

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

                print("Created temp files")
                stdin_content.write(self._stdin_content.encode('utf-8'))
                stdin_content.seek(0)

                try:
                    self._return_code = subprocess.call(
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
