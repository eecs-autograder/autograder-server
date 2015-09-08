import os
import subprocess

import autograder.shared.global_constants as gc


def _get_docker_args():
    return [
        'docker', 'run',
        '-a', 'STDIN', '-a', 'STDOUT', '-a', 'STDERR',  # Attach streams
        '--rm',  # Delete the container when finished running
        '-m', '500M',  # Memory limit
        '--memory-swap', '750M',  # Total memory limit (memory + swap)
        '--ulimit', 'nproc=5',  # Limit number of processes
        '-v', os.getcwd() + ':/home/autograder',  # Mount the current directory
        '-w', '/home/autograder',  # Set working directory in container
        # '-u', 'autograder',  # set user (root by default, but we don't want that)
        '-i',  # Run in interactive mode (needed for input redirection)
        'autograder'  # Specify which image to use
    ]


# TODO: Once upgraded to Python 3.5 and Django 1.9, replace Popen with the
# new subprocess.run() method.
class SubprocessRunner(object):
    """
    Convenience wrapper for calling Popen and retrieving the data
    we usually need.
    """
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
        # Note: It is not possible to use string streams
        # (io.StringIO) with subprocess.call() because they do not
        # have a fileno attribute. This is not a huge issue, as using
        # Popen and subprocess.PIPE is the preferred approach to
        # redirecting input and output from strings.
        self._process = subprocess.Popen(
            _get_docker_args() + self._args,
            universal_newlines=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=(subprocess.STDOUT if self._merge_stdout_and_stderr
                    else subprocess.PIPE)
        )

        try:
            self._stdout, self._stderr = self._process.communicate(
                input=self._stdin_content,
                timeout=self._timeout)

            self._process.stdin.close()

            self._return_code = self._process.returncode

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
