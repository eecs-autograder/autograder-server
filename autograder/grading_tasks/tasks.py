import time
import traceback

from django.conf import settings
from django.db import transaction

import celery

import autograder.core.models as ag_models


class MaxRetriesExceeded(Exception):
    pass


def retry(max_num_retries,
          retry_delay_start=0,
          retry_delay_end=0,
          retry_delay_step=None):
    '''
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
        delay for each consecutive retry. If not specified, defaults to
        (retry_delay_end - retry_delay_start) / max_num_retries
    '''
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
                except Exception as e:
                    print('Error in', func.__name__)
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
retry_ag_test = retry(max_num_retries=settings.AG_TEST_MAX_RETRIES,
                      retry_delay_start=settings.AG_TEST_MIN_RETRY_DELAY,
                      retry_delay_end=settings.AG_TEST_MAX_RETRY_DELAY)


@celery.shared_task(queue='submissions')
def grade_submission(submission_pk):
    try:
        submission = _mark_submission_as_being_graded(submission_pk)
        if submission is None:
            return

        project = submission.submission_group.project
        for ag_test in project.autograder_test_cases.filter(deferred=False):
            grade_non_deferred_ag_test(ag_test.pk, submission_pk)

        @retry_should_recover
        def mark_as_waiting_for_deferred():
            submission.status = (
                ag_models.Submission.GradingStatus.waiting_for_deferred)

        mark_as_waiting_for_deferred()

        deferred_queryset = project.autograder_test_cases.filter(deferred=True)
        signatures = [grade_deferred_ag_test.s(ag_test.pk, submission_pk)
                      for ag_test in deferred_queryset]
        if not signatures:
            _mark_submission_as_finished_impl(submission_pk)
            return

        celery.chord(signatures)(mark_submission_as_finished.s(submission_pk))
    except Exception:
        print('Error grading submission')
        traceback.print_exc()
        _mark_submission_as_error(submission_pk, traceback.format_exc())
        raise


def grade_non_deferred_ag_test(ag_test_pk, submission_pk):
    @retry_ag_test
    def _grade_non_deferred__ag_test_impl():
        grade_ag_test_impl(ag_test_pk, submission_pk)

    _grade_non_deferred__ag_test_impl()


@celery.shared_task(bind=True, max_retries=1, queue='deferred')
def grade_deferred_ag_test(self, ag_test_pk, submission_pk):
    @retry_should_recover
    def _grade_deferred_ag_test_impl():
        grade_ag_test_impl(ag_test_pk, submission_pk)

    try:
        _grade_deferred_ag_test_impl()
    except Exception:
        print('Error grading deferred test')
        traceback.print_exc()
        _mark_submission_as_error(submission_pk, traceback.format_exc())


def grade_ag_test_impl(ag_test_pk, submission_pk):
    @retry_should_recover
    def load_data():
        result = ag_models.AutograderTestCaseResult.objects.get(
            test_case__pk=ag_test_pk,
            submission__pk=submission_pk)
        return result, result.test_case, result.submission

    @retry_should_recover
    def save_result(result):
        result.save()

    # Leave this here
    grade_ag_test_impl.mocking_hook()

    # If this fails, something is seriously wrong.
    result, ag_test, submission = load_data()
    _update_ag_test_result_status(
        result, ag_models.AutograderTestCaseResult.ResultStatus.grading)
    try:
        result = _run_ag_test(ag_test, submission)
        save_result(result)
        _update_ag_test_result_status(
            result, ag_models.AutograderTestCaseResult.ResultStatus.finished)
    except Exception:
        _mark_ag_test_result_as_error(result, traceback.format_exc())
grade_ag_test_impl.mocking_hook = lambda: None  # type: ignore


def _run_ag_test(ag_test, submission):
    from autograder_sandbox import AutograderSandbox

    group = submission.submission_group

    sandbox = AutograderSandbox(
        name='submission{}-test{}'.format(submission.pk, ag_test.pk),
        environment_variables={
            'usernames': ' '.join(sorted(group.member_names))},
        allow_network_access=ag_test.allow_network_connections)

    with sandbox:
        return ag_test.run(submission, sandbox)


@retry_should_recover
def _mark_submission_as_being_graded(submission_id):
    with transaction.atomic():
        submission = ag_models.Submission.objects.select_for_update().get(
            pk=submission_id)
        if (submission.status ==
                ag_models.Submission.GradingStatus.removed_from_queue):
            print('submission {} has been removed '
                  'from the queue'.format(submission.pk))
            return None

        submission.status = ag_models.Submission.GradingStatus.being_graded
        submission.save()
        return submission


@celery.shared_task(queue='deferred')
def mark_submission_as_finished(chord_results, submission_pk):
    _mark_submission_as_finished_impl(submission_pk)


@retry_should_recover
def _mark_submission_as_finished_impl(submission_pk):
    ag_models.Submission.objects.filter(
        pk=submission_pk
    ).update(status=ag_models.Submission.GradingStatus.finished_grading)


@retry_should_recover
def _mark_submission_as_error(submission_pk, error_msg):
    with transaction.atomic():
        submission = ag_models.Submission.objects.select_for_update().get(
            pk=submission_pk)
        submission.status = ag_models.Submission.GradingStatus.error
        submission.error_msg += ('\n' + '=' * 80 + '\n' + error_msg)
        submission.save()


@retry_should_recover
def _update_ag_test_result_status(result, new_status):
    result.status = new_status
    result.save()


@retry_should_recover
def _mark_ag_test_result_as_error(result, error_msg):
    result.status = ag_models.AutograderTestCaseResult.ResultStatus.error
    result.error_msg = error_msg
    result.save()


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
