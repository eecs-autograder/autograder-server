import fnmatch
import os
import shlex
import shutil
import tempfile
import traceback
import uuid
from io import FileIO
from typing import List
from typing import Tuple

import celery

from autograder_sandbox import AutograderSandbox
from autograder_sandbox import SANDBOX_USERNAME
from django.db import transaction

import autograder.core.models as ag_models
from autograder.core import constants
import autograder.core.utils as core_ut
from .utils import retry_should_recover, retry_ag_test_cmd, mark_submission_as_error


@celery.shared_task(bind=True, queue='deferred', max_retries=1, acks_late=True)
def grade_deferred_ag_test_suite(self, ag_test_suite_pk, submission_pk):

    @retry_should_recover
    def _grade_deferred_ag_test_suite_impl():
        grade_ag_test_suite_impl(ag_models.AGTestSuite.objects.get(pk=ag_test_suite_pk),
                                 ag_models.Submission.objects.get(pk=submission_pk))

    try:
        _grade_deferred_ag_test_suite_impl()
    except Exception:
        print('Error grading deferred test')
        traceback.print_exc()
        mark_submission_as_error(submission_pk, traceback.format_exc())
        raise


# TODO: take in list of test cases to rerun
def grade_ag_test_suite_impl(ag_test_suite: ag_models.AGTestSuite,
                             submission: ag_models.Submission):
    @retry_should_recover
    def get_or_create_suite_result():
        return ag_models.AGTestSuiteResult.objects.get_or_create(
            ag_test_suite=ag_test_suite, submission=submission)[0]

    suite_result = get_or_create_suite_result()

    sandbox = AutograderSandbox(
        name='submission{}-suite{}-{}'.format(submission.pk, ag_test_suite.pk, uuid.uuid4().hex),
        environment_variables={
            'usernames': ' '.join(sorted(submission.submission_group.member_names))
        },
        allow_network_access=ag_test_suite.allow_network_access,
        docker_image=constants.DOCKER_IMAGE_IDS_TO_URLS[ag_test_suite.docker_image_to_use])
    print(ag_test_suite.docker_image_to_use)
    print(sandbox.docker_image)
    with sandbox:
        _add_files_to_sandbox(sandbox, ag_test_suite, submission)

        print('Running setup for', ag_test_suite.name)
        _run_suite_setup(sandbox, ag_test_suite, suite_result)

        for ag_test_case in ag_test_suite.ag_test_cases.all():
            print('Grading test case', ag_test_case.name)
            grade_ag_test_case_impl(sandbox, ag_test_case, suite_result)

        _run_suite_teardown(sandbox, ag_test_suite, suite_result)


def _add_files_to_sandbox(sandbox: AutograderSandbox,
                          ag_test_suite: ag_models.AGTestSuite,
                          submission: ag_models.Submission):
    student_files_to_add = []
    for student_file in ag_test_suite.student_files_needed.all():
        matching_files = fnmatch.filter(submission.submitted_filenames,
                                        student_file.pattern)
        student_files_to_add += [
            os.path.join(core_ut.get_submission_dir(submission), filename)
            for filename in matching_files]

    if student_files_to_add:
        sandbox.add_files(*student_files_to_add)

    project_files_to_add = [file_.abspath for file_ in ag_test_suite.project_files_needed.all()]
    if project_files_to_add:
        owner_and_read_only = {
            'owner': 'root' if ag_test_suite.read_only_project_files else SANDBOX_USERNAME,
            'read_only': ag_test_suite.read_only_project_files
        }
        sandbox.add_files(*project_files_to_add, **owner_and_read_only)


@retry_ag_test_cmd
def _run_suite_setup(sandbox: AutograderSandbox,
                     ag_test_suite: ag_models.AGTestSuite,
                     suite_result: ag_models.AGTestSuiteResult):
    if not ag_test_suite.setup_suite_cmd:
        return

    setup_result = sandbox.run_command(shlex.split(ag_test_suite.setup_suite_cmd),
                                       as_root=False,
                                       max_num_processes=constants.MAX_PROCESS_LIMIT,
                                       max_stack_size=constants.MAX_STACK_SIZE_LIMIT,
                                       max_virtual_memory=constants.MAX_VIRTUAL_MEM_LIMIT,
                                       timeout=constants.MAX_SUBPROCESS_TIMEOUT,
                                       truncate_stdout=constants.MAX_OUTPUT_LENGTH,
                                       truncate_stderr=constants.MAX_OUTPUT_LENGTH)
    suite_result.setup_return_code = setup_result.return_code
    suite_result.setup_timed_out = setup_result.timed_out
    suite_result.setup_stdout_truncated = setup_result.stdout_truncated
    suite_result.setup_stderr_truncated = setup_result.stderr_truncated
    shutil.move(setup_result.stdout.name, suite_result.setup_stdout_filename)
    shutil.move(setup_result.stderr.name, suite_result.setup_stderr_filename)

    suite_result.save()


