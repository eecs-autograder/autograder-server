import os
# import shutil

# from django.test import TestCase
# from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.models import Project, Course, UploadedProjectFile
from autograder.tests.temporary_filesystem_test_case import TemporaryFilesystemTestCase

from autograder.shared import utilities as ut


class UploadedProjectFileTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        self.course = Course.objects.create(name='eecs280')
        self.project = Project.objects.create(name='p1', course=self.course)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def test_valid_file_upload(self):
        filename = 'spam.txt'
        file_content = b"spame eggs sausage spam"
        uploaded_file = SimpleUploadedFile(filename, file_content)

        project_file = UploadedProjectFile.objects.create(
            project=self.project, uploaded_file=uploaded_file)

        expected_fs_path = os.path.join(
            ut.get_project_files_dir(self.project), filename)

        self.assertTrue(os.path.isfile(expected_fs_path))

        loaded_project_file = UploadedProjectFile.get_project_file(
            filename, self.project)

        self.assertEqual(project_file, loaded_project_file)
        self.assertEqual(
            expected_fs_path, loaded_project_file.uploaded_file.name)

    # -------------------------------------------------------------------------

    def test_file_already_exists(self):
        pass

    # -------------------------------------------------------------------------

    def test_overwrite_file(self):
        pass
