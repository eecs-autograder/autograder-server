import fnmatch
import os
import shlex
import subprocess
import time
import traceback
import uuid

from django.conf import settings
from django.db import transaction

import celery

import autograder.core.models as ag_models
from autograder.core import constants
import autograder.core.utils as core_ut
from autograder_sandbox import AutograderSandbox


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


@celery.shared_task(queue='submissions', acks_late=True)
def grade_submission(submission_pk):
    try:
        submission = _mark_submission_as_being_graded(submission_pk)
        if submission is None:
            return

        project = submission.submission_group.project
        for suite in project.ag_test_suites.filter(deferred=False):
            grade_ag_test_suite_impl(suite, submission)

        @retry_should_recover
        def mark_as_waiting_for_deferred():
            submission.status = (
                ag_models.Submission.GradingStatus.waiting_for_deferred)
            submission.save()

        mark_as_waiting_for_deferred()

        deferred_queryset = project.ag_test_suites.filter(deferred=True)
        signatures = [grade_deferred_ag_test_suite.s(ag_test_suite.pk, submission_pk)
                      for ag_test_suite in deferred_queryset]
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


@celery.shared_task(bind=True, max_retries=1, queue='deferred', acks_late=True)
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


# FIXME: TEST AND ADD RETRY STUFF
# TODO: take in list of test cases to rerun
def grade_ag_test_suite_impl(ag_test_suite: ag_models.AGTestSuite,
                             submission: ag_models.Submission):
    suite_result = ag_models.AGTestSuiteResult.objects.get_or_create(
        ag_test_suite=ag_test_suite, submission=submission)[0]

    sandbox = AutograderSandbox(
        name='submission{}-suite{}-{}'.format(submission.pk, ag_test_suite.pk, uuid.uuid4().hex),
        environment_variables={
            'usernames': ' '.join(sorted(submission.submission_group.member_names))
        },
        allow_network_access=ag_test_suite.allow_network_access)
    with sandbox:
        _add_files_to_sandbox(sandbox, ag_test_suite, submission)

        try:
            setup_result = sandbox.run_command(shlex.split(ag_test_suite.setup_suite_cmd),
                                               as_root=False,
                                               max_num_processes=constants.MAX_PROCESS_LIMIT,
                                               max_stack_size=constants.MAX_STACK_SIZE_LIMIT,
                                               max_virtual_memory=constants.MAX_VIRTUAL_MEM_LIMIT,
                                               timeout=constants.MAX_SUBPROCESS_TIMEOUT)
            suite_result.setup_return_code = setup_result.returncode
            suite_result.setup_stdout = setup_result.stdout
            suite_result.setup_stderr = setup_result.stderr
        except subprocess.TimeoutExpired as e:
            suite_result.setup_timed_out = True
            suite_result.setup_stdout = e.stdout
            suite_result.setup_stderr = e.stderr
        finally:
            suite_result.save()

        # run test cases
        for ag_test_case in ag_test_suite.ag_test_cases.all():
            grade_ag_test_case_impl(sandbox, ag_test_case, suite_result)

        try:
            teardown_result = sandbox.run_command(shlex.split(ag_test_suite.teardown_suite_cmd),
                                                  as_root=False,
                                                  max_num_processes=constants.MAX_PROCESS_LIMIT,
                                                  max_stack_size=constants.MAX_STACK_SIZE_LIMIT,
                                                  max_virtual_memory=constants.MAX_VIRTUAL_MEM_LIMIT,
                                                  timeout=constants.MAX_SUBPROCESS_TIMEOUT)
            suite_result.teardown_return_code = teardown_result.returncode
            suite_result.teardown_stdout = teardown_result.stdout
            suite_result.teardown_stderr = teardown_result.stderr
        except subprocess.TimeoutExpired as e:
            suite_result.teardown_timed_out = True
            suite_result.teardown_stdout = e.stdout
            suite_result.teardown_stderr = e.stderr
        finally:
            suite_result.save()


# FIXME: TEST AND ADD RETRY STUFF
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
        sandbox.add_files(*project_files_to_add)

# FIXME: TEST AND ADD RETRY STUFF
def grade_ag_test_case_impl(sandbox: AutograderSandbox,
                            ag_test_case: ag_models.AGTestCase,
                            suite_result: ag_models.AGTestSuiteResult):
    case_result = ag_models.AGTestCaseResult.objects.get_or_create(
        ag_test_case=ag_test_case, ag_test_suite_result=suite_result)[0]

    @retry_ag_test_cmd
    def _grade_ag_test_cmd_with_retry(sandbox, ag_test_cmd, case_result):
        grade_ag_test_command_impl(sandbox, ag_test_cmd, case_result)

    for ag_test_cmd in ag_test_case.ag_test_commands.all():
        _grade_ag_test_cmd_with_retry(sandbox, ag_test_cmd, case_result)

