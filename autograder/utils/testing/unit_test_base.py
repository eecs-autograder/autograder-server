import os
import shutil

from django.core.cache import cache
from django.conf import settings
from django.test import TransactionTestCase
from django.test.utils import override_settings


@override_settings(MEDIA_ROOT=os.path.join(settings.BASE_DIR, 'tmp_filesystem'))
class UnitTestBase(TransactionTestCase):
    """
    Base class for test cases that test code that performs
    filesystem operations. Overrides the MEDIA_ROOT setting

    The setUp() method does the following:
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

    def setUp(self):
        super().setUp()

        # HACK
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

    def assertDictContentsEqual(self, first, second):
        self.assertEqual(_ordered(first), _ordered(second))

    def assertListContentsEqual(self, first, second):
        self.assertCountEqual(_ordered(first), _ordered(second))


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
