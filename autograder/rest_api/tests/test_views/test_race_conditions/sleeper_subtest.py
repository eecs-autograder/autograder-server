import multiprocessing
import time
from unittest import mock

from django import db


class sleeper_subtest:
    '''
    The purpose of this decorator is to abstract away most of the
    subprocess, mocking, and error handling logic used when writing
    tests that target specific race conditions.

    The general pattern for this kind of test case is as follows:
    1. Initialize some data
    2. Define a function with this decorator, passing in parameters
        specifying what path should be mocked, which function in the
        unittest.mock.patch family should be used, and any other
        arguments to that patch function. The function being decorated
        should acquire some lock, then the applied mock will force the
        process to sleep. After the process wakes up, it may perform
        any test checks it needs to--errors will be propagated up to the
        main process.
    3. Call the function defined in the previous step. It is advisable
        to store the return value, which is a wrapper class created by
        the decorator.
    4. Perform any needed test case checks (in the main process).
    5. Call join() on the return value mentioned in step 3.
    '''

    def __init__(self, *mock_args, patch_func=mock.patch, **mock_kwargs):
        self.patch_func = patch_func
        self.mock_args = mock_args
        self.mock_kwargs = mock_kwargs

        self.event = multiprocessing.Event()

    def __call__(self, function):
        return sleeper_subtest._SleeperSubtest(
            function, self.event, self.patch_func,
            self.mock_args, self.mock_kwargs)

    class _SleeperSubtest:
        def __init__(self, function, event, patch_func, mock_args, mock_kwargs):
            self.function = function
            self.event = event
            self.patch_func = patch_func
            self.mock_args = mock_args
            self.mock_kwargs = mock_kwargs

            self.error_queue = multiprocessing.Queue()

        def __call__(self, *func_args, **func_kwargs):
            '''
            Closes the current database connection and starts the
            decorated function in a sub-process, then waits on the event
            that was passed in.
            '''
            if hasattr(self, 'proc'):
                raise AttributeError('The subprocess has already started')

            def sub_func():
                '''
                This function is a wrapper for the subprocess target.
                It applies the mock object, runs the wrapped function,
                and catches and stores any exceptions that are thrown
                from the wrapped function. It also sends a signal to
                the event that the main processes is waiting on.
                '''
                def notify_sleep_and_return(*args, **kwargs):
                    self.event.set()
                    print('subprocess going to sleep')
                    time.sleep(2)
                    return mock.DEFAULT

                try:
                    with self.patch_func(*self.mock_args,
                                         **self.mock_kwargs) as patched:
                        patched.side_effect = notify_sleep_and_return
                        print('calling wrapped function')
                        self.function(*func_args, **func_kwargs)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    self.error_queue.put(e)
                    self.event.set()

            db.connection.close()
            self.proc = multiprocessing.Process(target=sub_func)
            self.proc.start()
            print('waiting for event')
            self.event.wait()
            return self

        def join(self):
            '''
            Waits for the wrapped function subprocess to finish and
            propagates any errors that were raised in the subprocess.
            '''
            print('waiting for wrapped function')
            self.proc.join()
            print('checking for errors')
            while not self.error_queue.empty():
                raise self.error_queue.get()
