import os

from django.core import exceptions
from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.core import constants
from autograder.core.models.project.uploaded_file import UploadedFile

from autograder import utils
import autograder.core.utils as core_ut
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


_illegal_filenames = [
    '..',
    '',
    '.'
]


class _SetUp(UnitTestBase):
    def setUp(self):
        super().setUp()

        self.project = obj_build.build_project()
        self.file_obj = SimpleUploadedFile(
            'project_file.txt',
            b'contents more contents.')


class CreateUploadedFileTestCase(_SetUp):
    def test_valid_create(self):
        uploaded_file = UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=self.file_obj)

        self.assertEqual(self.file_obj.name, uploaded_file.name)
        expected_abspath = os.path.join(
            core_ut.get_project_files_dir(self.project), self.file_obj.name)
        self.assertEqual(expected_abspath, uploaded_file.abspath)
        self.assertEqual(self.file_obj.size, uploaded_file.size)

        self.file_obj.seek(0)
        self.assertEqual(self.file_obj.read(), uploaded_file.file_obj.read())

        with utils.ChangeDirectory(core_ut.get_project_files_dir(self.project)):
            self.assertTrue(os.path.isfile(self.file_obj.name))

    def test_create_file_exception_file_already_exists(self):
        self.file_obj.seek(0)
        uploaded_file = UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=self.file_obj)

        duplicate_file = SimpleUploadedFile(
            self.file_obj.name, b'some content that should not be here')
        with self.assertRaises(exceptions.ValidationError) as cm:
            UploadedFile.objects.validate_and_create(
                project=self.project, file_obj=duplicate_file)

        self.assertIn('filename', cm.exception.message_dict)
        self.file_obj.seek(0)
        self.assertEqual(uploaded_file.file_obj.read(), self.file_obj.read())

    # Note: Django's uploaded file objects strip path information from
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
        for filename in _illegal_filenames:
            self.file_obj.name = filename
            with self.assertRaises(exceptions.ValidationError,
                                   msg='Filename: ' + filename) as cm:
                UploadedFile.objects.validate_and_create(
                    project=self.project,
                    file_obj=self.file_obj)

            self.assertIn('file_obj', cm.exception.message_dict)

    def test_error_file_too_big(self):
        too_big = SimpleUploadedFile('wee', b'a' * (constants.MAX_PROJECT_FILE_SIZE + 1))
        with self.assertRaises(exceptions.ValidationError) as cm:
            UploadedFile.objects.validate_and_create(project=self.project, file_obj=too_big)

        self.assertIn('content', cm.exception.message_dict)


class RenameUploadedFileTestCase(_SetUp):
    def setUp(self):
        super().setUp()

        self.uploaded_file = UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=self.file_obj)

    def test_valid_rename(self):
        original_last_modified = self.uploaded_file.last_modified
        new_name = 'new_filename'
        self.uploaded_file.rename(new_name)

        self.uploaded_file.refresh_from_db()

        self.assertNotEqual(original_last_modified, self.uploaded_file.last_modified)
        self.assertEqual(new_name, self.uploaded_file.name)
        with utils.ChangeDirectory(core_ut.get_project_files_dir(self.project)):
            self.assertTrue(os.path.isfile(new_name))

    def test_path_info_stripped_from_new_name(self):
        name_with_path = '../../hack/you'
        self.uploaded_file.rename(name_with_path)

        self.uploaded_file.refresh_from_db()

        expected_new_name = 'you'
        self.assertEqual(expected_new_name, self.uploaded_file.name)
        with utils.ChangeDirectory(core_ut.get_project_files_dir(self.project)):
            self.assertTrue(os.path.isfile(expected_new_name))

    def test_error_illegal_filenames(self):
        for filename in _illegal_filenames:
            with self.assertRaises(exceptions.ValidationError,
                                   msg='Filename: ' + filename) as cm:
                self.uploaded_file.rename(filename)

            self.assertIn('name', cm.exception.message_dict)


class DeleteUploadedFileTestCase(_SetUp):
    def test_file_deleted_from_filesystem(self):
        uploaded_file = UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=self.file_obj)
        self.assertTrue(os.path.exists(uploaded_file.abspath))

        uploaded_file.delete()
        self.assertFalse(os.path.exists(uploaded_file.abspath))


class UploadedFileMiscTestCase(_SetUp):
    def test_serializable_fields(self):
        expected = [
            'pk',
            'name',
            'size',
            'project',
            'last_modified',
        ]

        self.assertCountEqual(expected,
                              UploadedFile.get_serializable_fields())

        uploaded_file = UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=self.file_obj)
        self.assertTrue(uploaded_file.to_dict())

    def test_editable_fields(self):
        expected = []
        self.assertCountEqual(expected, UploadedFile.get_editable_fields())
