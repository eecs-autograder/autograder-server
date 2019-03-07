from django.core import exceptions

import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase


class SandboxDockerImageTestCase(UnitTestBase):
    def test_create_sandbox_docker_image(self):
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            name='Imagey', tag='jameslp/imagey:1')

        self.assertEqual('Imagey', image.name)
        self.assertEqual('jameslp/imagey:1', image.tag)

    def test_create_sandbox_docker_image_error_missing_fields(self):
        with self.assertRaises(exceptions.ValidationError):
            ag_models.SandboxDockerImage.objects.validate_and_create(name='Imagey')

        with self.assertRaises(exceptions.ValidationError):
            ag_models.SandboxDockerImage.objects.validate_and_create(tag='jameslp/imagey:1')

    def test_edit_sandbox_docker_image(self):
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            name='Imagey', tag='jameslp/imagey:1')

        new_name = 'Imagey 2.0'
        new_tag = 'jameslp/imagey:2'

        image.validate_and_update(name=new_name, tag=new_tag)

        image.refresh_from_db()

        self.assertEqual(new_name, image.name)
        self.assertEqual(new_tag, image.tag)

    def test_edit_sandbox_docker_image_error_empty_fields(self):
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            name='Imagey', tag='jameslp/imagey:1')

        with self.assertRaises(exceptions.ValidationError) as cm:
            image.validate_and_update(name='')

        self.assertIn('name', cm.exception.message_dict)

        with self.assertRaises(exceptions.ValidationError) as cm:
            image.validate_and_update(tag='')

        self.assertIn('tag', cm.exception.message_dict)

    def test_serialize_sandbox_docker_image(self):
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            name='Imagey', tag='jameslp/imagey:1')

        serialized = image.to_dict()
        expected = {
            'pk': image.pk,
            'name': image.name,
            'tag': image.tag,
        }

        self.assertEqual(expected, serialized)
