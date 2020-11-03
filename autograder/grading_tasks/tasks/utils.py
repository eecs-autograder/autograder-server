import fnmatch
import os
import tempfile
from io import FileIO
from typing import List, Optional, Union

from autograder_sandbox import SANDBOX_USERNAME, AutograderSandbox, CompletedCommand
from django import db
from django.db import transaction
from django.db.models import QuerySet

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
from autograder.core import constants
from autograder.utils.retry import retry_should_recover


@retry_should_recover
def mark_submission_as_error(submission_pk: int, error_msg: str) -> None:
    with transaction.atomic():
        ag_models.Submission.objects.select_for_update().filter(
            pk=submission_pk
        ).update(status=ag_models.Submission.GradingStatus.error, error_msg=error_msg)


def add_files_to_sandbox(sandbox: AutograderSandbox,
                         suite: Union[ag_models.AGTestSuite, ag_models.MutationTestSuite],
                         submission: ag_models.Submission) -> None:
    student_files_to_add = []
    for student_file in load_queryset_with_retry(suite.student_files_needed.all()):
        matching_files = fnmatch.filter(submission.submitted_filenames,
                                        student_file.pattern)

        @retry_should_recover
        def _get_submission_dir():
            return core_ut.get_submission_dir(submission)

        student_files_to_add += [
            os.path.join(_get_submission_dir(), filename)
            for filename in matching_files]

    if student_files_to_add:
        sandbox.add_files(*student_files_to_add)

    project_files_to_add = [
        file_.abspath for file_
        in load_queryset_with_retry(suite.instructor_files_needed.all())
    ]
    if project_files_to_add:
        owner_and_read_only = {
            'owner': 'root' if suite.read_only_instructor_files else SANDBOX_USERNAME,
            'read_only': suite.read_only_instructor_files
        }
        sandbox.add_files(*project_files_to_add, **owner_and_read_only)


def run_ag_test_command(cmd: ag_models.AGTestCommand,
                        sandbox: AutograderSandbox,
                        ag_test_suite_result: ag_models.AGTestSuiteResult) -> CompletedCommand:
    with FileCloser() as file_closer:
        stdin = get_stdin_file(cmd, ag_test_suite_result)
        file_closer.register_file(stdin)

        return run_command_from_args(
            cmd=cmd.cmd,
            sandbox=sandbox,
            block_process_spawn=cmd.block_process_spawn,
            max_virtual_memory=cmd.virtual_memory_limit if cmd.use_virtual_memory_limit else None,
            timeout=cmd.time_limit,
            stdin=stdin
        )


def run_ag_command(cmd: ag_models.Command, sandbox: AutograderSandbox,
                   cmd_str_override: Optional[str]=None):
    cmd_str = cmd_str_override if cmd_str_override is not None else cmd.cmd
    return run_command_from_args(
        cmd_str,
        sandbox=sandbox,
        block_process_spawn=cmd.block_process_spawn,
        max_virtual_memory=cmd.virtual_memory_limit if cmd.use_virtual_memory_limit else None,
        timeout=cmd.time_limit,
        stdin=None
    )


def run_command_from_args(cmd: str,
                          sandbox: AutograderSandbox,
                          *,
                          max_virtual_memory: Optional[int],
                          block_process_spawn: bool,
                          timeout: int,
                          stdin: Optional[FileIO]=None) -> CompletedCommand:
    run_result = sandbox.run_command(['bash', '-c', cmd],
                                     stdin=stdin,
                                     as_root=False,
                                     max_virtual_memory=max_virtual_memory,
                                     block_process_spawn=block_process_spawn,
                                     timeout=timeout,
                                     truncate_stdout=constants.MAX_RECORDED_OUTPUT_LENGTH,
                                     truncate_stderr=constants.MAX_RECORDED_OUTPUT_LENGTH)
    return run_result


def get_stdin_file(cmd: ag_models.AGTestCommand,
                   ag_test_suite_result: ag_models.AGTestSuiteResult=None) -> Optional[FileIO]:
    if cmd.stdin_source == ag_models.StdinSource.text:
        stdin = tempfile.NamedTemporaryFile()
        stdin.write(cmd.stdin_text.encode())
        stdin.flush()
        stdin.seek(0)
        return stdin
    elif cmd.stdin_source == ag_models.StdinSource.instructor_file:
        return cmd.stdin_instructor_file.open('rb')
    elif cmd.stdin_source == ag_models.StdinSource.setup_stdout:
        if ag_test_suite_result is None:
            raise Exception('Expected ag test suite result, but got None.')

        return ag_test_suite_result.open_setup_stdout('rb')
    elif cmd.stdin_source == ag_models.StdinSource.setup_stderr:
        if ag_test_suite_result is None:
            raise Exception('Expected ag test suite result, but got None.')

        return ag_test_suite_result.open_setup_stderr('rb')
    else:
        return None


class FileCloser:
    def __init__(self):
        self._files_to_close = []  # type: List[FileIO]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for file_ in self._files_to_close:
            file_.close()

    def register_file(self, file_: Optional[FileIO]):
        if file_ is None:
            return
        self._files_to_close.append(file_)


@retry_should_recover
def load_queryset_with_retry(queryset) -> List:
    """
    Given a Django QuerySet, evaluates the queryset and returns
    a list of the queried items.
    If an error occurs, retries the QuerySet evaluation according
    to the retry_should_recover decorator.
    """
    assert isinstance(queryset, QuerySet)
    return list(queryset)
