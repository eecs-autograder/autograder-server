import os
import shutil
from contextlib import contextmanager

from django.core.cache import cache
from django.conf import settings
from django.test import TransactionTestCase
from django.test.utils import override_settings


@override_settings(MEDIA_ROOT=os.path.join(settings.PROJECT_ROOT, 'tmp_filesystem'))
class UnitTestBase(TransactionTestCase):
    """
    Base class for test cases that use either the filesystem or the
    cache. Overrides the MEDIA_ROOT setting.

    The setUp() method does the followiPng:
        - Clears the cache
        - Creates a temporary directory for the test to use.
        - Saves the current settings.MEDIA_ROOT,
          then modifies it to refer to the temporary directory.
    The tearDown() method does the following:
        - Restores the original settings.MEDIA_ROOT
        - Deletes the temporary directory created in setUp()

    Since setUp() and tearDown() are called for each test case,
    you won't have to worry about tests interfering with each other.

    This class also includes a method for comparing containers, ignoring
    the order of any items in sub-containers.
    """

    fixtures = ['default_sandbox_image.json']

    def setUp(self):
        super().setUp()

        cache.clear()

        if os.path.isdir(settings.MEDIA_ROOT):
            print('Deleting temp filesystem')
            self.assertTrue(settings.MEDIA_ROOT.endswith('tmp_filesystem'))
            shutil.rmtree(settings.MEDIA_ROOT)

    def tearDown(self):
        try:
            shutil.rmtree(settings.MEDIA_ROOT)
        except Exception:
            pass

    def assert_dict_is_subset(self, subset_dict, superset_dict):
        for key, value in subset_dict.items():
            self.assertEqual(value, superset_dict[key])

    def assert_dict_contents_equal(self, first, second):
        self.assertEqual(_ordered(first), _ordered(second))

    def assert_list_contents_equal(self, first, second):
        self.assertCountEqual(_ordered(first), _ordered(second))

    def assert_queryset_count_unchanged(self, queryset):
        return UnitTestBase._AssertQuerySetCountUnchanged(queryset, self)

    class _AssertQuerySetCountUnchanged:
        def __init__(self, queryset, test_case_object):
            self.original_count = None
            self.queryset = queryset
            self.test_case_object = test_case_object

        def __enter__(self):
            self.original_count = self.queryset.count()

        def __exit__(self, *args):
            self.test_case_object.assertEqual(self.original_count, self.queryset.count())

    def assert_cache_key_invalidated(self, cache_key: str):
        return _assert_cache_key_invalidated(cache_key)


@contextmanager
def _assert_cache_key_invalidated(cache_key: str):
    if cache.get(cache_key) is None:
        raise AssertionError(f'Cache key "{cache_key}" not present before expected invalidation.')

    yield

    if cache.get(cache_key) is not None:
        raise AssertionError(f'Cache key "{cache_key}" unexpectedly present.')


# Adapted from: http://stackoverflow.com/questions/25851183/
def _ordered(obj):
    if isinstance(obj, dict):
        return {key: _ordered(value) for key, value in obj.items()}
    if isinstance(obj, list) or isinstance(obj, tuple):
        try:
            return list(sorted(_ordered(value) for value in obj))
        except TypeError:
            return [_ordered(value) for value in obj]
    else:
        return obj
