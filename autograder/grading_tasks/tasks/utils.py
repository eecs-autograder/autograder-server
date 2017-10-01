import traceback

import time
from django.conf import settings
from django.db import transaction

import autograder.core.models as ag_models


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


@retry_should_recover
def mark_submission_as_error(submission_pk, error_msg):
    with transaction.atomic():
        submission = ag_models.Submission.objects.select_for_update().filter(
            pk=submission_pk).update(status=ag_models.Submission.GradingStatus.error,
                                     error_msg=error_msg)
