import os
import subprocess
import uuid
import tempfile

import autograder.shared.global_constants as gc


SANDBOX_HOME_DIR_NAME = '/home/autograder'
SANDBOX_WORKING_DIR_NAME = os.path.join(SANDBOX_HOME_DIR_NAME, 'working_dir')


class AutograderSandbox(object):
    def __init__(self, name):  # , linux_user_id):
        self.name = name
        # self._linux_user_id = linux_user_id
        # self._linux_username = 'worker{}'.format(self._linux_user_id)
        self._linux_username = 'autograder'

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    def start(self):
        print('starting container: ' + self.name)
        subprocess.check_call(
            ['docker', 'create', '--name=' + self.name,
             '-a', 'STDOUT', '-a', 'STDERR', '-a', 'STDIN',  # Attach streams
             '-i',  # Run in interactive mode (needed for input redirection)
             '-t',  # Allocate psuedo tty
             'autograder', 'bash'],
            timeout=10
        )
        try:
            subprocess.check_call(['docker', 'start', self.name], timeout=10)
        except subprocess.CalledProcessError:
            self.stop()
            raise

    def stop(self):
        print('stopping container: ' + self.name)
        subprocess.check_call(['docker', 'stop', self.name])

    def copy_into_sandbox(self, *filenames):
        for filename in filenames:
            subprocess.check_call(
                ['docker', 'cp', filename,
                 self.name + ':/home/autograder/working_dir']
            )

        basenames = [os.path.basename(filename) for filename in filenames]

        self.run_cmd_success_required(
            ['chown', self._linux_username + ':' + self._linux_username] +
            basenames, as_root=True)

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
            args, timeout=timeout * 2,
            stdin_content=stdin_content)
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


# TODO: Once upgraded to Python 3.5 and Django 1.9, replace call() with the
# new subprocess.run() method.
class _SubprocessRunner(object):
    """
    Convenience wrapper for calling a subprocess and retrieving the data
    we usually need.
    """
    # HACK: Currently, this class assumes that the command called inside
    # Docker is wrapped in a linux timeout call. This is to get around the
    # fact that we can't directly kill exec instances.
    # See http://linux.die.net/man/1/timeout
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
