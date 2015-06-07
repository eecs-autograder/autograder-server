import os
import shutil

from django.test import TestCase
from django.conf import settings


class TemporaryFilesystemTestCase(TestCase):
    def setUp(self):
        self.old_media_root = settings.MEDIA_ROOT
        self.new_media_root = os.path.join(
            settings.BASE_DIR, 'tmp_filesystem')
        os.makedirs(self.new_media_root)#, ok_exist=True)
        settings.MEDIA_ROOT = self.new_media_root

    def tearDown(self):
        settings.MEDIA_ROOT = self.old_media_root
        print("Deleting: " + self.new_media_root)
        shutil.rmtree(self.new_media_root)
