import os
import shutil

from django.test import TestCase
from django.conf import settings


class TemporaryFilesystemTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_media_root = settings.MEDIA_ROOT
        cls.new_media_root = os.path.join(
            settings.BASE_DIR, 'tmp_filesystem')
        os.makedirs(cls.new_media_root)
        settings.MEDIA_ROOT = cls.new_media_root

    @classmethod
    def tearDownClass(cls):
        settings.MEDIA_ROOT = cls.old_media_root
        print(cls.new_media_root)
        shutil.rmtree(cls.new_media_root)
