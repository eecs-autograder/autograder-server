from unittest import mock

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


@mock.patch('autograder.rest_api.serializers.serializer_impls.inspect_remote_image',
            new=lambda tag: {'config': {'Entrypoint': None, 'Cmd': ['/bin/bash']}})
class SandboxDockerImageViewTestCase(_SetUp):
    def setUp(self):
        super().setUp()
        # This one should be filtered out of the global list endpoint
        ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image with an course', tag='very_tag', course=self.course
        )

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

    def test_superuser_create_courseless_sandbox_image(self):
        url = reverse('sandbox-docker-image-list')
        self.do_create_object_test(
            ag_models.SandboxDockerImage.objects, self.client, self.superuser, url,
            {'name': 'new_image', 'display_name': 'Spam', 'tag': 'taggy'})

    def test_non_superuser_create_courseless_sandbox_image_permission_denied(self):
        url = reverse('sandbox-docker-image-list')
        self.do_permission_denied_create_test(
            ag_models.SandboxDockerImage.objects, self.client, self.admin, url,
            {'name': 'new_image', 'display_name': 'Spam', 'tag': 'taggy'})

    def test_superuser_update_courseless_sandbox_image(self):
        url = reverse('sandbox-docker-image-detail', kwargs={'pk': self.image1.pk})
        self.do_patch_object_test(
            self.image1, self.client, self.superuser, url,
            {'display_name': 'New Display Name', 'tag': 'new_taggy'})

    def test_non_superuser_update_courseless_sandbox_image_permission_denied(self):
        url = reverse('sandbox-docker-image-detail', kwargs={'pk': self.image1.pk})
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            url,
            {'display_name': 'New Display Name', 'tag': 'new_taggy'}
        )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_admin_update_sandbox_image_with_course(self) -> None:
        image_with_course = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 3', tag='tag3', course=self.course
        )
        self.do_patch_object_test(
            image_with_course, self.client, self.admin,
            reverse('sandbox-docker-image-detail', kwargs={'pk': image_with_course.pk}),
            {'display_name': 'New Display Name', 'tag': 'new_taggy'})

    def test_non_admin_get_sandbox_image_with_course_permission_denied(self) -> None:
        other_course = obj_build.make_course()
        other_admin = obj_build.make_admin_user(other_course)
        image_with_course = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Image 3', tag='tag3', course=self.course
        )
        self.do_permission_denied_get_test(
            self.client, other_admin,
            reverse('sandbox-docker-image-detail', kwargs={'pk': image_with_course.pk}))

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


class InspectRemoteImageOnlyCalledWhenNeededTestCase(_SetUp):
    @mock.patch('autograder.rest_api.serializers.serializer_impls.inspect_remote_image')
    def test_update_image_display_name_not_tag_inspect_remote_image_not_called(
        self, mock_inspect_image
    ) -> None:
        url = reverse('sandbox-docker-image-detail', kwargs={'pk': self.image1.pk})
        self.do_patch_object_test(
            self.image1, self.client, self.superuser, url,
            {'display_name': 'New Display Name', 'tag': self.image1.tag})
        mock_inspect_image.assert_not_called()

        self.do_patch_object_test(
            self.image1, self.client, self.superuser, url,
            {'display_name': 'New Display Name'})
        mock_inspect_image.assert_not_called()


@mock.patch('autograder.rest_api.serializers.serializer_impls.inspect_remote_image',
            new=lambda tag: {'config': {'Entrypoint': None, 'Cmd': ['/bin/bash']}})
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


