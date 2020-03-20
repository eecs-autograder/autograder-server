from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
from autograder.rest_api.inspect_remote_image import SignatureVerificationFailedError
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

        self.url = reverse('list-course-sandbox-images', kwargs={'pk': self.course.pk})

    def test_admin_list_images_for_their_course(self) -> None:
        self.do_list_objects_test(
            self.client, self.admin, self.url,
            [self.course_image2.to_dict(), self.course_image1.to_dict()])

    def test_non_admin_list_images_for_course_permission_denied(self) -> None:
        self.do_permission_denied_get_test(self.client, self.staff, self.url)


@mock.patch('autograder.core.tasks.push_image', new=mock.Mock())
class BuildSandboxDockerImageForCourseViewTestCase(_SetUp):
    def test_admin_create_image_for_their_course(self) -> None:
        self.fail('build request')

    def test_non_admin_create_image_for_course_permission_denied(self) -> None:
        self.fail('build request')
#

@mock.patch('autograder.core.tasks.push_image', new=mock.Mock())
class BuildNewImageViewTests(AGViewTestBase):
    pass


class ListBuildTaskTestCase(AGViewTestBase):
    def test_superuser_list_global_build_tasks(self) -> None:
        self.fail()

    def test_non_superuser_list_global_build_tasks_permission_denied(self) -> None:
        self.fail()

    def test_admin_list_build_tasks_for_course(self) -> None:
        self.fail()

    def test_non_admin_list_build_tasks_for_course(self) -> None:
        self.fail()


class BuildTaskDetailViewTestCase(AGViewTestBase):
    def test_superuser_get_global_build_task(self) -> None:
        self.fail()

    def test_non_superuser_get_global_build_task_permission_denied(self) -> None:
        self.fail()

    def test_admin_get_build_task_for_course(self) -> None:
        self.fail()

    def test_non_admin_get_build_task_for_course_permission_denied(self) -> None:
        self.fail()

    def test_superuser_cancel_global_build_task(self) -> None:
        self.fail()

    def test_non_superuser_cancel_global_build_task_permission_denied(self) -> None:
        self.fail()

    def test_admin_cancel_build_task_for_course(self) -> None:
        self.fail()

    def test_non_admin_cancel_build_task_for_course_permission_denied(self) -> None:
        self.fail()


class GetUpdateSandboxImageViewTestCase(_SetUp):
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


@mock.patch('autograder.core.tasks.push_image', new=mock.Mock())
class RebuildSandboxImageViewTestCase(AGViewTestBase):
    def test_superuser_update_global_sandbox_image(self):
        self.fail('build request')

    def test_non_superuser_update_global_sandbox_image_permission_denied(self):
        self.fail('build request')

    def test_admin_update_sandbox_image_with_course(self) -> None:
        self.fail('build request')

    def test_non_admin_update_sandbox_image_with_course_permission_denied(self) -> None:
        self.fail('build request')
