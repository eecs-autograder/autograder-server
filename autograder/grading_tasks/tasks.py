import fnmatch
import os
import shlex
import shutil
import tempfile
import time
import traceback
import uuid
from io import FileIO
from typing import Tuple

from django.conf import settings
from django.db import transaction

import celery

import autograder.core.models as ag_models
from autograder.core import constants
import autograder.core.utils as core_ut
from autograder_sandbox import AutograderSandbox, SANDBOX_USERNAME


class MaxRetriesExceeded(Exception):
    pass


def retry(max_num_retries,
          retry_delay_start=0,
          retry_delay_end=0,
          retry_delay_step=None):
    """
    Returns a decorator that applies a synchronous retry loop to the
    decorated function.

    :param max_num_retries: The maximum number of times the decorated
        function can be retried before raising an exception. This
        parameter must be greater than zero.

    :param retry_delay_start: The delay time, in seconds, before retrying
        the function for the first time.

    :param retry_delay_end: The delay time, in seconds, before retrying
        the function for the last time.

    :param retry_delay_step: The number of seconds to increase the retry
        delay for each consecutive retry. If None, defaults to
        (retry_delay_end - retry_delay_start) / max_num_retries
    """
    if retry_delay_step is None:
        retry_delay_step = (retry_delay_end - retry_delay_start) / max_num_retries

    def decorator(func):
        def func_with_retry(*args, **kwargs):
            num_retries_remaining = max_num_retries
            retry_delay = retry_delay_start
            latest_exception = None
            while num_retries_remaining >= 0:
                try:
                    return func(*args, **kwargs)
                except Exception as e:  # TODO: handle certain database errors differently
                    print('Error in', func.__name__)
                    traceback.print_exc()
                    print('Will try again in', retry_delay, 'seconds')
                    num_retries_remaining -= 1
                    time.sleep(retry_delay)
                    retry_delay += retry_delay_step
                    latest_exception = traceback.format_exc()

            raise MaxRetriesExceeded(latest_exception)

        return func_with_retry

    return decorator


# Specialization of the "retry" decorator to be used for synchronous
# tasks that should always succeed unless there is a database issue.
retry_should_recover = retry(max_num_retries=60,
                             retry_delay_start=1, retry_delay_end=60)
# Specialization of the "retry" to be used for grading non-deferred
# autograder test cases.
retry_ag_test_cmd = retry(max_num_retries=settings.AG_TEST_MAX_RETRIES,
                          retry_delay_start=settings.AG_TEST_MIN_RETRY_DELAY,
                          retry_delay_end=settings.AG_TEST_MAX_RETRY_DELAY)


@celery.shared_task(acks_late=True)
def grade_submission(submission_pk):
    try:
        submission = _mark_submission_as_being_graded(submission_pk)
        if submission is None:
            return

        project = submission.submission_group.project

        @retry_should_recover
        def load_non_deferred_suites():
            return list(project.ag_test_suites.filter(deferred=False))

        for suite in load_non_deferred_suites():
            grade_ag_test_suite_impl(suite, submission)

        @retry_should_recover
        def mark_as_waiting_for_deferred():
            submission.status = (
                ag_models.Submission.GradingStatus.waiting_for_deferred)
            submission.save()

        mark_as_waiting_for_deferred()

        @retry_should_recover
        def load_deferred_suites():
            return list(project.ag_test_suites.filter(deferred=True))

        signatures = [grade_deferred_ag_test_suite.s(ag_test_suite.pk, submission_pk)
                      for ag_test_suite in load_deferred_suites()]
        if not signatures:
            _mark_submission_as_finished_impl(submission_pk)
            return

        if len(signatures) == 1:
            signatures[0].apply_async(
                link_error=on_chord_error.s(),
                link=mark_submission_as_finished.s(submission_pk))
        else:
            callback = mark_submission_as_finished.s(submission_pk).on_error(on_chord_error.s())
            celery.chord(signatures)(callback)
    except Exception:
        print('Error grading submission')
        traceback.print_exc()
        _mark_submission_as_error(submission_pk, traceback.format_exc())
        raise


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
        _mark_submission_as_error(submission_pk, traceback.format_exc())
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
        allow_network_access=ag_test_suite.allow_network_access)
    with sandbox:
        _add_files_to_sandbox(sandbox, ag_test_suite, submission)

        _run_suite_setup(sandbox, ag_test_suite, suite_result)

        for ag_test_case in ag_test_suite.ag_test_cases.all():
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

        @retry_should_recover
        def save_ag_test_cmd_result():
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


@retry_should_recover
def _mark_submission_as_being_graded(submission_pk):
    with transaction.atomic():
        submission = ag_models.Submission.objects.select_for_update().select_related(
            'submission_group__project').get(pk=submission_pk)
        if (submission.status ==
                ag_models.Submission.GradingStatus.removed_from_queue):
            print('submission {} has been removed '
                  'from the queue'.format(submission.pk))
            return None

        submission.status = ag_models.Submission.GradingStatus.being_graded
        submission.save()
        return submission


@celery.shared_task(queue='small_tasks', acks_late=True)
def mark_submission_as_finished(chord_results, submission_pk):
    _mark_submission_as_finished_impl(submission_pk)


@celery.shared_task(queue='small_tasks', acks_late=True)
def on_chord_error(request, exc, traceback):
    print('Error in deferred test case chord. '
          'This most likely means that a deferred test '
          'case exceeded the retry limit.')
    print(traceback)
    print(exc)


@retry_should_recover
def _mark_submission_as_finished_impl(submission_pk):
    ag_models.Submission.objects.filter(
        pk=submission_pk
    ).update(status=ag_models.Submission.GradingStatus.finished_grading)


@retry_should_recover
def _mark_submission_as_error(submission_pk, error_msg):
    with transaction.atomic():
        submission = ag_models.Submission.objects.select_for_update().filter(
            pk=submission_pk).update(status=ag_models.Submission.GradingStatus.error,
                                     error_msg=error_msg)


@celery.shared_task
def queue_submissions():
    with transaction.atomic():
        to_queue = list(ag_models.Submission.objects.select_for_update().filter(
            status=ag_models.Submission.GradingStatus.received).reverse())
        print(to_queue)

        for submission in to_queue:
            print('adding submission{} to queue for grading'.format(submission.pk))
            submission.status = ag_models.Submission.GradingStatus.queued
            submission.save()
            grade_submission.apply_async([submission.pk],
                                         queue=_get_submission_queue_name(submission))

        print('queued {} submissions'.format(to_queue))


@celery.shared_task(acks_late=True, autoretry_for=(Exception,))
def register_project_queues(worker_names=None, project_pks=None):
    from autograder.celery import app

    if not worker_names:
        worker_names = [worker_name for worker_name in app.control.inspect().active()
                        if worker_name.startswith(settings.SUBMISSION_WORKER_PREFIX)]

    print('worker names', worker_names)
    if not worker_names:
        return

    if not project_pks:
        project_pks = [project.pk for project in ag_models.Project.objects.all()]

    print('project pks:', project_pks)
    for pk in project_pks:
        res = app.control.add_consumer('project{}'.format(pk), destination=worker_names)
        print(res)


def _get_submission_queue_name(submission: ag_models.Submission):
    return 'project{}'.format(submission.submission_group.project_id)