@retry_ag_test_cmd
def _run_suite_teardown(sandbox: AutograderSandbox,
                        ag_test_suite: ag_models.AGTestSuite,
                        suite_result: ag_models.AGTestSuiteResult):
    if not ag_test_suite.teardown_suite_cmd:
        return

    teardown_result = sandbox.run_command(shlex.split(ag_test_suite.teardown_suite_cmd),
                                          as_root=False,
                                          max_num_processes=constants.MAX_PROCESS_LIMIT,
                                          max_stack_size=constants.MAX_STACK_SIZE_LIMIT,
                                          max_virtual_memory=constants.MAX_VIRTUAL_MEM_LIMIT,
                                          timeout=constants.MAX_SUBPROCESS_TIMEOUT,
                                          truncate_stdout=constants.MAX_OUTPUT_LENGTH,
                                          truncate_stderr=constants.MAX_OUTPUT_LENGTH)
    suite_result.teardown_return_code = teardown_result.return_code
    suite_result.teardown_timed_out = teardown_result.timed_out
    suite_result.teardown_stdout_truncated = teardown_result.stdout_truncated
    suite_result.teardown_stderr_truncated = teardown_result.stderr_truncated
    shutil.move(teardown_result.stdout.name, suite_result.teardown_stdout_filename)
    shutil.move(teardown_result.stderr.name, suite_result.teardown_stderr_filename)

    suite_result.save()


def grade_ag_test_case_impl(sandbox: AutograderSandbox,
                            ag_test_case: ag_models.AGTestCase,
                            suite_result: ag_models.AGTestSuiteResult):
    @retry_should_recover
    def get_or_create_ag_test_case_result():
        return ag_models.AGTestCaseResult.objects.get_or_create(
            ag_test_case=ag_test_case, ag_test_suite_result=suite_result)[0]

    case_result = get_or_create_ag_test_case_result()

    @retry_ag_test_cmd
    def _grade_ag_test_cmd_with_retry(ag_test_cmd, case_result):
        grade_ag_test_command_impl(sandbox, ag_test_cmd, case_result)

    for ag_test_cmd in ag_test_case.ag_test_commands.all():
        print('Running command', ag_test_cmd.name)
        _grade_ag_test_cmd_with_retry(ag_test_cmd, case_result)


