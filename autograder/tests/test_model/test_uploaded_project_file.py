import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from autograder.models import Project, Course, UploadedProjectFile
from autograder.tests.temporary_filesystem_test_case import TemporaryFilesystemTestCase

from autograder.shared import utilities as ut


class UploadedProjectFileTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.course = Course.objects.create(name='eecs280')
        self.project = Project.objects.create(name='p1', course=self.course)

        self.txt_filename = 'spam.txt'
        self.txt_file_content = b"spam eggs sausage spam"
        self.uploaded_txt_file = SimpleUploadedFile(
            self.txt_filename, self.txt_file_content)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------

    def test_valid_file_upload(self):
        project_file = UploadedProjectFile.objects.create(
            project=self.project, uploaded_file=self.uploaded_txt_file)

        expected_fs_path = os.path.join(
            ut.get_project_files_dir(self.project), self.txt_filename)

        self.assertTrue(os.path.isfile(expected_fs_path))

        loaded_project_file = UploadedProjectFile.get_project_file(
            self.txt_filename, self.project)

        self.assertEqual(project_file, loaded_project_file)
        self.assertEqual(
            expected_fs_path, loaded_project_file.uploaded_file.name)
        self.assertEqual(
            self.txt_file_content, loaded_project_file.uploaded_file.read())

    # -------------------------------------------------------------------------

    def test_exception_on_file_already_exists(self):
        UploadedProjectFile.objects.create(
            project=self.project, uploaded_file=self.uploaded_txt_file)
        with self.assertRaises(ValidationError):
            UploadedProjectFile.objects.create(
                project=self.project, uploaded_file=self.uploaded_txt_file)

    # -------------------------------------------------------------------------

    def test_valid_same_filename_different_projects(self):
        UploadedProjectFile.objects.create(
            project=self.project, uploaded_file=self.uploaded_txt_file)
        new_project = Project.objects.create(
            course=self.course, name="eecs381")

        new_file = UploadedProjectFile.objects.create(
            project=new_project, uploaded_file=self.uploaded_txt_file)
        loaded_new_file = UploadedProjectFile.get_project_file(
            self.txt_filename, new_project)

        self.assertEqual(new_file, loaded_new_file)

    # -------------------------------------------------------------------------

    # TODO: custom FileStorageSystem that allows overwriting files instead of
    #       the default renaming behavior
    # def test_overwrite_file(self):
    #     old_file = UploadedProjectFile.objects.create(
    #         project=self.project, uploaded_file=self.uploaded_txt_file)
    #     loaded_old_file = UploadedProjectFile.get_project_file(
    #         self.txt_filename, self.project)
    #     self.assertEqual(old_file, loaded_old_file)

    #     new_file_content = b"egg, bacon, spam, and sausage"
    #     new_uploaded_file = SimpleUploadedFile(
    #         self.txt_filename, new_file_content)
    #     new_file = UploadedProjectFile.objects.create(
    #         project=self.project, uploaded_file=new_uploaded_file,
    #         overwrite_on_save=True)

    #     loaded_new_file = UploadedProjectFile.get_project_file(
    #         self.txt_filename, self.project)

    #     self.assertEqual(new_file, loaded_new_file)
    #     self.assertEqual(
    #         new_file_content, loaded_new_file.uploaded_file.read())
