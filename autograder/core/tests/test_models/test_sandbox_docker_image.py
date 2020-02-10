from django.core import exceptions

import autograder.core.models as ag_models
from autograder.utils.testing import UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


class SandboxDockerImageTestCase(UnitTestBase):
    def test_create_sandbox_docker_images_same_display_name_different_courses(self):
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Imagey', tag='jameslp/imagey:1')

        self.assertEqual('Imagey', image.display_name)
        self.assertEqual('jameslp/imagey:1', image.tag)
        self.assertIsNone(image.course)

        course = obj_build.make_course()

        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            course=course,
            display_name='Imagey',
            tag='jameslp/an_image:1')
        image.refresh_from_db()

        self.assertEqual('Imagey', image.display_name)
        self.assertEqual('jameslp/an_image:1', image.tag)
        self.assertEqual(course, image.course)

    def test_create_error_same_display_name_no_course(self) -> None:
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Imagey', tag='jameslp/imagey:1')

        with self.assertRaises(exceptions.ValidationError):
            ag_models.SandboxDockerImage.objects.validate_and_create(
                display_name=image.display_name, tag='jameslp/an_image:2')

    def test_create_error_same_display_name_same_course(self) -> None:
        course = obj_build.make_course()
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Imagey', tag='jameslp/imagey:1', course=course)

        with self.assertRaises(exceptions.ValidationError):
            ag_models.SandboxDockerImage.objects.validate_and_create(
                display_name=image.display_name, tag='jameslp/an_image:2', course=course)

    def test_create_sandbox_docker_image_error_missing_fields(self):
        with self.assertRaises(exceptions.ValidationError):
            ag_models.SandboxDockerImage.objects.validate_and_create(display_name='Spam')

        with self.assertRaises(exceptions.ValidationError):
            ag_models.SandboxDockerImage.objects.validate_and_create(tag='jameslp/imagey:1')

    def test_edit_sandbox_docker_image(self):
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='An Image', tag='jameslp/imagey:1')

        new_display_name = 'Very Image'
        new_tag = 'jameslp/imagey:2'

        image.validate_and_update(display_name=new_display_name, tag=new_tag)

        image.refresh_from_db()

        self.assertEqual(new_display_name, image.display_name)
        self.assertEqual(new_tag, image.tag)

    # Note: The name field will be removed eventually.
    def test_name_not_editable(self):
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            name='imaaage', display_name='Wee', tag='jameslp/imagey:1')

        with self.assertRaises(exceptions.ValidationError) as cm:
            image.validate_and_update(name='new_name')

        self.assertEqual(['name'], cm.exception.message_dict['non_editable_fields'])

    def course_not_editable(self):
        course = obj_build.make_course()
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            course=course,
            display_name='Wee',
            tag='jameslp/imagey:1')

        with self.assertRaises(exceptions.ValidationError) as cm:
            image.validate_and_update(course=None)

        self.assertEqual(['course'], cm.exception.message_dict['non_editable_fields'])

    def test_edit_sandbox_docker_image_error_empty_fields(self):
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            display_name='Wee', tag='jameslp/imagey:1')

        with self.assertRaises(exceptions.ValidationError) as cm:
            image.validate_and_update(display_name='')

        self.assertIn('display_name', cm.exception.message_dict)

        with self.assertRaises(exceptions.ValidationError) as cm:
            image.validate_and_update(tag='')

        self.assertIn('tag', cm.exception.message_dict)

    def test_serialize_sandbox_docker_image(self):
        course = obj_build.make_course()
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            course=course, display_name='Supar Image', tag='jameslp/imagey:1')

        serialized = image.to_dict()
        expected = {
            'pk': image.pk,
            'course': image.course.pk,
            'display_name': image.display_name,
            'tag': image.tag,
            'validation_warning': '',
        }

        self.assertEqual(expected, serialized)
