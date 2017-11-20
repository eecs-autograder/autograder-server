from unittest import mock

from autograder.utils.testing import UnitTestBase

from autograder.grading_tasks import tasks


class RetryDecoratorTestCase(UnitTestBase):
    def test_retry_and_succeed(self):
        arg_val = 42
        kwarg_val = "cheese"
        return_val = "winzorz!"

        should_throw = True

        @tasks.retry(max_num_retries=1, retry_delay_start=0, retry_delay_end=0)
        def func_to_retry(test_case, arg, kwarg=None):
            test_case.assertEqual(arg_val, arg)
            test_case.assertEqual(kwarg_val, kwarg)

            nonlocal should_throw
            if should_throw:
                should_throw = False
                raise Exception('Throooooow')

            return return_val

        self.assertEqual(return_val, func_to_retry(self, arg_val, kwarg_val))

    def test_max_retries_exceeded(self):
        @tasks.retry(max_num_retries=10, retry_delay_start=0, retry_delay_end=0)
        def func_to_retry():
            raise Exception('Errrrror')

        with self.assertRaises(tasks.MaxRetriesExceeded):
            func_to_retry()

    @mock.patch('autograder.grading_tasks.tasks.utils.time.sleep')
    def test_retry_delay(self, mocked_sleep):
        max_num_retries = 3
        min_delay = 2
        max_delay = 6
        delay_step = 2

        @tasks.retry(max_num_retries=max_num_retries,
                     retry_delay_start=min_delay, retry_delay_end=max_delay,
                     retry_delay_step=delay_step)
        def func_to_retry():
            raise Exception

        with self.assertRaises(tasks.MaxRetriesExceeded):
            func_to_retry()

        mocked_sleep.assert_has_calls(
            [mock.call(delay) for delay in range(min_delay, max_delay, delay_step)])

    @mock.patch('autograder.grading_tasks.tasks.utils.time.sleep')
    def test_retry_zero_delay(self, mocked_sleep):
        max_num_retries = 1

        @tasks.retry(max_num_retries=max_num_retries,
                     retry_delay_start=0, retry_delay_end=0)
        def func_to_retry():
            raise Exception

        with self.assertRaises(tasks.MaxRetriesExceeded):
            func_to_retry()

        mocked_sleep.assert_has_calls([mock.call(0) for i in range(max_num_retries)])

