import uuid

from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import status

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_generic_data as test_data


class _UploadedFilesSetUp(test_data.Client, test_data.Project):
    pass


class ListUploadedFilesTestCase(_UploadedFilesSetUp,
                                UnitTestBase):
    def test_admin_list_files(self):
        for project in self.all_projects:
            self.do_list_uploaded_files_test(self.admin, project)

    def test_staff_list_files(self):
        for project in self.all_projects:
            self.do_list_uploaded_files_test(self.staff, project)

    def test_enrolled_list_patterns(self):
        for project in self.all_projects:
            self.do_permission_denied_test(self.enrolled, project)

    def test_other_list_patterns(self):
        for project in self.all_projects:
            self.do_permission_denied_test(self.nobody, project)

    def do_list_uploaded_files_test(self, user, project):
        serialized_files = self.build_uploaded_files(project)
        self.client.force_authenticate(user)
        response = self.client.get(self.get_uploaded_files_url(project))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertCountEqual(serialized_files, response.data)

    def do_permission_denied_test(self, user, project):
        self.build_uploaded_files(project)
        self.client.force_authenticate(user)
        response = self.client.get(self.get_uploaded_files_url(project))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def build_uploaded_files(self, project):
        num_files = 3
        if not project.uploaded_files.count():
            for i in range(num_files):
                name = 'file' + str(i)
                file_ = SimpleUploadedFile(name, b'file with stuff')
                ag_models.UploadedFile.objects.validate_and_create(
                    project=project, file_obj=file_)

        serialized_files = ag_serializers.UploadedFileSerializer(
            project.uploaded_files.all(), many=True).data
        self.assertEqual(num_files, len(serialized_files))
        return serialized_files


class CreateUploadedFileTestCase(_UploadedFilesSetUp,
                                 UnitTestBase):
    def setUp(self):
        super().setUp()
        self.file_obj = SimpleUploadedFile('file' + str(uuid.uuid4().hex),
                                           b'waaaaluigi')

    def test_admin_create_uploaded_file(self):
        self.assertEqual(0, self.project.uploaded_files.count())
        args = {'file_obj': self.file_obj}
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.get_uploaded_files_url(self.project), args,
            format='multipart')
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, self.project.uploaded_files.count())
        loaded = self.project.uploaded_files.first()
        self.assertEqual(loaded.to_dict(), response.data)

        self.file_obj.seek(0)
        self.assertEqual(self.file_obj.name, loaded.name)
        self.assertEqual(self.file_obj.read(), loaded.file_obj.read())

    def test_admin_create_uploaded_file_invalid_settings(self):
        bad_file = SimpleUploadedFile('..', b'waaaario')
        self.assertEqual(0, self.project.uploaded_files.count())
        args = {'file_obj': bad_file}
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.get_uploaded_files_url(self.project), args,
            format='multipart')
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(0, self.project.uploaded_files.count())

    def test_non_admin_create_uploaded_file_permission_denied(self):
        for user in self.staff, self.enrolled, self.nobody:
            self.assertEqual(0, self.project.uploaded_files.count())
            args = {'file_obj': self.file_obj}
            self.client.force_authenticate(user)
            response = self.client.post(
                self.get_uploaded_files_url(self.project), args,
                format='multipart')
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
            self.assertEqual(0, self.project.uploaded_files.count())
