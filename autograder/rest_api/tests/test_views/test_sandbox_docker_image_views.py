from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import autograder.core.models as ag_models
import autograder.utils.testing.model_obj_builders as obj_build
from autograder.rest_api.tests.test_views.ag_view_test_base import AGViewTestBase


class _SetUp(AGViewTestBase):
    @classmethod
    def setUpTestData(cls):
        ag_models.SandboxDockerImage.objects.exclude(display_name='Default').delete()

        cls.superuser = obj_build.make_user(superuser=True)
        cls.course = obj_build.make_course()
        cls.admin = obj_build.make_admin_user(cls.course)
        cls.staff = obj_build.make_staff_user(cls.course)

    def setUp(self):
        super().setUp()
        self.client = APIClient()

        # Create them out of order to verify sortedness
        self.image2 = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 2', tag='tag2'
        )

        self.image1 = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 1', tag='tag1'
        )


class SandboxDockerImageViewTestCase(_SetUp):
    def test_superuser_get_sandbox_image(self):
        url = reverse('sandbox-docker-image-detail', kwargs={'pk': self.image1.pk})
        self.client.force_authenticate(self.superuser)

        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self.image1.to_dict(), response.data)

    def test_admin_for_any_course_get_sandbox_image(self):
        url = reverse('sandbox-docker-image-detail', kwargs={'pk': self.image1.pk})
        self.client.force_authenticate(self.admin)

        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self.image1.to_dict(), response.data)

    def test_non_admin_for_any_course_get_sandbox_image_permission_denied(self):
        url = reverse('sandbox-docker-image-detail', kwargs={'pk': self.image1.pk})
        self.client.force_authenticate(self.staff)

        response = self.client.get(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_superuser_list_sandbox_images(self):
        url = reverse('sandbox-docker-image-list')
        self.client.force_authenticate(self.superuser)

        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        expected = [
            ag_models.SandboxDockerImage.objects.get(name='default').to_dict(),
            self.image1.to_dict(),
            self.image2.to_dict()
        ]
        self.assertEqual(expected, response.data)

    def test_admin_for_any_course_list_sandbox_images(self):
        url = reverse('sandbox-docker-image-list')
        self.client.force_authenticate(self.admin)

        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        expected = [
            ag_models.SandboxDockerImage.objects.get(name='default').to_dict(),
            self.image1.to_dict(),
            self.image2.to_dict()
        ]
        self.assertEqual(expected, response.data)

    def test_non_admin_for_any_course_list_sandbox_images_permission_denied(self):
        url = reverse('sandbox-docker-image-list')
        self.client.force_authenticate(self.staff)

        response = self.client.get(url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_superuser_create_sandbox_image(self):
        url = reverse('sandbox-docker-image-list')
        self.client.force_authenticate(self.superuser)

        response = self.client.post(
            url,
            {'name': 'new_image', 'display_name': 'Spam', 'tag': 'taggy'}
        )

        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        # 4 because of the default image and the 2 we created in the test
        self.assertEqual(4, ag_models.SandboxDockerImage.objects.count())

    def test_non_superuser_create_sandbox_image_permission_denied(self):
        url = reverse('sandbox-docker-image-list')
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            url,
            {'name': 'new_image', 'display_name': 'Spam', 'tag': 'taggy'}
        )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        # 3 because of the default image and the 2 we created in the test
        self.assertEqual(3, ag_models.SandboxDockerImage.objects.count())

    def test_superuser_update_sandbox_image(self):
        url = reverse('sandbox-docker-image-detail', kwargs={'pk': self.image1.pk})
        self.client.force_authenticate(self.superuser)

        response = self.client.patch(
            url,
            {'display_name': 'New Display Name', 'tag': 'new_taggy'}
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        self.image1.refresh_from_db()

        self.assertEqual('New Display Name', self.image1.display_name)
        self.assertEqual('new_taggy', self.image1.tag)

    def test_non_superuser_update_sandbox_image_permission_denied(self):
        url = reverse('sandbox-docker-image-detail', kwargs={'pk': self.image1.pk})
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            url,
            {'display_name': 'New Display Name', 'tag': 'new_taggy'}
        )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class SandboxDockerImageForCourseViewTestCase(_SetUp):
    def setUp(self):
        super().setUp()

        self.course_image1 = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 3', tag='tag3', course=self.course)

        self.course_image2 = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 2', tag='tag2', course=self.course)

        self.url = reverse('sandbox-docker-images-for-course', kwargs={'pk': self.course.pk})

    def test_admin_list_images_for_their_course(self) -> None:
        self.do_list_objects_test(
            self.client, self.admin, self.url,
            [self.course_image2.to_dict(), self.course_image1.to_dict()])

    def test_non_admin_list_images_for_course_permission_denied(self) -> None:
        self.do_permission_denied_get_test(self.client, self.staff, self.url)

    def test_admin_create_image_for_their_course(self) -> None:
        self.do_create_object_test(
            ag_models.SandboxDockerImage.objects, self.client, self.admin, self.url,
            {'display_name': 'another image', 'tag': 'an tag'}
        )

    def test_non_admin_create_image_for_course_permission_denied(self) -> None:
        self.do_permission_denied_create_test(
            ag_models.SandboxDockerImage.objects, self.client, self.staff, self.url,
            {'display_name': 'another image', 'tag': 'an tag'}

        )