# FIXME: TEST AND ADD RETRY STUFF
def grade_ag_test_command_impl(sandbox: AutograderSandbox,
                               ag_test_cmd: ag_models.AGTestCommand,
                               case_result: ag_models.AGTestCaseResult):
    if ag_test_cmd.stdin_source == ag_models.StdinSource.text:
        stdin = ag_test_cmd.stdin_text
    elif ag_test_cmd.stdin_source == ag_models.StdinSource.project_file:
        with ag_test_cmd.stdin_project_file.open() as f:
            stdin = f.read()
    elif ag_test_cmd.stdin_source == ag_models.StdinSource.setup_stdout:
        stdin = case_result.ag_test_suite_result.setup_stdout
    elif ag_test_cmd.stdin_source == ag_models.StdinSource.setup_stderr:
        stdin = case_result.ag_test_suite_result.setup_stderr
    else:
        stdin = ''

    try:
        run_result = sandbox.run_command(shlex.split(ag_test_cmd.cmd),
                                         input=stdin,
                                         as_root=False,
                                         max_num_processes=ag_test_cmd.process_spawn_limit,
                                         max_stack_size=ag_test_cmd.stack_size_limit,
                                         max_virtual_memory=ag_test_cmd.virtual_memory_limit,
                                         timeout=ag_test_cmd.time_limit)
        result_data = {
            'stdout': run_result.stdout,
            'stderr': run_result.stderr,
            'return_code': run_result.returncode
        }
        if ag_test_cmd.expected_return_code == ag_models.ExpectedReturnCode.zero:
            result_data['return_code_correct'] = run_result.returncode == 0
        elif ag_test_cmd.expected_return_code == ag_models.ExpectedReturnCode.nonzero:
            result_data['return_code_correct'] = run_result.returncode != 0

        expected_stdout = None
        if ag_test_cmd.expected_stdout_source == ag_models.ExpectedOutputSource.text:
            expected_stdout = ag_test_cmd.expected_stdout_text
        elif ag_test_cmd.expected_stdout_source == ag_models.ExpectedOutputSource.project_file:
            with ag_test_cmd.expected_stdout_project_file.open() as f:
                expected_stdout = f.read()

        if expected_stdout is not None:
            result_data['stdout_correct'] = not core_ut.get_diff(
                expected_stdout, run_result.stdout,
                ignore_case=ag_test_cmd.ignore_case,
                ignore_whitespace=ag_test_cmd.ignore_whitespace,
                ignore_whitespace_changes=ag_test_cmd.ignore_whitespace_changes,
                ignore_blank_lines=ag_test_cmd.ignore_blank_lines)

        expected_stderr = None
        if ag_test_cmd.expected_stderr_source == ag_models.ExpectedOutputSource.text:
            expected_stderr = ag_test_cmd.expected_stderr_text
        elif ag_test_cmd.expected_stderr_source == ag_models.ExpectedOutputSource.project_file:
            with ag_test_cmd.expected_stderr_project_file.open() as f:
                expected_stderr = f.read()

        if expected_stderr is not None:
            result_data['stderr_correct'] = not core_ut.get_diff(
                expected_stderr, run_result.stderr,
                ignore_case=ag_test_cmd.ignore_case,
                ignore_whitespace=ag_test_cmd.ignore_whitespace,
                ignore_whitespace_changes=ag_test_cmd.ignore_whitespace_changes,
                ignore_blank_lines=ag_test_cmd.ignore_blank_lines)

        ag_models.AGTestCommandResult.objects.get_or_create(
            ag_test_command=ag_test_cmd,
            ag_test_case_result=case_result,
            **result_data)
    except subprocess.TimeoutExpired as e:
        ag_models.AGTestCommandResult.objects.get_or_create(
            ag_test_command=ag_test_cmd,
            ag_test_case_result=case_result,
            stdout=e.stdout,
            stderr=e.stderr,
            timed_out=True)
    # FIXME: TEST AND ADD RETRY STUFF)


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


@celery.shared_task(queue='deferred', acks_late=True)
def mark_submission_as_finished(chord_results, submission_pk):
    _mark_submission_as_finished_impl(submission_pk)


@celery.shared_task(queue='deferred', acks_late=True)
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
    # TODO: integration test
    # TODO: update this to support multiple courses in one system.
    #       To do this, load all submissions and group by project. Then,
    #       do a "round robin" submission queueing so that one project
    #       doesn't hog all the grading resources. Do we need to limit the
    #       number of queued submissions to the number of grading workers?
    #       We essentially want to create the illusion that each project gets
    #       an equal number of dedicated workers.
    with transaction.atomic():
        to_queue = list(ag_models.Submission.objects.select_for_update().filter(
            status=ag_models.Submission.GradingStatus.received).reverse())
        print(to_queue)

        for submission in to_queue:
            print('adding submission{} to queue for grading'.format(submission.pk))
            submission.status = 'queued'
            submission.save()
            grade_submission.apply_async([submission.pk], queue='submissions')

        print('queued {} submissions'.format(to_queue))