def grade_ag_test_command_impl(sandbox: AutograderSandbox,
                               ag_test_cmd: ag_models.AGTestCommand,
                               case_result: ag_models.AGTestCaseResult):
    with FileCloser() as file_closer:
        stdin = _get_stdin_file(ag_test_cmd, case_result)
        file_closer.register_file(stdin)

        result_data = {}

        run_result = sandbox.run_command(shlex.split(ag_test_cmd.cmd),
                                         stdin=stdin,
                                         as_root=False,
                                         max_num_processes=ag_test_cmd.process_spawn_limit,
                                         max_stack_size=ag_test_cmd.stack_size_limit,
                                         max_virtual_memory=ag_test_cmd.virtual_memory_limit,
                                         timeout=ag_test_cmd.time_limit,
                                         truncate_stdout=constants.MAX_OUTPUT_LENGTH,
                                         truncate_stderr=constants.MAX_OUTPUT_LENGTH)

        result_data['return_code'] = run_result.return_code
        result_data['timed_out'] = run_result.timed_out
        result_data['stdout_truncated'] = run_result.stdout_truncated
        result_data['stderr_truncated'] = run_result.stderr_truncated

        if ag_test_cmd.expected_return_code == ag_models.ExpectedReturnCode.zero:
            result_data['return_code_correct'] = run_result.return_code == 0
        elif ag_test_cmd.expected_return_code == ag_models.ExpectedReturnCode.nonzero:
            result_data['return_code_correct'] = run_result.return_code != 0

        expected_stdout, expected_stdout_filename = _get_expected_stdout_file_and_name(ag_test_cmd)
        file_closer.register_file(expected_stdout)

        if expected_stdout_filename is not None:
            diff = core_ut.get_diff(
                expected_stdout_filename, run_result.stdout.name,
                ignore_case=ag_test_cmd.ignore_case,
                ignore_whitespace=ag_test_cmd.ignore_whitespace,
                ignore_whitespace_changes=ag_test_cmd.ignore_whitespace_changes,
                ignore_blank_lines=ag_test_cmd.ignore_blank_lines)
            result_data['stdout_correct'] = diff.diff_pass

        expected_stderr, expected_stderr_filename = _get_expected_stderr_file_and_name(ag_test_cmd)
        file_closer.register_file(expected_stderr)

        if expected_stderr_filename is not None:
            diff = core_ut.get_diff(
                expected_stderr_filename, run_result.stderr.name,
                ignore_case=ag_test_cmd.ignore_case,
                ignore_whitespace=ag_test_cmd.ignore_whitespace,
                ignore_whitespace_changes=ag_test_cmd.ignore_whitespace_changes,
                ignore_blank_lines=ag_test_cmd.ignore_blank_lines)
            result_data['stderr_correct'] = diff.diff_pass

        print(result_data)

        @retry_should_recover
        def save_ag_test_cmd_result():
            with transaction.atomic():
                cmd_result = ag_models.AGTestCommandResult.objects.update_or_create(
                    defaults=result_data,
                    ag_test_command=ag_test_cmd,
                    ag_test_case_result=case_result)[0]  # type: ag_models.AGTestCommandResult

                shutil.move(run_result.stdout.name, cmd_result.stdout_filename)
                shutil.move(run_result.stderr.name, cmd_result.stderr_filename)

        save_ag_test_cmd_result()


def _get_stdin_file(ag_test_cmd: ag_models.AGTestCommand, case_result: ag_models.AGTestCaseResult):
    if ag_test_cmd.stdin_source == ag_models.StdinSource.text:
        stdin = tempfile.NamedTemporaryFile()
        stdin.write(ag_test_cmd.stdin_text.encode())
        stdin.flush()
        stdin.seek(0)
        return stdin
    elif ag_test_cmd.stdin_source == ag_models.StdinSource.project_file:
        return ag_test_cmd.stdin_project_file.open('rb')
    elif ag_test_cmd.stdin_source == ag_models.StdinSource.setup_stdout:
        return case_result.ag_test_suite_result.open_setup_stdout('rb')
    elif ag_test_cmd.stdin_source == ag_models.StdinSource.setup_stderr:
        return case_result.ag_test_suite_result.open_setup_stderr('rb')
    else:
        return None


def _get_expected_stdout_file_and_name(
        ag_test_cmd: ag_models.AGTestCommand) -> Tuple[FileIO, str]:
    expected_stdout = None
    expected_stdout_filename = None
    if ag_test_cmd.expected_stdout_source == ag_models.ExpectedOutputSource.text:
        expected_stdout = tempfile.NamedTemporaryFile()
        expected_stdout.write(ag_test_cmd.expected_stdout_text.encode())
        expected_stdout.flush()
        expected_stdout_filename = expected_stdout.name
    elif ag_test_cmd.expected_stdout_source == ag_models.ExpectedOutputSource.project_file:
        expected_stdout_filename = ag_test_cmd.expected_stdout_project_file.abspath

    return expected_stdout, expected_stdout_filename


def _get_expected_stderr_file_and_name(
        ag_test_cmd: ag_models.AGTestCommand) -> Tuple[FileIO, str]:
    expected_stderr = None
    expected_stderr_filename = None
    if ag_test_cmd.expected_stderr_source == ag_models.ExpectedOutputSource.text:
        expected_stderr = tempfile.NamedTemporaryFile()
        expected_stderr.write(ag_test_cmd.expected_stderr_text.encode())
        expected_stderr.flush()
        expected_stderr_filename = expected_stderr.name
    elif ag_test_cmd.expected_stderr_source == ag_models.ExpectedOutputSource.project_file:
        expected_stderr_filename = ag_test_cmd.expected_stderr_project_file.abspath

    return expected_stderr, expected_stderr_filename


class FileCloser:
    def __init__(self):
        self._files_to_close = []  # type: List[FileIO]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for file_ in self._files_to_close:
            file_.close()

    def register_file(self, file_: FileIO):
        if file_ is None:
            return
        self._files_to_close.append(file_)
