import os
import subprocess
import uuid

import autograder.shared.global_constants as gc


SANDBOX_WORKING_DIR_NAME = '/home/autograder/working_dir'


class AutograderSandbox(object):
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    def start(self):
        print('starting container: ' + self.name)
        subprocess.check_call(
            ['docker', 'create', '--name=' + self.name,
             # unneeded # '-m', '1000M',  # Memory limit
             # unneeded # '--memory-swap', '2000M',  # Total memory limit (memory + swap)
             # BAAAAAAD!!!!! '--ulimit', 'nproc=5', # Limit number of processes
             '-a', 'STDOUT', '-a', 'STDERR',  # Attach streams
             '-i',  # Run in interactive mode (needed for input redirection)
             '-t',  # Allocate psuedo tty
             'autograder', 'bash']
        )
        try:
            subprocess.call(['docker', 'start', self.name])
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

        subprocess.check_call(
            ['docker', 'exec', self.name, 'chown', 'autograder:autograder'] +
            basenames)

    def run_cmd(self, cmd_exec_args,
                as_root=False,
                timeout=gc.DEFAULT_SUBPROCESS_TIMEOUT,
                stdin_content=''):
        args = ['docker', 'exec', '-i']
        if not as_root:
            args.append('--user=autograder')
        args.append(self.name)
        args += ['timeout', str(timeout)] + cmd_exec_args

        print('running: {}'.format(args))

        runner = _SubprocessRunner(
            args,  # timeout=timeout,
            stdin_content=stdin_content)
        return runner

    def clear_working_dir(self):
        working_dir_contents = subprocess.check_output(
            ['docker', 'exec', '--user=autograder', self.name,
             'ls', SANDBOX_WORKING_DIR_NAME], universal_newlines=True
        ).split()

        backup_dirname = "/home/autograder/old-" + uuid.uuid4().hex
        subprocess.check_call(
            ['docker', 'exec', '--user=autograder', self.name,
             "mkdir", "-p", backup_dirname])

        subprocess.check_call(
            ['docker', 'exec', '--user=autograder', self.name,
             "mv"] + working_dir_contents + [backup_dirname])


# TODO: Once upgraded to Python 3.5 and Django 1.9, replace Popen with the
# new subprocess.run() method.
class _SubprocessRunner(object):
    """
    Convenience wrapper for calling Popen and retrieving the data
    we usually need.
    """
    # HACK: Currently, this class assumes that the command called inside
    # Docker is wrapped in a linux timeout call. This is to get around the
    # fact that we can't directly kill exec instances.
    # See http://linux.die.net/man/1/timeout
    _TIMEOUT_RETURN_CODE = 124

    def __init__(self, program_args, **kwargs):
        self._args = program_args
        # self._timeout = kwargs.get('timeout', gc.DEFAULT_SUBPROCESS_TIMEOUT)
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
        # Note: It is not possible to use string streams
        # (io.StringIO) with subprocess.call() because they do not
        # have a fileno attribute. This is not a huge issue, as using
        # Popen and subprocess.PIPE is the preferred approach to
        # redirecting input and output from strings.
        self._process = subprocess.Popen(
            self._args,
            universal_newlines=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=(subprocess.STDOUT if self._merge_stdout_and_stderr
                    else subprocess.PIPE)
        )

        try:
            self._stdout, self._stderr = self._process.communicate(
                input=self._stdin_content)  # ,#timeout=self._timeout)

            self._process.stdin.close()

            self._return_code = self._process.returncode
            if self._return_code == _SubprocessRunner._TIMEOUT_RETURN_CODE:
                self._timed_out = True

            print(self._process.args)
            print(self._process.returncode)
            print(self._stdout)
            print(self._stderr)
            # print(self._process.stdin.read())
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._stdout, self._stderr = self._process.communicate()
            self._return_code = self._process.returncode
            self._timed_out = True

            self._process.stdin.close()
        except UnicodeDecodeError:
            msg = ("Error reading program output: "
                   "non-unicode characters detected")
            self._stdout = msg
            self._stderr = msg

            self._process.stdin.close()
