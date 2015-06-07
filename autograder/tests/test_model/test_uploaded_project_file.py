import os
import shutil

from django.test import TestCase
from django.conf import settings

from autograder.models import Project, Course

from autograder.shared import utilities as ut


class UploadedProjectFileTestCase(TestCase):
    def setUp(self):
        self.old_media_root = settings.MEDIA_ROOT
        self.new_media_root = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "tmp_filesystem")
        os.mkdir(self.new_media_root)

        settings.MEDIA_ROOT = os.path.abspath(self.new_media_root)
        print(settings.MEDIA_ROOT)

        self.course = Course.objects.create(name='eecs280')
        self.project = Project.objects.create(name='p1', course=self.course)

        os.makedirs(ut.get_project_files_dir(self.project))

    # -------------------------------------------------------------------------

    def tearDown(self):
        settings.MEDIA_ROOT = self.old_media_root

        print(self.new_media_root)
        # os.move()

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def test_blech(self):
        pass
