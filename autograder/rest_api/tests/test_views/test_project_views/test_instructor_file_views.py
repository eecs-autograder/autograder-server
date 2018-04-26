import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
import autograder.rest_api.tests.test_views.ag_view_test_base as test_impls
import autograder.rest_api.tests.test_views.common_generic_data as test_data
from autograder.core import constants
from autograder.utils.testing import UnitTestBase


class _UploadedFilesSetUp(test_data.Client, test_data.Project):
    pass


class ListUploadedFilesTestCase(_UploadedFilesSetUp, UnitTestBase):
    def test_admin_list_files(self):
        for project in self.all_projects:
            self.do_list_instructor_files_test(self.admin, project)

    def test_staff_list_files(self):
        for project in self.all_projects:
            self.do_list_instructor_files_test(self.staff, project)

    def test_enrolled_list_patterns(self):
        for project in self.all_projects:
            self.do_permission_denied_test(self.enrolled, project)

    def test_other_list_patterns(self):
        for project in self.all_projects:
            self.do_permission_denied_test(self.nobody, project)

    def do_list_instructor_files_test(self, user, project):
        serialized_files = self.build_instructor_files(project)
        self.client.force_authenticate(user)
        response = self.client.get(self.get_instructor_files_url(project))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertCountEqual(serialized_files, response.data)

    def do_permission_denied_test(self, user, project):
        self.build_instructor_files(project)
        self.client.force_authenticate(user)
        response = self.client.get(self.get_instructor_files_url(project))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def build_instructor_files(self, project):
        num_files = 3
        if not project.instructor_files.count():
            for i in range(num_files):
                name = 'file' + str(i)
                file_ = SimpleUploadedFile(name, b'file with stuff')
                ag_models.InstructorFile.objects.validate_and_create(
                    project=project, file_obj=file_)

        serialized_files = ag_serializers.InstructorFileSerializer(
            project.instructor_files.all(), many=True).data
        self.assertEqual(num_files, len(serialized_files))
        return serialized_files


class CreateUploadedFileTestCase(_UploadedFilesSetUp,
                                 UnitTestBase):
    def setUp(self):
        super().setUp()
        self.file_obj = SimpleUploadedFile('file' + str(uuid.uuid4().hex),
                                           b'waaaaluigi')

    def test_admin_create_uploaded_file(self):
        self.assertEqual(0, self.project.instructor_files.count())
        args = {'file_obj': self.file_obj}
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.get_instructor_files_url(self.project), args,
            format='multipart')
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, self.project.instructor_files.count())
        loaded = self.project.instructor_files.first()
        self.assertEqual(loaded.to_dict(), response.data)

        self.file_obj.seek(0)
        self.assertEqual(self.file_obj.name, loaded.name)
        self.assertEqual(self.file_obj.read(), loaded.file_obj.read())

    def test_admin_create_uploaded_file_invalid_settings(self):
        bad_file = SimpleUploadedFile('..', b'waaaario')
        self.assertEqual(0, self.project.instructor_files.count())
        args = {'file_obj': bad_file}
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.get_instructor_files_url(self.project), args,
            format='multipart')
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(0, self.project.instructor_files.count())

    def test_invalid_create_too_large_uploaded_file(self):
        too_big_file = SimpleUploadedFile('spam', b'a' * (constants.MAX_PROJECT_FILE_SIZE + 1))
        self.assertEqual(0, self.project.instructor_files.count())
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.get_instructor_files_url(self.project), {'file_obj': too_big_file},
            format='multipart')
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(0, self.project.instructor_files.count())

    def test_non_admin_create_uploaded_file_permission_denied(self):
        for user in self.staff, self.enrolled, self.nobody:
            self.assertEqual(0, self.project.instructor_files.count())
            args = {'file_obj': self.file_obj}
            self.client.force_authenticate(user)
            response = self.client.post(
                self.get_instructor_files_url(self.project), args,
                format='multipart')
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
            self.assertEqual(0, self.project.instructor_files.count())

    def test_missing_file_obj_param(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.get_instructor_files_url(self.project), {}, format='multipart')
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)


def file_url(uploaded_file):
    return reverse('uploaded-file-detail', kwargs={'pk': uploaded_file.pk})


class _BuildFile:
    def setUp(self):
        super().setUp()
        self.file_obj_kwargs = {'name': 'file' + str(uuid.uuid4().hex),
                                'content': b'waaaluigi'}

    def build_file(self, project):
        return ag_models.InstructorFile.objects.validate_and_create(
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

    def test_missing_file_obj_param(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.get_instructor_files_url(self.project), {}, format='multipart')
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)


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
