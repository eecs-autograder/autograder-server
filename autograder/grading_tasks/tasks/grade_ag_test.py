import shutil
import tempfile
import traceback
import uuid
from io import FileIO
from typing import Tuple

import celery
from autograder_sandbox import AutograderSandbox
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
from autograder.core import constants
from autograder.core.submission_feedback import \
    update_denormalized_ag_test_results

from .utils import (FileCloser, add_files_to_sandbox, mark_submission_as_error,
                    retry_ag_test_cmd, retry_should_recover,
                    run_ag_test_command, run_command_from_args)


@celery.shared_task(bind=True, queue='deferred', max_retries=1, acks_late=True)
def grade_deferred_ag_test_suite(self, ag_test_suite_pk, submission_pk):
    @retry_should_recover
    def _grade_deferred_ag_test_suite_impl():
        try:
            grade_ag_test_suite_impl(ag_models.AGTestSuite.objects.get(pk=ag_test_suite_pk),
                                     ag_models.Submission.objects.get(pk=submission_pk))
        except ObjectDoesNotExist:
            # This means that the suite was deleted, so we skip it.
            pass

    try:
        _grade_deferred_ag_test_suite_impl()
    except Exception:
        print('Error grading deferred test')
        traceback.print_exc()
        mark_submission_as_error(submission_pk, traceback.format_exc())
        raise


def grade_ag_test_suite_impl(ag_test_suite: ag_models.AGTestSuite,
                             submission: ag_models.Submission,
                             *ag_test_cases_to_run: ag_models.AGTestCase):
    @retry_should_recover
    def get_or_create_suite_result():
        try:
            return ag_models.AGTestSuiteResult.objects.get_or_create(
                ag_test_suite=ag_test_suite, submission=submission)[0]
        except IntegrityError:
            # The suite was deleted, so we skip it.
            return None

    suite_result = get_or_create_suite_result()
    if suite_result is None:
        return

    sandbox = AutograderSandbox(
        name='submission{}-suite{}-{}'.format(submission.pk, ag_test_suite.pk, uuid.uuid4().hex),
        environment_variables={
            'usernames': ' '.join(submission.group.member_names)
        },
        allow_network_access=ag_test_suite.allow_network_access,
        docker_image=ag_test_suite.sandbox_docker_image.tag)
    print(ag_test_suite.sandbox_docker_image.to_dict())
    print(sandbox.docker_image)
    with sandbox:
        add_files_to_sandbox(sandbox, ag_test_suite, submission)

        print('Running setup for', ag_test_suite.name)
        _run_suite_setup(sandbox, ag_test_suite, suite_result)

        if not ag_test_cases_to_run:
            ag_test_cases_to_run = ag_test_suite.ag_test_cases.all()

        for ag_test_case in ag_test_cases_to_run:
            print('Grading test case', ag_test_case.name)
            grade_ag_test_case_impl(sandbox, ag_test_case, suite_result)

        update_denormalized_ag_test_results(submission.pk)


@retry_ag_test_cmd
def _run_suite_setup(sandbox: AutograderSandbox,
                     ag_test_suite: ag_models.AGTestSuite,
                     suite_result: ag_models.AGTestSuiteResult):
    if not ag_test_suite.setup_suite_cmd:
        # Erase the setup output files.
        with open(suite_result.setup_stdout_filename, 'wb') as f:
            pass
        with open(suite_result.setup_stderr_filename, 'wb') as f:
            pass

        return

    setup_result = run_command_from_args(
        cmd=ag_test_suite.setup_suite_cmd,
        sandbox=sandbox,
        max_num_processes=constants.MAX_PROCESS_LIMIT,
        max_stack_size=constants.MAX_STACK_SIZE_LIMIT,
        max_virtual_memory=constants.MAX_VIRTUAL_MEM_LIMIT,
        timeout=constants.MAX_SUBPROCESS_TIMEOUT)
    suite_result.setup_return_code = setup_result.return_code
    suite_result.setup_timed_out = setup_result.timed_out
    suite_result.setup_stdout_truncated = setup_result.stdout_truncated
    suite_result.setup_stderr_truncated = setup_result.stderr_truncated

    with open(suite_result.setup_stdout_filename, 'wb') as f:
        shutil.copyfileobj(setup_result.stdout, f)
    with open(suite_result.setup_stderr_filename, 'wb') as f:
        shutil.copyfileobj(setup_result.stderr, f)

    @retry_should_recover
    def _save_suite_result():
        suite_result.save()

    _save_suite_result()


def grade_ag_test_case_impl(sandbox: AutograderSandbox,
                            ag_test_case: ag_models.AGTestCase,
                            suite_result: ag_models.AGTestSuiteResult):
    @retry_should_recover
    def get_or_create_ag_test_case_result():
        try:
            return ag_models.AGTestCaseResult.objects.get_or_create(
                ag_test_case=ag_test_case, ag_test_suite_result=suite_result)[0]
        except IntegrityError:
            # The AGTestCase or AGSuiteResult has been deleted.
            return None

    case_result = get_or_create_ag_test_case_result()
    if case_result is None:
        return

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
        run_result = run_ag_test_command(ag_test_cmd, sandbox, case_result.ag_test_suite_result)

        result_data = {
            'return_code': run_result.return_code,
            'timed_out': run_result.timed_out,
            'stdout_truncated': run_result.stdout_truncated,
            'stderr_truncated': run_result.stderr_truncated,
        }

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
            try:
                with transaction.atomic():
                    cmd_result = ag_models.AGTestCommandResult.objects.update_or_create(
                        defaults=result_data,
                        ag_test_command=ag_test_cmd,
                        ag_test_case_result=case_result)[0]  # type: ag_models.AGTestCommandResult

                    with open(cmd_result.stdout_filename, 'wb') as f:
                        shutil.copyfileobj(run_result.stdout, f)
                    with open(cmd_result.stderr_filename, 'wb') as f:
                        shutil.copyfileobj(run_result.stderr, f)
            except IntegrityError:
                # The command or case result has likely been deleted
                return

        save_ag_test_cmd_result()


def _get_expected_stdout_file_and_name(
        ag_test_cmd: ag_models.AGTestCommand) -> Tuple[FileIO, str]:
    expected_stdout = None
    expected_stdout_filename = None
    if ag_test_cmd.expected_stdout_source == ag_models.ExpectedOutputSource.text:
        expected_stdout = tempfile.NamedTemporaryFile()
        expected_stdout.write(ag_test_cmd.expected_stdout_text.encode())
        expected_stdout.flush()
        expected_stdout_filename = expected_stdout.name
    elif ag_test_cmd.expected_stdout_source == ag_models.ExpectedOutputSource.instructor_file:
        expected_stdout_filename = ag_test_cmd.expected_stdout_instructor_file.abspath

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
    elif ag_test_cmd.expected_stderr_source == ag_models.ExpectedOutputSource.instructor_file:
        expected_stderr_filename = ag_test_cmd.expected_stderr_instructor_file.abspath

    return expected_stderr, expected_stderr_filename