class ImageConfigValidationTestCase(AGViewTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        ag_models.SandboxDockerImage.objects.exclude(display_name='Default').delete()
        self.superuser = obj_build.make_user(superuser=True)
        self.course = obj_build.make_course()
        self.admin = obj_build.make_admin_user(self.course)

        self.images_for_course_url = reverse(
            'sandbox-docker-images-for-course', kwargs={'pk': self.course.pk})
        self.images_no_course_url = reverse('sandbox-docker-image-list')
        self.default_image = ag_models.SandboxDockerImage.objects.get(display_name='Default')
        self.default_image_url = reverse(
            'sandbox-docker-image-detail', kwargs={'pk': self.default_image.pk})

    def test_valid_image_config(self) -> None:
        self.do_create_object_test(
            ag_models.SandboxDockerImage.objects, self.client, self.superuser,
            self.images_no_course_url,
            {'display_name': 'Default 2', 'tag': 'jameslp/ag-ubuntu-16:1'}
        )

        self.do_create_object_test(
            ag_models.SandboxDockerImage.objects, self.client, self.admin,
            self.images_for_course_url,
            {'display_name': 'I am image', 'tag': 'jameslp/autograder-sandbox:3.1.0'}
        )

        self.do_patch_object_test(
            self.default_image, self.client, self.superuser,
            self.default_image_url,
            {'tag': 'jameslp/autograder-sandbox:3.0.0'}
        )

    def test_invalid_image_entrypoint(self) -> None:
        response = self.do_invalid_create_object_test(
            ag_models.SandboxDockerImage.objects, self.client, self.superuser,
            self.images_no_course_url,
            {'display_name': 'Default 2', 'tag': 'postgres:latest'}
        )
        self.assertIn('ENTRYPOINT', response.data['__all__'][0])

        response = self.do_invalid_create_object_test(
            ag_models.SandboxDockerImage.objects, self.client, self.admin,
            self.images_for_course_url,
            {'display_name': 'I am image', 'tag': 'postgres:latest'}
        )
        self.assertIn('ENTRYPOINT', response.data['__all__'][0])

        response = self.do_patch_object_invalid_args_test(
            self.default_image, self.client, self.superuser,
            self.default_image_url,
            {'tag': 'postgres:latest'}
        )
        self.assertIn('ENTRYPOINT', response.data['__all__'][0])

    def test_invalid_image_cmd(self) -> None:
        response = self.do_invalid_create_object_test(
            ag_models.SandboxDockerImage.objects, self.client, self.superuser,
            self.images_no_course_url,
            {'display_name': 'Default 2', 'tag': 'nginx:latest'}
        )
        self.assertIn('CMD', response.data['__all__'][0])

        response = self.do_invalid_create_object_test(
            ag_models.SandboxDockerImage.objects, self.client, self.admin,
            self.images_for_course_url,
            {'display_name': 'I am image', 'tag': 'nginx:latest'}
        )
        self.assertIn('CMD', response.data['__all__'][0])

        response = self.do_patch_object_invalid_args_test(
            self.default_image, self.client, self.superuser,
            self.default_image_url,
            {'tag': 'nginx:latest'}
        )
        self.assertIn('CMD', response.data['__all__'][0])

    def test_image_not_found(self) -> None:
        response = self.do_invalid_create_object_test(
            ag_models.SandboxDockerImage.objects, self.client, self.superuser,
            self.images_no_course_url,
            {'display_name': 'Default 2', 'tag': 'noooope'}
        )
        self.assertIn('not found', response.data['__all__'][0])

        response = self.do_invalid_create_object_test(
            ag_models.SandboxDockerImage.objects, self.client, self.admin,
            self.images_for_course_url,
            {'display_name': 'I am image', 'tag': 'jameslp/does_not_exist'}
        )
        self.assertIn('not found', response.data['__all__'][0])

        response = self.do_patch_object_invalid_args_test(
            self.default_image, self.client, self.superuser,
            self.default_image_url,
            {'tag': 'jameslp/ag-ubuntu-16:not.a.tag'}
        )
        self.assertIn('not found', response.data['__all__'][0])

    def test_signature_verification_failed_error_handled(self) -> None:
        mock_inspect_image = mock.Mock(side_effect=SignatureVerificationFailedError)
        with mock.patch('autograder.rest_api.serializers.serializer_impls.inspect_remote_image',
                        new=mock_inspect_image):

            response = self.do_patch_object_invalid_args_test(
                self.default_image, self.client, self.superuser,
                self.default_image_url,
                {'tag': 'jameslp/autograder-sandbox:3.0.0'}
            )
            self.assertIn('Temporary error fetching image', response.data['__all__'][0])
