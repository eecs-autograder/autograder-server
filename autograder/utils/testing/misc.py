import timeit


class Timer:
    def __init__(self, msg=''):
        self.msg = msg

    def __enter__(self):
        self.start_time = timeit.default_timer()

    def __exit__(self, *args, **kwargs):
        self.elapsed = timeit.default_timer() - self.start_time
        print(self.msg, 'Took', self.elapsed, 'seconds')


def mocking_hook():
    '''
    This is a dummy function that can be used to insert special mock
    behaviors during testing, i.e. Forcing a function to sleep during a
    race condition test case.

    This function should be used sparingly to avoid source code clutter.

    Yes, this probably goes against some best practices, but race
    condition test cases are very important, and trying to find a "real"
    line of code to mock has so far proven to be a large time waster due
    to the complexity of the libraries being used.
    '''
    pass
