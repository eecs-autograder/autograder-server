import logging
import os
import shutil
import unittest
from contextlib import contextmanager
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models.query import QuerySet
from django.db.models.signals import post_save
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings

import autograder.core.models as ag_models
from autograder.rest_api.signals import on_project_created


class _CustomAssertsMixin:
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

    @property
    def mock_register_project_queues(self):
        return _mock_register_project_queues


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


class _SetUpTearDownCommon:
    """
    Provides common setup behavior needed for tests that use the
    filesystem, cache and/or the database.
    - Clears the cache and creates a fresh filesystem directory
      before each test.
    - Disconnects on_project_created from Project's post_save signal
      (details in inline comments).

    IMPORTANT: Classes inheriting from this mixin should override the
    MEDIA_ROOT setting, such as with this decorator:
        @override_settings(MEDIA_ROOT=os.path.join(settings.PROJECT_ROOT, 'tmp_filesystem'))

    NOTE: Avoid using setUpTestData until we implement some sort of filesystem
    rollback behavior.
    """
    def setUp(self):
        super().setUp()

        cache.clear()

        if os.path.isdir(settings.MEDIA_ROOT):
            print('Deleting temp filesystem')
            self.assertTrue(settings.MEDIA_ROOT.endswith('tmp_filesystem'))
            shutil.rmtree(settings.MEDIA_ROOT)

        # The function autograder.rest_api.signals.on_project_created
        # causes a celery function to be called that causes the tests to stall.
        # (The celery function is app.control.inspect().active())
        # Our current solution is disconnect that function from the post_save
        # signal. We can re-connect in tests where it's needed.
        post_save.disconnect(on_project_created, sender=ag_models.Project)

    def tearDown(self):
        super().tearDown()

        try:
            shutil.rmtree(settings.MEDIA_ROOT)
        except Exception:
            pass


@override_settings(MEDIA_ROOT=os.path.join(settings.PROJECT_ROOT, 'tmp_filesystem'))
class UnitTestBase(_CustomAssertsMixin, _SetUpTearDownCommon, TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        logging.disable(logging.NOTSET)

    def setUp(self):
        super().setUp()

        # Here we wrap django's Atomic class and QuerySet's
        # select_for_update() method. The wrapper around Atomic keeps
        # track of whether we are in a transaction started by our code
        # (as opposed to, say, django wrapping tests in a transaction).
        #
        # The QuerySet.select_for_update() wrapper asserts that we are
        # in a transaction when it's called.
        #
        # This lets us verify that our code never uses select_for_update()
        # outside of a transaction while still letting us use django's
        # TestCase base class, which provides significantly faster
        # database setup.
        #
        # Note that this mocking may not be applied early enough to
        # affect transaction.atomic calls used as a decorator. In those
        # cases, switch to a context manager instead.

        atomic_block_counter = 0

        original_atomic_enter = transaction.Atomic.__enter__
        original_atomic_exit = transaction.Atomic.__exit__

        def mock_enter(*args):
            nonlocal atomic_block_counter
            atomic_block_counter += 1
            original_atomic_enter(*args)

        def mock_exit(*args):
            nonlocal atomic_block_counter
            atomic_block_counter -= 1
            original_atomic_exit(*args)

        original_select_for_update = QuerySet.select_for_update

        def disable_select_for_update(*args, **kwargs):
            self.assertGreater(
                atomic_block_counter, 0,
                msg='select_for_update() can only be used inside a transaction')

            return original_select_for_update(*args, **kwargs)

        patch_atomic_enter = mock.patch(
            'django.db.transaction.Atomic.__enter__', new=mock_enter)
        patch_atomic_enter.start()
        self.addCleanup(patch_atomic_enter.stop)

        patch_atomic_exit = mock.patch(
            'django.db.transaction.Atomic.__exit__', new=mock_exit)
        patch_atomic_exit.start()
        self.addCleanup(patch_atomic_exit.stop)

        patch_select_for_update = mock.patch(
            'django.db.models.query.QuerySet.select_for_update', new=disable_select_for_update)
        patch_select_for_update.start()
        self.addCleanup(patch_select_for_update.stop)


@override_settings(MEDIA_ROOT=os.path.join(settings.PROJECT_ROOT, 'tmp_filesystem'))
class TransactionUnitTestBase(_CustomAssertsMixin, _SetUpTearDownCommon, TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.flush_sandbox_docker_images()

    def setUp(self):
        super().setUp()
        self.create_default_sandbox_image()

    @classmethod
    def flush_sandbox_docker_images(cls):
        ag_models.SandboxDockerImage.objects.exclude(name='default').delete()

    @classmethod
    def create_default_sandbox_image(cls):
        ag_models.SandboxDockerImage.objects.get_or_create(
            defaults={
                "display_name": "Default",
                "tag": "jameslp/autograder-sandbox:3.1.2"
            },
            name='default'
        )
