import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.core import constants
from autograder.rest_api.tests.test_views.ag_view_test_base import AGViewTestBase
from autograder.utils.testing import UnitTestBase


class ListInstructorFilesTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.project = obj_build.make_project()
        self.course = self.project.course

    def test_admin_list_files(self):
        self.do_list_instructor_files_test(obj_build.make_admin_user(self.course), self.project)

    def test_staff_list_files(self):
        self.do_list_instructor_files_test(obj_build.make_staff_user(self.course), self.project)

    def test_student_list_patterns(self):
        self.project.validate_and_update(visible_to_students=True)
        self.do_permission_denied_test(obj_build.make_student_user(self.course), self.project)

    def test_other_list_patterns(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        self.do_permission_denied_test(obj_build.make_user(), self.project)

    def do_list_instructor_files_test(self, user, project):
        serialized_files = [
            obj_build.make_instructor_file(project).to_dict(),
            obj_build.make_instructor_file(project).to_dict(),
            obj_build.make_instructor_file(project).to_dict(),
            obj_build.make_instructor_file(project).to_dict(),
        ]
        self.client.force_authenticate(user)
        response = self.client.get(get_instructor_files_url(project))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertCountEqual(serialized_files, response.data)

    def do_permission_denied_test(self, user, project):
        obj_build.make_instructor_file(project)
        self.client.force_authenticate(user)
        response = self.client.get(get_instructor_files_url(project))
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


def get_instructor_files_url(project: ag_models.Project) -> str:
    return reverse('instructor-files', kwargs={'pk': project.pk})


class CreateInstructorFileTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.project = obj_build.make_project()
        self.course = self.project.course

        self.file_obj = SimpleUploadedFile('file' + str(uuid.uuid4().hex),
                                           b'waaaaluigi')

    def test_admin_create_uploaded_file(self):
        self.assertEqual(0, self.project.instructor_files.count())
        self.client.force_authenticate(obj_build.make_admin_user(self.course))
        response = self.client.post(
            get_instructor_files_url(self.project),
            {'file_obj': self.file_obj}, format='multipart')
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
        self.client.force_authenticate(obj_build.make_admin_user(self.course))
        response = self.client.post(
            get_instructor_files_url(self.project), {'file_obj': bad_file}, format='multipart')
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(0, self.project.instructor_files.count())

    def test_invalid_create_too_large_uploaded_file(self):
        too_big_file = SimpleUploadedFile('spam', b'a' * (constants.MAX_PROJECT_FILE_SIZE + 1))
        self.assertEqual(0, self.project.instructor_files.count())
        self.client.force_authenticate(obj_build.make_admin_user(self.course))
        response = self.client.post(
            get_instructor_files_url(self.project), {'file_obj': too_big_file}, format='multipart')
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(0, self.project.instructor_files.count())

    def test_non_admin_create_uploaded_file_permission_denied(self):
        staff = obj_build.make_staff_user(self.course)
        student = obj_build.make_student_user(self.course)
        handgrader = obj_build.make_handgrader_user(self.course)
        guest = obj_build.make_user()

        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        for user in staff, student, handgrader, guest:
            self.assertEqual(0, self.project.instructor_files.count())

            self.client.force_authenticate(user)
            response = self.client.post(
                get_instructor_files_url(self.project),
                {'file_obj': self.file_obj}, format='multipart')
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
            self.assertEqual(0, self.project.instructor_files.count())

    def test_missing_file_obj_param(self):
        self.client.force_authenticate(obj_build.make_admin_user(self.course))
        response = self.client.post(get_instructor_files_url(self.project), {}, format='multipart')
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)


def file_url(uploaded_file):
    return reverse('instructor-file-detail', kwargs={'pk': uploaded_file.pk})


class _DetailViewTestSetup(AGViewTestBase):
    def setUp(self):
        super().setUp()

        self.client = APIClient()
        self.project = obj_build.make_project()
        self.course = self.project.course
        self.admin = obj_build.make_admin_user(self.course)
        self.staff = obj_build.make_staff_user(self.course)

        self.file_content = b'waaaluigi' + uuid.uuid4().hex.encode()
        self.file_ = ag_models.InstructorFile.objects.validate_and_create(
            file_obj=SimpleUploadedFile('file' + str(uuid.uuid4().hex), self.file_content),
            project=self.project)
        self.url = reverse('instructor-file-detail', kwargs={'pk': self.file_.pk})


class RetrieveUploadedFileTestCase(_DetailViewTestSetup):
    def test_admin_get_uploaded_file(self):
        self.do_get_object_test(self.client, self.admin, self.url, self.file_.to_dict())

    def test_staff_get_uploaded_file(self):
        self.do_get_object_test(
            self.client, obj_build.make_staff_user(self.course), self.url, self.file_.to_dict())

    def test_student_get_uploaded_file(self):
        self.project.validate_and_update(visible_to_students=True)
        self.do_permission_denied_get_test(
            self.client, obj_build.make_student_user(self.course), self.url)

    def test_other_get_uploaded_file(self):
        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)
        self.do_permission_denied_get_test(self.client, obj_build.make_user(), self.url)


