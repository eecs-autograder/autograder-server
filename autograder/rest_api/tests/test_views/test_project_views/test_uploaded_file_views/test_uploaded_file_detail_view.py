import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from rest_framework import status
import autograder.core.models as ag_models
from autograder.core import constants

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


def file_url(uploaded_file):
    return reverse('uploaded-file-detail', kwargs={'pk': uploaded_file.pk})


class _BuildFile:
    def setUp(self):
        super().setUp()
        self.file_obj_kwargs = {'name': 'file' + str(uuid.uuid4().hex),
                                'content': b'waaaluigi'}

    def build_file(self, project):
        return ag_models.UploadedFile.objects.validate_and_create(
            file_obj=SimpleUploadedFile(**self.file_obj_kwargs),
            project=project)


class RetrieveUploadedFileTestCase(_BuildFile,
                                   test_data.Client,
                                   test_data.Project,
                                   test_impls.GetObjectTest,
                                   UnitTestBase):
    def test_admin_get_uploaded_file(self):
        for project in self.all_projects:
            file_ = self.build_file(project)
            self.do_get_object_test(
                self.client, self.admin, file_url(file_), file_.to_dict())

    def test_staff_get_uploaded_file(self):
        for project in self.all_projects:
            file_ = self.build_file(project)
            self.do_get_object_test(
                self.client, self.staff, file_url(file_), file_.to_dict())

    def test_enrolled_get_uploaded_file(self):
        for project in self.all_projects:
            file_ = self.build_file(project)
            self.do_permission_denied_get_test(
                self.client, self.enrolled, file_url(file_))

    def test_other_get_uploaded_file(self):
        for project in self.all_projects:
            file_ = self.build_file(project)
            self.do_permission_denied_get_test(
                self.client, self.nobody, file_url(file_))


def file_name_url(uploaded_file):
    return reverse('uploaded-file-name',
                   kwargs={'pk': uploaded_file.pk})


class RenameUploadedFileTestCase(_BuildFile,
                                 test_data.Client,
                                 test_data.Project,
                                 test_impls.UpdateObjectTest,
                                 UnitTestBase):
    def test_admin_rename_uploaded_file(self):
        new_name = self.file_obj_kwargs['name'] + str(uuid.uuid4().hex)
        request_data = {'name': new_name}
        self.client.force_authenticate(self.admin)
        for project in self.all_projects:
            file_ = self.build_file(project)
            self.do_put_object_test(
                file_, self.client, self.admin, file_name_url(file_),
                request_data)

            file_.refresh_from_db()
            self.assertEqual(new_name, file_.name)

    def test_admin_rename_uploaded_file_invalid_name(self):
        illegal_name = '..'
        file_ = self.build_file(self.project)
        self.do_put_object_invalid_args_test(
            file_, self.client, self.admin, file_name_url(file_),
            {'name': illegal_name})

    def test_other_rename_uploaded_file(self):
        file_ = self.build_file(self.visible_public_project)
        for user in self.staff, self.enrolled, self.nobody:
            self.do_put_object_permission_denied_test(
                file_, self.client, user, file_name_url(file_),
                {'name': 'steve'})


def file_content_url(uploaded_file):
    return reverse('uploaded-file-content',
                   kwargs={'pk': uploaded_file.pk})


class RetrieveUploadedFileContentTestCase(_BuildFile,
                                          test_data.Client,
                                          test_data.Project,
                                          test_impls.GetObjectTest,
                                          UnitTestBase):
    def test_admin_get_content(self):
        for project in self.all_projects:
            file_ = self.build_file(project)
            self.do_get_content_test(
                self.client, self.admin, file_content_url(file_),
                self.file_obj_kwargs['content'])

    def test_staff_get_content(self):
        for project in self.all_projects:
            file_ = self.build_file(project)
            self.do_get_content_test(
                self.client, self.staff, file_content_url(file_),
                self.file_obj_kwargs['content'])

    def test_enrolled_or_other_get_content(self):
        file_ = self.build_file(self.visible_public_project)
        for user in self.enrolled, self.nobody:
            self.do_permission_denied_get_test(
                self.client, user, file_content_url(file_))

    def do_get_content_test(self, client, user, url, expected_content):
        client.force_authenticate(user)
        response = client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(
            expected_content,
            b''.join((chunk for chunk in response.streaming_content)))


class UpdateUploadedFileContentTestCase(_BuildFile,
                                        test_data.Client,
                                        test_data.Project,
                                        test_impls.UpdateObjectTest,
                                        UnitTestBase):
    def setUp(self):
        super().setUp()
        self.new_content = self.file_obj_kwargs['content'] + b'stevestavestove'

    @property
    def updated_file(self):
        return SimpleUploadedFile(
            self.file_obj_kwargs['name'], self.new_content)

    def test_admin_update_content(self):
        self.client.force_authenticate(self.admin)
        for project in self.all_projects:
            file_ = self.build_file(project)
            original_last_modified = file_.last_modified
            response = self.client.put(file_content_url(file_),
                                       {'file_obj': self.updated_file},
                                       format='multipart')
            self.assertEqual(status.HTTP_200_OK, response.status_code)
            file_.refresh_from_db()
            self.assertNotEqual(original_last_modified, file_.last_modified)
            self.assertEqual(self.new_content, file_.file_obj.read())
            self.assertEqual(file_.to_dict(), response.data)

    def test_other_update_content_permission_denied(self):
        file_ = self.build_file(self.visible_public_project)
        for user in self.staff, self.enrolled, self.nobody:
            self.do_put_object_permission_denied_test(
                file_, self.client, user, file_content_url(file_),
                {'file_obj': self.updated_file}, format='multipart')
            file_.refresh_from_db()
            self.assertEqual(self.file_obj_kwargs['content'],
                             file_.file_obj.read())

    def test_error_update_content_too_large(self):
        self.client.force_authenticate(self.admin)
        file_ = self.build_file(self.project)
        too_big_updated_file = SimpleUploadedFile(
            self.file_obj_kwargs['name'], b'a' * (constants.MAX_PROJECT_FILE_SIZE + 1))
        response = self.client.put(file_content_url(file_),
                                   {'file_obj': too_big_updated_file},
                                   format='multipart')
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        file_.refresh_from_db()
        with file_.open('rb') as f:
            self.assertEqual(self.file_obj_kwargs['content'], f.read())


class DeleteUploadedFileTestCase(_BuildFile,
                                 test_data.Client,
                                 test_data.Project,
                                 test_impls.DestroyObjectTest,
                                 UnitTestBase):
    def test_admin_delete_file(self):
        self.client.force_authenticate(self.admin)
        for project in self.all_projects:
            file_ = self.build_file(project)

            self.do_delete_object_test(
                file_, self.client, self.admin, file_url(file_))
            with self.assertRaises(FileNotFoundError):
                file_.file_obj.read()

    def test_other_delete_file_permission_denied(self):
        file_ = self.build_file(self.visible_public_project)
        for user in self.staff, self.enrolled, self.nobody:
            self.do_delete_object_permission_denied_test(
                file_, self.client, user, file_url(file_))

            file_.file_obj.read()
