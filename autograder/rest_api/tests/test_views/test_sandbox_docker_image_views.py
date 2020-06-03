from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.rest_api.tests.test_views.ag_view_test_base import AGViewTestBase


class _SetUp(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        ag_models.SandboxDockerImage.objects.exclude(display_name='Default').delete()

        self.superuser = obj_build.make_user(superuser=True)
        self.course = obj_build.make_course()
        self.admin = obj_build.make_admin_user(self.course)
        self.staff = obj_build.make_staff_user(self.course)

        # Create them out of order to verify sortedness
        self.image2 = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 2', tag='tag2'
        )

        self.image1 = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 1', tag='tag1'
        )


class ListGlobalImagesTestCase(_SetUp):
    def setUp(self):
        super().setUp()
        # This one should be filtered out of the global list endpoint
        ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image with an course', tag='very_tag', course=self.course
        )

        self.url = reverse('global-sandbox-images')

    def test_superuser_list_sandbox_images(self):
        self.client.force_authenticate(self.superuser)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        expected = [
            ag_models.SandboxDockerImage.objects.get(display_name='Default').to_dict(),
            self.image1.to_dict(),
            self.image2.to_dict()
        ]
        self.assertEqual(expected, response.data)

    def test_admin_for_any_course_list_sandbox_images(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        expected = [
            ag_models.SandboxDockerImage.objects.get(display_name='Default').to_dict(),
            self.image1.to_dict(),
            self.image2.to_dict()
        ]
        self.assertEqual(expected, response.data)

    def test_non_admin_for_any_course_list_sandbox_images_permission_denied(self):
        self.client.force_authenticate(self.staff)

        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


@mock.patch('autograder.core.tasks.push_image')
@mock.patch('autograder.utils.retry.sleep', new=mock.Mock())
class BuildGlobalImageTestCase(_SetUp):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.url = reverse('global-sandbox-images')

        self.files = [
            SimpleUploadedFile('Dockerfile', b'FROM jameslp/ag-ubuntu-16:1'),
            SimpleUploadedFile('filey.txt', b'')
        ]

        self.superuser = obj_build.make_user(superuser=True)
        self.admin = obj_build.make_admin_user(obj_build.make_course())

    def test_superuser_create_global_sandbox_image(self, push_image_mock) -> None:
        self.client.force_authenticate(self.superuser)
        response = self.client.post(self.url, {'files': self.files}, format='multipart')
        self.assertEqual(status.HTTP_202_ACCEPTED, response.status_code)
        self.assertEqual(ag_models.BuildImageStatus.queued.value, response.data['status'])

        loaded = ag_models.BuildSandboxDockerImageTask.objects.get(
            pk=response.data['pk']
        )
        self.assertEqual(['Dockerfile', 'filey.txt'], loaded.filenames)
        self.assertEqual(ag_models.BuildImageStatus.done, loaded.status)

        push_image_mock.assert_called_once()

    def test_non_superuser_create_global_sandbox_image_permission_denied(self, push_image_mock):
        self.do_permission_denied_create_test(
            ag_models.BuildSandboxDockerImageTask.objects,
            self.client, self.admin, self.url,
            {'files': self.files}, format='multipart'
        )
        push_image_mock.assert_not_called()


class ListSandboxDockerImagesForCourseViewTestCase(_SetUp):
    def setUp(self):
        super().setUp()

        self.course_image1 = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 3', tag='tag3', course=self.course)

        self.course_image2 = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 2', tag='tag2', course=self.course)

        self.url = reverse('course-sandbox-images', kwargs={'pk': self.course.pk})

    def test_admin_list_images_for_their_course(self) -> None:
        self.do_list_objects_test(
            self.client, self.admin, self.url,
            [self.course_image2.to_dict(), self.course_image1.to_dict()])

    def test_non_admin_list_images_for_course_permission_denied(self) -> None:
        self.do_permission_denied_get_test(self.client, self.staff, self.url)


@mock.patch('autograder.core.tasks.push_image')
@mock.patch('autograder.utils.retry.sleep', new=mock.Mock())
class BuildSandboxDockerImageForCourseViewTestCase(_SetUp):
    def setUp(self):
        super().setUp()
        self.course = obj_build.make_course()

        self.client = APIClient()
        self.url = reverse('course-sandbox-images', kwargs={'pk': self.course.pk})

        self.files = [
            SimpleUploadedFile('Dockerfile', b'FROM jameslp/ag-ubuntu-16:1'),
            SimpleUploadedFile('filey.txt', b'')
        ]

        self.admin = obj_build.make_admin_user(self.course)

    def test_admin_create_image_for_their_course(self, push_image_mock) -> None:
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, {'files': self.files}, format='multipart')
        self.assertEqual(status.HTTP_202_ACCEPTED, response.status_code)
        self.assertEqual(ag_models.BuildImageStatus.queued.value, response.data['status'])

        loaded = ag_models.BuildSandboxDockerImageTask.objects.get(
            pk=response.data['pk']
        )
        self.assertEqual(['Dockerfile', 'filey.txt'], loaded.filenames)
        self.assertEqual(ag_models.BuildImageStatus.done, loaded.status)
        self.assertEqual(self.course, loaded.course)

        push_image_mock.assert_called_once()

    def test_non_admin_create_image_for_course_permission_denied(self, push_image_mock) -> None:
        self.do_permission_denied_create_test(
            ag_models.BuildSandboxDockerImageTask.objects,
            self.client, self.staff, self.url,
            {'files': self.files}, format='multipart'
        )
        push_image_mock.assert_not_called()


class ListBuildTaskTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.course = obj_build.make_course()
        self.admin = obj_build.make_admin_user(self.course)

        self.global_build_tasks = [
            ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
                files=[SimpleUploadedFile('Dockerfile', b'')],
                course=None
            ).to_dict(),
            ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
                files=[SimpleUploadedFile('Dockerfile', b'')],
                course=None
            ).to_dict()
        ]

        self.build_tasks_for_course = [
            ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
                files=[SimpleUploadedFile('Dockerfile', b'')],
                course=self.course
            ).to_dict(),
            ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
                files=[SimpleUploadedFile('Dockerfile', b'')],
                course=self.course
            ).to_dict()
        ]

    def test_superuser_list_global_build_tasks(self) -> None:
        superuser = obj_build.make_user(superuser=True)
        url = reverse('list-global-image-builds')
        self.do_list_objects_test(self.client, superuser, url, self.global_build_tasks)

    def test_non_superuser_list_global_build_tasks_permission_denied(self) -> None:
        url = reverse('list-global-image-builds')
        self.do_permission_denied_get_test(self.client, self.admin, url)

    def test_admin_list_build_tasks_for_course(self) -> None:
        url = reverse('list-course-image-builds', kwargs={'pk': self.course.pk})
        self.do_list_objects_test(self.client, self.admin, url, self.build_tasks_for_course)

    def test_non_admin_list_build_tasks_for_course(self) -> None:
        url = reverse('list-course-image-builds', kwargs={'pk': self.course.pk})
        staff = obj_build.make_staff_user(self.course)
        self.do_permission_denied_get_test(self.client, staff, url)


class BuildTaskDetailViewTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.superuser = obj_build.make_user(superuser=True)
        self.course = obj_build.make_course()
        self.admin = obj_build.make_admin_user(self.course)
        self.staff = obj_build.make_staff_user(self.course)

    def _make_global_build_task(self):
        return ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            files=[SimpleUploadedFile('Dockerfile', b'')],
            course=None
        )

    def _make_build_task_for_course(self):
        return ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            files=[SimpleUploadedFile('Dockerfile', b'')],
            course=self.course
        )

    def test_superuser_get_global_build_task(self) -> None:
        task = self._make_global_build_task()
        url = reverse('image-build-task-detail', kwargs={'pk': task.pk})
        self.do_get_object_test(self.client, self.superuser, url, task.to_dict())

    def test_non_superuser_get_global_build_task_permission_denied(self) -> None:
        task = self._make_global_build_task()
        url = reverse('image-build-task-detail', kwargs={'pk': task.pk})
        self.do_permission_denied_get_test(self.client, self.admin, url)

    def test_superuser_get_global_task_output(self) -> None:
        output = b'oniresatonwunroeivbmnoiufaoniremvoinemofnt'
        task = self._make_global_build_task()
        with open(task.output_filename, 'wb') as f:
            f.write(output)

        self.client.force_authenticate(self.superuser)
        response = self.client.get(reverse('image-build-task-output', kwargs={'pk': task.pk}))
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        self.assertEqual(output, b''.join(response.streaming_content))

    def test_non_superuser_get_global_task_output(self) -> None:
        task = self._make_global_build_task()
        url = reverse('image-build-task-output', kwargs={'pk': task.pk})
        self.do_permission_denied_get_test(self.client, self.admin, url)

    def test_admin_get_build_task_for_course(self) -> None:
        task = self._make_build_task_for_course()
        url = reverse('image-build-task-detail', kwargs={'pk': task.pk})
        self.do_get_object_test(self.client, self.admin, url, task.to_dict())

    def test_non_admin_get_build_task_for_course_permission_denied(self) -> None:
        task = self._make_build_task_for_course()
        url = reverse('image-build-task-detail', kwargs={'pk': task.pk})
        self.do_permission_denied_get_test(self.client, self.staff, url)

    def test_admin_get_task_for_course_output(self) -> None:
        output = b'noxcievmnowufyvzncevtnof'
        task = self._make_build_task_for_course()
        with open(task.output_filename, 'wb') as f:
            f.write(output)

        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse('image-build-task-output', kwargs={'pk': task.pk}))
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        self.assertEqual(output, b''.join(response.streaming_content))

    def test_non_admin_get_task_for_course_output(self) -> None:
        task = self._make_build_task_for_course()
        url = reverse('image-build-task-output', kwargs={'pk': task.pk})
        self.do_permission_denied_get_test(self.client, self.staff, url)

    def test_superuser_cancel_global_build_task(self) -> None:
        task = self._make_global_build_task()
        self._do_cancel_task_test(self.superuser, task)

    def test_non_superuser_cancel_global_build_task_permission_denied(self) -> None:
        task = self._make_global_build_task()
        self._do_permission_denied_cancel_task_test(self.admin, task)

    def test_admin_cancel_build_task_for_course(self) -> None:
        task = self._make_build_task_for_course()
        self._do_cancel_task_test(self.admin, task)

    def test_non_admin_cancel_build_task_for_course_permission_denied(self) -> None:
        task = self._make_build_task_for_course()
        self._do_permission_denied_cancel_task_test(self.staff, task)

    def test_cancel_finished_task_bad_request(self) -> None:
        task = self._make_global_build_task()
        url = reverse('cancel-image-build-task', kwargs={'pk': task.pk})
        self.client.force_authenticate(self.superuser)
        done_statuses = [
            ag_models.BuildImageStatus.done,
            ag_models.BuildImageStatus.image_invalid,
            ag_models.BuildImageStatus.internal_error,
            ag_models.BuildImageStatus.cancelled
        ]
        for build_status in done_statuses:
            task.status = build_status
            task.save()

            response = self.client.post(url)
            self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def _do_cancel_task_test(self, user, task: ag_models.BuildSandboxDockerImageTask):
        self.client.force_authenticate(user)
        url = reverse('cancel-image-build-task', kwargs={'pk': task.pk})
        response = self.client.post(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        loaded = ag_models.BuildSandboxDockerImageTask.objects.get(pk=task.pk)
        self.assertEqual(ag_models.BuildImageStatus.cancelled, loaded.status)
        self.assertEqual(loaded.to_dict(), response.data)

    def _do_permission_denied_cancel_task_test(
        self, user, task: ag_models.BuildSandboxDockerImageTask
    ):
        self.client.force_authenticate(user)
        url = reverse('cancel-image-build-task', kwargs={'pk': task.pk})
        response = self.client.post(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        loaded = ag_models.BuildSandboxDockerImageTask.objects.get(pk=task.pk)
        self.assertEqual(ag_models.BuildImageStatus.queued, loaded.status)


class SandboxImageDetailViewTestCase(_SetUp):
    def test_superuser_get_global_sandbox_image(self):
        url = reverse('sandbox-docker-image-detail', kwargs={'pk': self.image1.pk})
        self.client.force_authenticate(self.superuser)

        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self.image1.to_dict(), response.data)

    def test_admin_for_any_course_get_global_sandbox_image(self):
        url = reverse('sandbox-docker-image-detail', kwargs={'pk': self.image1.pk})
        self.client.force_authenticate(self.admin)

        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self.image1.to_dict(), response.data)

    def test_non_admin_for_any_course_get_global_sandbox_image_permission_denied(self):
        url = reverse('sandbox-docker-image-detail', kwargs={'pk': self.image1.pk})
        self.client.force_authenticate(self.staff)

        response = self.client.get(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_admin_get_sandbox_image_with_course(self):
        self.client.force_authenticate(self.admin)

        image_with_course = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 3', tag='tag3', course=self.course
        )
        response = self.client.get(
            reverse('sandbox-docker-image-detail', kwargs={'pk': image_with_course.pk})
        )
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(image_with_course.to_dict(), response.data)

    def test_non_admin_get_sandbox_image_with_course_permission_denied(self) -> None:
        other_course = obj_build.make_course()
        other_admin = obj_build.make_admin_user(other_course)
        image_with_course = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 3', tag='tag3', course=self.course
        )
        self.do_permission_denied_get_test(
            self.client, other_admin,
            reverse('sandbox-docker-image-detail', kwargs={'pk': image_with_course.pk}))

    def test_superuser_update_global_sandbox_image(self):
        url = reverse('sandbox-docker-image-detail', kwargs={'pk': self.image1.pk})
        self.do_patch_object_test(
            self.image1, self.client, self.superuser, url,
            {'display_name': 'New Display Name'})

    def test_non_superuser_update_global_sandbox_image_permission_denied(self):
        url = reverse('sandbox-docker-image-detail', kwargs={'pk': self.image1.pk})
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            url,
            {'display_name': 'New Display Name'}
        )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_admin_update_sandbox_image_with_course(self) -> None:
        image_with_course = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 3', tag='tag3', course=self.course
        )
        self.do_patch_object_test(
            image_with_course, self.client, self.admin,
            reverse('sandbox-docker-image-detail', kwargs={'pk': image_with_course.pk}),
            {'display_name': 'New Display Name'})

    def test_non_admin_update_sandbox_image_with_course_permission_denied(self) -> None:
        other_course = obj_build.make_course()
        other_admin = obj_build.make_admin_user(other_course)
        image_with_course = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 3', tag='tag3', course=self.course
        )
        self.do_patch_object_permission_denied_test(
            image_with_course, self.client, other_admin,
            reverse('sandbox-docker-image-detail', kwargs={'pk': image_with_course.pk}),
            {'display_name': 'New Display Name', 'tag': 'new_taggy'})

    def test_superuser_delete_global_sandbox_image(self) -> None:
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 3', tag='tag3'
        )
        self.do_delete_object_test(
            image, self.client, self.superuser,
            reverse('sandbox-docker-image-detail', kwargs={'pk': image.pk})
        )

    def test_delete_default_image_bad_request(self) -> None:
        image = ag_models.SandboxDockerImage.objects.get(display_name='Default')
        self.client.force_authenticate(self.superuser)
        url = reverse('sandbox-docker-image-detail', kwargs={'pk': image.pk})

        response = self.client.delete(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        image.refresh_from_db()

    def test_admin_delete_global_sanbdox_image_permission_denied(self) -> None:
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 3', tag='tag3'
        )
        self.do_delete_object_permission_denied_test(
            image, self.client, self.admin,
            reverse('sandbox-docker-image-detail', kwargs={'pk': image.pk})
        )

    def test_admin_delete_course_sandbox_image(self) -> None:
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 3', tag='tag3', course=self.course
        )
        self.do_delete_object_test(
            image, self.client, self.admin,
            reverse('sandbox-docker-image-detail', kwargs={'pk': image.pk})
        )

    def test_non_admin_delete_course_sandbox_image_permission_denied(self) -> None:
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 3', tag='tag3', course=self.course
        )

        other_course = obj_build.make_course()
        other_admin = obj_build.make_admin_user(other_course)

        self.do_delete_object_permission_denied_test(
            image, self.client, other_admin,
            reverse('sandbox-docker-image-detail', kwargs={'pk': image.pk})
        )


