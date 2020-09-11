from autograder.grading_tasks.tasks.exceptions import StopGrading
import traceback
import time

from django.conf import settings
from django import db
from django.db import transaction


class MaxRetriesExceeded(Exception):
    pass


# This thin wrapper around time.sleep is needed so that we can mock
# the calls to sleep in this module only. As of this writing, patching
# autograder.grading_tasks.tasks.utils.time.sleep also causes uses
# of time.sleep in the subprocess module to be mocked.
def sleep(secs: float):
    return time.sleep(secs)


def retry(max_num_retries,
          retry_delay_start=0,
          retry_delay_end=0,
          retry_delay_step=None,
          immediately_reraise_on=tuple()):
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

    :param immediately_reraise_on: A tuple of exception classes. If any
        of these exceptions are caught, they will be immediately be
        re-raised, halting the retry attempts. The tuple will be passed
        directly as the second argument to isinstance().
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
                except Exception as e:
                    print('Error in', func.__name__)
                    traceback.print_exc()

                    if isinstance(e, immediately_reraise_on):
                        raise

                    # In case the database connection was closed unexpectedly
                    # (this could happen if the database server restarts), we
                    # want to tell Django to discard the connection so that it
                    # will create a new one next time we try to access the database.
                    # Otherwise, we could get stuck in an error loop due to a
                    # "connection already closed" or similar error.
                    #
                    # To test this behavior:
                    #   - Add a call to time.sleep in the middle of some retry-able
                    #     task.
                    #   - While the task is sleeping *restart* the postgres server.
                    #     Note: With docker, use docker restart --time 0 <container>
                    #   - When the task wakes up, it should raise an InterfaceError
                    #     ("connection already closed") or OperationalError ("server
                    #     closed the connection unexpectedly"),
                    #     otherwise try putting the time.sleep somewhere else.
                    if isinstance(e, db.Error):
                        try:
                            for conn in db.connections.all():
                                conn.close_if_unusable_or_obsolete()
                        except Exception:
                            print('Error closing db connections')
                            traceback.print_exc()

                    print('Will try again in', retry_delay, 'seconds')
                    num_retries_remaining -= 1
                    sleep(retry_delay)
                    retry_delay += retry_delay_step
                    latest_exception = traceback.format_exc()

            raise MaxRetriesExceeded(latest_exception)

        return func_with_retry

    return decorator


RERAISE_IMMEDIATELY = (
    db.IntegrityError,
    StopGrading
)


# Specialization of the "retry" decorator to be used for synchronous
# tasks that should always succeed unless there is a database issue.
retry_should_recover = retry(max_num_retries=60,
                             retry_delay_start=1,
                             retry_delay_end=60,
                             immediately_reraise_on=RERAISE_IMMEDIATELY)
# Specialization of "retry" to be used for grading non-deferred
# autograder test cases.
retry_ag_test_cmd = retry(max_num_retries=settings.AG_TEST_MAX_RETRIES,
                          retry_delay_start=settings.AG_TEST_MIN_RETRY_DELAY,
                          retry_delay_end=settings.AG_TEST_MAX_RETRY_DELAY,
                          immediately_reraise_on=RERAISE_IMMEDIATELY)
