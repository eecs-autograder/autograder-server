from django.core import exceptions

import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase


class SandboxDockerImageTestCase(UnitTestBase):
    def test_create_sandbox_docker_image(self):
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            name='imagey', display_name='Imagey', tag='jameslp/imagey:1')

        self.assertEqual('imagey', image.name)
        self.assertEqual('Imagey', image.display_name)
        self.assertEqual('jameslp/imagey:1', image.tag)

    def test_create_sandbox_docker_image_error_missing_fields(self):
        with self.assertRaises(exceptions.ValidationError):
            ag_models.SandboxDockerImage.objects.validate_and_create(
                name='image', display_name='Spam')

        with self.assertRaises(exceptions.ValidationError):
            ag_models.SandboxDockerImage.objects.validate_and_create(
                name='image', tag='jameslp/imagey:1')

        with self.assertRaises(exceptions.ValidationError):
            ag_models.SandboxDockerImage.objects.validate_and_create(
                display_name='Egg', tag='jameslp/imagey:1')

    def test_edit_sandbox_docker_image(self):
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            name='an_image', display_name='An Image', tag='jameslp/imagey:1')

        new_display_name = 'Very Image'
        new_tag = 'jameslp/imagey:2'

        image.validate_and_update(display_name=new_display_name, tag=new_tag)

        image.refresh_from_db()

        self.assertEqual('an_image', image.name)
        self.assertEqual(new_display_name, image.display_name)
        self.assertEqual(new_tag, image.tag)

    def test_name_not_editable(self):
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            name='imaaage', display_name='Wee', tag='jameslp/imagey:1')

        with self.assertRaises(exceptions.ValidationError) as cm:
            image.validate_and_update(name='new_name')

        self.assertEqual(['name'], cm.exception.message_dict['non_editable_fields'])

    def test_edit_sandbox_docker_image_error_empty_fields(self):
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            name='imaaage', display_name='Wee', tag='jameslp/imagey:1')

        with self.assertRaises(exceptions.ValidationError) as cm:
            image.validate_and_update(display_name='')

        self.assertIn('display_name', cm.exception.message_dict)

        with self.assertRaises(exceptions.ValidationError) as cm:
            image.validate_and_update(tag='')

        self.assertIn('tag', cm.exception.message_dict)

    def test_serialize_sandbox_docker_image(self):
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            name='super_image', display_name='Supar Image', tag='jameslp/imagey:1')

        serialized = image.to_dict()
        expected = {
            'pk': image.pk,
            'name': image.name,
            'display_name': image.display_name,
            'tag': image.tag,
        }

        self.assertEqual(expected, serialized)