def file_name_url(uploaded_file):
    return reverse('instructor-file-rename', kwargs={'pk': uploaded_file.pk})


class RenameUploadedFileTestCase(_DetailViewTestSetup):
    def setUp(self):
        super().setUp()
        self.url = reverse('instructor-file-rename', kwargs={'pk': self.file_.pk})

    def test_admin_rename_uploaded_file(self):
        new_name = 'i am a new name'
        self.do_put_object_test(
            self.file_, self.client, self.admin, self.url, {'name': new_name})

        self.file_.refresh_from_db()
        self.assertEqual(new_name, self.file_.name)

    def test_admin_rename_uploaded_file_invalid_name(self):
        illegal_name = '..'
        self.do_put_object_invalid_args_test(
            self.file_, self.client, self.admin, self.url, {'name': illegal_name})

    def test_non_admin_rename_uploaded_file(self):
        student = obj_build.make_student_user(self.course)
        handgrader = obj_build.make_handgrader_user(self.course)
        guest = obj_build.make_user()

        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        for user in self.staff, student, handgrader, guest:
            self.do_put_object_permission_denied_test(
                self.file_, self.client, user, self.url, {'name': 'steve'})


def file_content_url(uploaded_file):
    return reverse('instructor-file-content',
                   kwargs={'pk': uploaded_file.pk})


class RetrieveUploadedFileContentTestCase(_DetailViewTestSetup):
    def setUp(self):
        super().setUp()
        self.url = reverse('instructor-file-content', kwargs={'pk': self.file_.pk})

    def test_admin_get_content(self):
        self.do_get_content_test(self.client, self.admin, self.url, self.file_content)

    def test_staff_get_content(self):
        self.do_get_content_test(self.client, self.staff, self.url, self.file_content)

    def test_non_staff_get_content(self):
        student = obj_build.make_student_user(self.course)
        handgrader = obj_build.make_handgrader_user(self.course)
        guest = obj_build.make_user()

        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        for user in student, handgrader, guest:
            self.do_permission_denied_get_test(self.client, user, self.url)

    def do_get_content_test(self, client, user, url, expected_content):
        client.force_authenticate(user)
        response = client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertIn('Content-Length', response)
        self.assertEqual(
            expected_content, b''.join((chunk for chunk in response.streaming_content)))


class UpdateUploadedFileContentTestCase(_DetailViewTestSetup):
    def setUp(self):
        super().setUp()
        self.new_content = b'this is what you would call new content'
        self.url = reverse('instructor-file-content', kwargs={'pk': self.file_.pk})

    @property
    def updated_file(self):
        return SimpleUploadedFile(self.file_.name, self.new_content)

    def test_admin_update_content(self):
        self.client.force_authenticate(self.admin)
        original_last_modified = self.file_.last_modified

        response = self.client.put(
            self.url, {'file_obj': self.updated_file}, format='multipart')
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        self.file_.refresh_from_db()
        self.assertNotEqual(original_last_modified, self.file_.last_modified)
        self.assertEqual(self.new_content, self.file_.file_obj.read())
        self.assertEqual(self.file_.to_dict(), response.data)

    def test_non_admin_update_content_permission_denied(self):
        student = obj_build.make_student_user(self.course)
        handgrader = obj_build.make_handgrader_user(self.course)
        guest = obj_build.make_user()

        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        for user in self.staff, student, handgrader, guest:
            self.do_put_object_permission_denied_test(
                self.file_, self.client, user, self.url,
                {'file_obj': self.updated_file}, format='multipart')
            self.file_.refresh_from_db()
            self.assertEqual(self.file_content, self.file_.file_obj.read())

    def test_error_update_content_too_large(self):
        self.client.force_authenticate(self.admin)
        too_big_updated_file = SimpleUploadedFile(
            self.file_.name, b'a' * (constants.MAX_PROJECT_FILE_SIZE + 1))

        response = self.client.put(
            self.url, {'file_obj': too_big_updated_file}, format='multipart')

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.file_.refresh_from_db()
        with self.file_.open('rb') as f:
            self.assertEqual(self.file_content, f.read())

    def test_missing_file_obj_param(self):
        self.client.force_authenticate(self.admin)
        response = self.client.put(self.url, {}, format='multipart')
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn('file_obj', response.data)


class DeleteUploadedFileTestCase(_DetailViewTestSetup):
    def test_admin_delete_file(self):
        self.do_delete_object_test(self.file_, self.client, self.admin, self.url)
        with self.assertRaises(FileNotFoundError):
            self.file_.file_obj.read()

    def test_non_admin_delete_file_permission_denied(self):
        student = obj_build.make_student_user(self.course)
        handgrader = obj_build.make_handgrader_user(self.course)
        guest = obj_build.make_user()

        self.project.validate_and_update(visible_to_students=True, guests_can_submit=True)

        for user in self.staff, student, handgrader, guest:
            self.do_delete_object_permission_denied_test(self.file_, self.client, user, self.url)
            self.file_.file_obj.read()
