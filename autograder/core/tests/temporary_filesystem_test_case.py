import os
import shutil

from django.test import TestCase
from django.conf import settings


class TemporaryFilesystemTestCase(TestCase):
    """
    Base class for test cases that test code that performs
    filesystem operations.

    The setUp() method does the following:
        - Creates a temporary directory for the test to use.
        - Saves the current settings.MEDIA_ROOT,
          then modifies it to refer to the temporary directory.
    The tearDown() method does the following:
        - Restores the original settings.MEDIA_ROOT
        - Deletes the temporary directory created in setUp()

    Since setUp() and tearDown() are called for each test case,
    you won't have to worry about tests interfering with each other.
    """

    def setUp(self):
        # super().setUp()
        self._old_media_root = settings.MEDIA_ROOT
        self.new_media_root = os.path.join(
            settings.BASE_DIR, 'tmp_filesystem')

        if os.path.isdir(self.new_media_root):
            print('Deleting temp filesystem')
            shutil.rmtree(self.new_media_root)

        os.makedirs(self.new_media_root)
        settings.MEDIA_ROOT = self.new_media_root

    def tearDown(self):
        settings.MEDIA_ROOT = self._old_media_root
        shutil.rmtree(self.new_media_root)
