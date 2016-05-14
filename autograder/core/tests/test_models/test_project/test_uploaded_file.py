import os

from django.core import exceptions
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from autograder.core.models.project.uploaded_file import UploadedFile

import autograder.core.shared.utilities as ut

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut


class _SetUp:
    def setUp(self):
        super().setUp()

        self.project = obj_ut.build_project()
        self.file_obj = SimpleUploadedFile(
            'project_file.txt', b'contents more contents.')


class RenameUploadedFileTestCase(_SetUp, TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.uploaded_file = UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=self.file_obj)

    def test_valid_rename(self):
        new_name = 'new_filename'
        self.uploaded_file.rename(new_name)

        self.uploaded_file.refresh_from_db()

        self.assertEqual(new_name, self.uploaded_file.name)
        with ut.ChangeDirectory(ut.get_project_files_dir(self.project)):
            self.assertTrue(os.path.isfile(new_name))

    def test_path_info_stripped_from_new_name(self):
        name_with_path = '../../hack/you'
        self.uploaded_file.rename(name_with_path)

        self.uploaded_file.refresh_from_db()

        expected_new_name = 'you'
        self.assertEqual(expected_new_name, self.uploaded_file.name)
        with ut.ChangeDirectory(ut.get_project_files_dir(self.project)):
            self.assertTrue(os.path.isfile(expected_new_name))


class CreateUploadedFileTestCase(_SetUp, TemporaryFilesystemTestCase):
    def test_default_to_dict_fields(self):
        expected = [
            'name',
            'size',
            'project'
        ]

        self.assertCountEqual(expected,
                              UploadedFile.get_default_to_dict_fields())

        uploaded_file = UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=self.file_obj)
        self.assertTrue(uploaded_file.to_dict())

    def test_editable_fields(self):
        expected = []

        self.assertCountEqual(expected, UploadedFile.get_editable_fields())

    def test_valid_create(self):
        uploaded_file = UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=self.file_obj)

        self.assertEqual(self.file_obj.name, uploaded_file.name)
        expected_abspath = os.path.join(
            ut.get_project_files_dir(self.project), self.file_obj.name)
        self.assertEqual(expected_abspath, uploaded_file.abspath)
        self.assertEqual(self.file_obj.size, uploaded_file.size)

        self.file_obj.seek(0)
        self.assertEqual(self.file_obj.read(), uploaded_file.file_obj.read())

        with ut.ChangeDirectory(ut.get_project_files_dir(self.project)):
            self.assertTrue(os.path.isfile(self.file_obj.name))

    # If we decide we don't want the Django default behavior of renaming
    # duplicate filenames, implement this test.
    # def test_exception_file_exists(self):
    #     self.fail()

    # NOTE: Django's uploaded file objects strip path information from
    # uploaded files
    def test_path_info_stripped_from_uploaded_filenames(self):
        # This test makes sure that these objects don't allow
        # the user to add files in subdirectories (or worse,
        # somewhere else in the filesystem).
        new_filename = 'new_filename.txt'
        self.file_obj.name = '../../' + new_filename

        uploaded_file = UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=self.file_obj)

        self.assertEqual(new_filename, uploaded_file.name)

    def test_exception_illegal_filenames(self):
        illegal_filenames = [
            '..',
            '; echo "haxorz";#',
            '.spam.txt',
            '',
            '     '
        ]

        for filename in illegal_filenames:
            self.file_obj.name = filename
            with self.assertRaises(exceptions.ValidationError,
                                   msg='Filename: ' + filename) as cm:
                UploadedFile.objects.validate_and_create(
                    project=self.project,
                    file_obj=self.file_obj)

            self.assertIn('file_obj', cm.exception.message_dict)