@mock.patch('autograder.core.tasks.push_image')
@mock.patch('autograder.utils.retry.sleep', new=mock.Mock())
class RebuildSandboxImageViewTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.url = reverse('global-sandbox-images')

        self.files = [
            SimpleUploadedFile('Dockerfile', b'FROM jameslp/ag-ubuntu-16:1'),
            SimpleUploadedFile('filey.txt', b'')
        ]

        self.course = obj_build.make_course()
        self.admin = obj_build.make_admin_user(self.course)

    def test_superuser_update_global_sandbox_image(self, push_image_mock):
        superuser = obj_build.make_user(superuser=True)
        image = obj_build.make_sandbox_docker_image()
        self._do_rebuild_image_test(superuser, image)
        push_image_mock.assert_called_once()

    def test_non_superuser_update_global_sandbox_image_permission_denied(self, *args):
        image = obj_build.make_sandbox_docker_image()
        self._do_permission_denied_rebuild_image_test(self.admin, image)

    def test_admin_update_sandbox_image_with_course(self, push_image_mock) -> None:
        image = obj_build.make_sandbox_docker_image(self.course)
        self._do_rebuild_image_test(self.admin, image)
        push_image_mock.assert_called_once()

    def test_non_admin_update_sandbox_image_with_course_permission_denied(self, *args) -> None:
        staff = obj_build.make_staff_user(self.course)
        image = obj_build.make_sandbox_docker_image(self.course)
        self._do_permission_denied_rebuild_image_test(staff, image)

    def _do_rebuild_image_test(self, user, image: ag_models.SandboxDockerImage):
        self.client.force_authenticate(user)
        url = reverse('rebuild-sandbox-docker-image', kwargs={'pk': image.pk})

        original_tag = image.tag

        response = self.client.put(url, {'files': self.files}, format='multipart')
        self.assertEqual(status.HTTP_202_ACCEPTED, response.status_code)
        self.assertEqual(ag_models.BuildImageStatus.queued.value, response.data['status'])

        loaded_task = ag_models.BuildSandboxDockerImageTask.objects.get(
            pk=response.data['pk']
        )
        self.assertEqual(['Dockerfile', 'filey.txt'], loaded_task.filenames)
        self.assertEqual(ag_models.BuildImageStatus.done, loaded_task.status)

        image.refresh_from_db()
        self.assertNotEqual(original_tag, image.tag)

    def _do_permission_denied_rebuild_image_test(self, user, image: ag_models.SandboxDockerImage):
        self.client.force_authenticate(user)
        url = reverse('rebuild-sandbox-docker-image', kwargs={'pk': image.pk})

        original_tag = image.tag

        response = self.client.put(url, {'files': self.files}, format='multipart')
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

        image.refresh_from_db()
        self.assertEqual(original_tag, image.tag)
