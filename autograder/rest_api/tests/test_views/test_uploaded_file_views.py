from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse

from rest_framework import status
import autograder.core.models as ag_models

from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


_file_obj_kwargs = {'name': 'spam', 'content': b'waaaluigi'}


def build_file(project):
    return ag_models.UploadedFile.objects.validate_and_create(
        file_obj=SimpleUploadedFile(**_file_obj_kwargs),
        project=project)


def file_url(uploaded_file):
    return reverse('uploaded-file-detail', kwargs={'pk': uploaded_file.pk})


class RetrieveUploadedFileTestCase(test_data.Client,
                                   test_data.Project,
                                   test_impls.GetObjectTest,
                                   TemporaryFilesystemTestCase):
    def test_admin_get_uploaded_file(self):
        for project in self.all_projects:
            file_ = build_file(project)
            self.do_get_object_test(
                self.client, self.admin, file_url(file_), file_.to_dict())

    def test_staff_get_uploaded_file(self):
        for project in self.all_projects:
            file_ = build_file(project)
            self.do_get_object_test(
                self.client, self.staff, file_url(file_), file_.to_dict())

    def test_enrolled_get_uploaded_file(self):
        for project in self.all_projects:
            file_ = build_file(project)
            self.do_permission_denied_get_test(
                self.client, self.enrolled, file_url(file_))

    def test_other_get_uploaded_file(self):
        for project in self.all_projects:
            file_ = build_file(project)
            self.do_permission_denied_get_test(
                self.client, self.nobody, file_url(file_))


def file_name_url(uploaded_file):
    return reverse('uploaded-file-name',
                   kwargs={'pk': uploaded_file.pk})


class RenameUploadedFileTestCase(test_data.Client,
                                 test_data.Project,
                                 test_impls.UpdateObjectTest,
                                 TemporaryFilesystemTestCase):
    def test_admin_rename_uploaded_file(self):
        new_name = _file_obj_kwargs['name'] + 'waaa'
        request_data = {'name': new_name}
        self.client.force_authenticate(self.admin)
        for project in self.all_projects:
            file_ = build_file(project)
            self.do_put_object_test(
                file_, self.client, self.admin, file_name_url(file_),
                request_data)

            file_.refresh_from_db()
            self.assertEqual(new_name, file_.name)

    def test_admin_rename_uploaded_file_invalid_name(self):
        illegal_name = '..'
        file_ = build_file(self.project)
        self.do_put_object_invalid_args_test(
            file_, self.client, self.admin, file_name_url(file_),
            {'name': illegal_name})

    def test_other_rename_uploaded_file(self):
        file_ = build_file(self.visible_public_project)
        for user in self.staff, self.enrolled, self.nobody:
            self.do_put_object_permission_denied_test(
                file_, self.client, user, file_name_url(file_),
                {'name': 'steve'})


def file_content_url(uploaded_file):
    return reverse('uploaded-file-content',
                   kwargs={'pk': uploaded_file.pk})


class RetrieveUploadedFileContentTestCase(test_data.Client,
                                          test_data.Project,
                                          test_impls.GetObjectTest,
                                          TemporaryFilesystemTestCase):
    def test_admin_get_content(self):
        for project in self.all_projects:
            file_ = build_file(project)
            self.do_get_content_test(
                self.client, self.admin, file_content_url(file_),
                _file_obj_kwargs['content'])

    def test_staff_get_content(self):
        for project in self.all_projects:
            file_ = build_file(project)
            self.do_get_content_test(
                self.client, self.staff, file_content_url(file_),
                _file_obj_kwargs['content'])

    def test_enrolled_or_other_get_content(self):
        for user in self.enrolled, self.nobody:
            file_ = build_file(self.visible_public_project)
            self.do_permission_denied_get_test(
                self.client, user, file_content_url(file_))

    def do_get_content_test(self, client, user, url, expected_content):
        client.force_authenticate(user)
        response = client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(
            expected_content,
            b''.join((chunk for chunk in response.streaming_content)))


class UpdateUploadedFileContentTestCase(test_data.Client,
                                        test_data.Project,
                                        test_impls.UpdateObjectTest,
                                        TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()
        self.new_content = _file_obj_kwargs['content'] + b'stevestavestove'

    @property
    def updated_file(self):
        return SimpleUploadedFile(_file_obj_kwargs['name'], self.new_content)

    def test_admin_update_content(self):
        self.client.force_authenticate(self.admin)
        for project in self.all_projects:
            file_ = build_file(project)
            response = self.client.put(file_content_url(file_),
                                       {'file_obj': self.updated_file})

            self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
            file_.refresh_from_db()
            self.assertEqual(self.new_content, file_.file_obj.read())

    def test_other_update_content(self):
        file_ = build_file(self.visible_public_project)
        for user in self.staff, self.enrolled, self.nobody:
            self.do_put_object_permission_denied_test(
                file_, self.client, user, file_content_url(file_),
                {'file_obj': self.updated_file})
            file_.refresh_from_db()
            self.assertEqual(_file_obj_kwargs['content'],
                             file_.file_obj.read())
