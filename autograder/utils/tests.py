import os

from django.conf import settings

from autograder import utils
import autograder.utils.testing as test_ut


class TestFileSystemNavigationUtils(test_ut.UnitTestBase):
    def setUp(self):
        super().setUp()

        os.makedirs(settings.MEDIA_ROOT)
        self.original_dir = os.getcwd()
        os.chdir(settings.MEDIA_ROOT)

    def tearDown(self):
        super().tearDown()

        os.chdir(self.original_dir)

    def test_change_directory(self):
        new_dirname = 'my_dir'
        os.mkdir('my_dir')

        self.assertEqual(os.getcwd(), settings.MEDIA_ROOT)

        with utils.ChangeDirectory(new_dirname):
            self.assertEqual(
                os.path.join(settings.MEDIA_ROOT, new_dirname),
                os.getcwd())

        self.assertEqual(os.getcwd(), settings.MEDIA_ROOT)
