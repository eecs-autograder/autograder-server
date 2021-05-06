import os

from django.conf import settings
from django.core import exceptions
from django.core.files.uploadedfile import SimpleUploadedFile

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
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
        image.validate_and_update(display_name=new_display_name)

        image.refresh_from_db()
        self.assertEqual(new_display_name, image.display_name)

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

    def test_serialize_sandbox_docker_image(self):
        course = obj_build.make_course()
        image = ag_models.SandboxDockerImage.objects.validate_and_create(
            course=course, display_name='Supar Image', tag='jameslp/imagey:1')

        serialized = image.to_dict()
        expected = {
            'pk': image.pk,
            'course': image.course.pk,
            'display_name': image.display_name,
            'last_modified': image.last_modified,
        }

        self.assertEqual(expected, serialized)


class BuildSandboxDockerImageTaskTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.course = obj_build.make_course()

    def test_create_build_task(self) -> None:
        files = [
            SimpleUploadedFile('spam.sh', b'blah'),
            SimpleUploadedFile('Dockerfile', b'blee'),
            SimpleUploadedFile('sausage.sh', b'bloo'),
        ]
        task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(files, None)

        loaded = ag_models.BuildSandboxDockerImageTask.objects.get(pk=task.pk)
        self.assertEqual(ag_models.BuildImageStatus.queued, loaded.status)
        self.assertIsNone(loaded.return_code)
        self.assertFalse(loaded.timed_out)
        self.assertEqual(['spam.sh', 'Dockerfile', 'sausage.sh'], loaded.filenames)
        self.assertIsNone(loaded.course)
        self.assertIsNone(loaded.image)
        self.assertEqual('', loaded.internal_error_msg)

        for file_ in files:
            file_.seek(0)
            path = os.path.join(loaded.build_dir, file_.name)
            with open(path, 'rb') as f:
                self.assertEqual(file_.read(), f.read())

    def test_create_build_task_course_none_image_to_update_has_no_course(self) -> None:
        image_to_update = obj_build.make_sandbox_docker_image()
        task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            files=[
                SimpleUploadedFile('Dockerfile', b'blee'),
            ],
            course=None,
            image=image_to_update
        )
        loaded = ag_models.BuildSandboxDockerImageTask.objects.get(pk=task.pk)
        self.assertEqual(ag_models.BuildImageStatus.queued, loaded.status)
        self.assertEqual(['Dockerfile'], loaded.filenames)
        self.assertIsNone(loaded.course)
        self.assertEqual(image_to_update, loaded.image)

    def test_create_build_task_course_and_image_to_update_not_none(self) -> None:
        image_to_update = obj_build.make_sandbox_docker_image(self.course)
        task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            files=[
                SimpleUploadedFile('Dockerfile', b'blee'),
            ],
            course=self.course,
            image=image_to_update
        )
        loaded = ag_models.BuildSandboxDockerImageTask.objects.get(pk=task.pk)
        self.assertEqual(ag_models.BuildImageStatus.queued, loaded.status)
        self.assertEqual(['Dockerfile'], loaded.filenames)
        self.assertEqual(self.course, loaded.course)
        self.assertEqual(image_to_update, loaded.image)

    def test_image_to_update_has_finished_build_task(self) -> None:
        image_to_update = obj_build.make_sandbox_docker_image()
        task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            files=[SimpleUploadedFile('Dockerfile', b'')],
            course=None,
            image=image_to_update
        )
        done_statuses = [
            ag_models.BuildImageStatus.done,
            ag_models.BuildImageStatus.failed,
            ag_models.BuildImageStatus.image_invalid,
            ag_models.BuildImageStatus.internal_error,
            ag_models.BuildImageStatus.cancelled
        ]
        for status in done_statuses:
            task.status = status
            task.save()
            new_task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
                files=[SimpleUploadedFile('Dockerfile', b'')],
                course=None,
                image=image_to_update,
            )
            new_task.delete()

    def test_error_image_to_update_has_unfinished_build_task(self) -> None:
        image_to_update = obj_build.make_sandbox_docker_image()
        task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            files=[SimpleUploadedFile('Dockerfile', b'')],
            course=None,
            image=image_to_update
        )

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
                files=[SimpleUploadedFile('Dockerfile', b'')],
                course=None,
                image=image_to_update,
            )
        self.assertIn('image', cm.exception.message_dict)

        task.status = ag_models.BuildImageStatus.in_progress
        task.save()

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
                files=[SimpleUploadedFile('Dockerfile', b'')],
                course=None,
                image=image_to_update,
            )
        self.assertIn('image', cm.exception.message_dict)

    def test_task_output_filename_with_course(self) -> None:
        task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            files=[
                SimpleUploadedFile('Dockerfile', b'blee'),
            ],
            course=self.course,
        )
        expected = os.path.join(
            settings.MEDIA_ROOT,
            'image_builds',
            f'course{self.course.pk}',
            f'task{task.pk}',
            f'__build{task.pk}_output'
        )
        self.assertEqual(expected, task.output_filename)

    def test_task_output_filename_no_course(self) -> None:
        task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            files=[
                SimpleUploadedFile('Dockerfile', b'blee'),
            ],
            course=None,
        )
        expected = os.path.join(
            settings.MEDIA_ROOT,
            'image_builds',
            f'task{task.pk}',
            f'__build{task.pk}_output'
        )
        self.assertEqual(expected, task.output_filename)

    def test_error_image_to_update_from_different_course(self) -> None:
        other_course = obj_build.make_course()
        image_to_update = obj_build.make_sandbox_docker_image(other_course)

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
                files=[SimpleUploadedFile('Dockerfile', b'hi')],
                course=self.course,
                image=image_to_update,
            )
        self.assertIn('image', cm.exception.message_dict)

    def test_error_image_to_update_has_no_course_and_course_not_null(self) -> None:
        other_course = obj_build.make_course()
        image_to_update = obj_build.make_sandbox_docker_image()

        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
                files=[SimpleUploadedFile('Dockerfile', b'hi')],
                course=self.course,
                image=image_to_update,
            )
        self.assertIn('image', cm.exception.message_dict)

    def test_error_no_dockerfile(self) -> None:
        with self.assertRaises(exceptions.ValidationError) as cm:
            ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
                files=[],
                course=self.course,
            )
        self.assertIn('files', cm.exception.message_dict)
        self.assertIn('Dockerfile', cm.exception.message_dict['files'][0])

    def test_build_tasks_deleted_on_image_delete(self) -> None:
        image_to_update = obj_build.make_sandbox_docker_image(self.course)
        task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            files=[
                SimpleUploadedFile('Dockerfile', b'blee'),
            ],
            course=self.course,
            image=image_to_update
        )

        image_to_update.delete()
        with self.assertRaises(exceptions.ObjectDoesNotExist):
            task.refresh_from_db()

    def test_serialize_build_task(self):
        image_to_update = obj_build.make_sandbox_docker_image(self.course)
        task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            files=[
                SimpleUploadedFile('Dockerfile', b'blee'),
            ],
            course=self.course,
            image=image_to_update
        )

        serialized = task.to_dict()
        expected = {
            'pk': task.pk,
            'created_at': task.created_at,
            'status': task.status.value,
            'return_code': task.return_code,
            'timed_out': task.timed_out,
            'filenames': task.filenames,
            'course_id': self.course.pk,
            'image': image_to_update.to_dict(),
            'validation_error_msg': '',
            'internal_error_msg': '',
            'last_modified': task.last_modified,
        }

        self.assertEqual(expected, serialized)
