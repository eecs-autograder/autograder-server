from django.core import exceptions

from autograder.core.models.project.required_student_file import (
    RequiredStudentFile)

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.core.tests.dummy_object_utils as obj_ut


class CreateRequiredStudentFileTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.project = obj_ut.build_project()
        self.valid_filename = 'project_file42.txt'

    def test_valid_create(self):
        required_file = RequiredStudentFile.objects.validate_and_create(
            project=self.project,
            filename=self.valid_filename)

        required_file.refresh_from_db()

        self.assertEqual(self.valid_filename, required_file.filename)

    def test_exception_filename_exists(self):
        RequiredStudentFile.objects.validate_and_create(
            project=self.project,
            filename=self.valid_filename)

        with self.assertRaises(exceptions.ValidationError):
            RequiredStudentFile.objects.validate_and_create(
                project=self.project,
                filename=self.valid_filename)

    def test_no_exception_same_filename_as_other_project(self):
        RequiredStudentFile.objects.validate_and_create(
            project=self.project,
            filename=self.valid_filename)

        other_project = obj_ut.build_project()
        RequiredStudentFile.objects.validate_and_create(
            project=other_project,
            filename=self.valid_filename)

    def test_exception_illegal_filenames(self):
        illegal_names = [
            'student_file;echo "haxhorz";#.cpp',
            '../../../hack/you.cpp',
            '',
            '     '
        ]

        for filename in illegal_names:
            with self.assertRaises(exceptions.ValidationError,
                                   msg='Filename: ' + filename) as cm:
                RequiredStudentFile.objects.validate_and_create(
                    project=self.project,
                    filename=filename)

            self.assertIn('filename', cm.exception.message_dict)
