import timeit


class Timer:
    def __init__(self, msg=''):
        self.msg = msg
        self.elapsed = 0

    def __enter__(self):
        print('Starting', self.msg)
        self.start_time = timeit.default_timer()

    def __exit__(self, *args, **kwargs):
        self.elapsed = timeit.default_timer() - self.start_time
        print(self.msg, 'Took', self.elapsed, 'seconds')

    @property
    def time(self):
        return self.elapsed


def timer(msg=''):
    num_times_called = 0
    cumulative_time = 0

    def decorator(func):
        def decorated_func(*args, **kwargs):
            nonlocal msg
            if not msg:
                msg = '  - {}'.format(func.__name__)

            with Timer(msg) as t:
                func(*args, **kwargs)

            nonlocal num_times_called
            num_times_called += 1

            nonlocal cumulative_time
            cumulative_time += t.time

            print(msg, f'called {num_times_called} times so far, {cumulative_time}s total')

        return decorated_func

    return decorator


def mocking_hook():
    """
    This is a dummy function that can be used to insert special mock
    behaviors during testing, i.e. forcing a function to sleep during a
    race condition test case.

    This function should be used sparingly to avoid source code clutter.

    Yes, this probably goes against some best practices, but race
    condition test cases are very important, and trying to find a "real"
    line of code to mock has so far proven to be a large time waster due
    to the complexity of the libraries being used.
    """
    pass
