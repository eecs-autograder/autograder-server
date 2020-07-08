import subprocess
import threading
import time
from typing import Optional
from unittest import mock

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

import autograder.core.models as ag_models
from autograder.core.tasks import build_sandbox_docker_image
from autograder.utils.testing import TransactionUnitTestBase, UnitTestBase
import autograder.utils.testing.model_obj_builders as obj_build


_DOCKERFILE = SimpleUploadedFile(
    'Dockerfile',
    b'''FROM jameslp/ag-ubuntu-16:1
RUN echo "Hello World"
    ''',
)


@mock.patch('autograder.core.tasks.push_image')
@mock.patch('autograder.utils.retry.sleep', new=mock.Mock())
class BuildSandboxDockerImageTestCase(UnitTestBase):
    def setUp(self):
        super().setUp()
        self.maxDiff = None

    def test_build_new_default_image(self, push_image_mock) -> None:
        self._do_build_image_test(course=None, image=None)
        push_image_mock.assert_called_once()

    def test_build_new_course_image(self, push_image_mock) -> None:
        self._do_build_image_test(course=obj_build.make_course(), image=None)
        push_image_mock.assert_called_once()

    def test_build_and_update_default_image(self, push_image_mock) -> None:
        self._do_build_image_test(
            course=None,
            image=ag_models.SandboxDockerImage.objects.get(display_name='Default')
        )
        push_image_mock.assert_called_once()

    def test_build_and_update_course_image(self, push_image_mock) -> None:
        course = obj_build.make_course()
        image = obj_build.make_sandbox_docker_image(course)
        self._do_build_image_test(course, image)
        push_image_mock.assert_called_once()

    def _do_build_image_test(
        self, course: Optional[ag_models.Course],
        image: Optional[ag_models.SandboxDockerImage]
    ):
        task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            [_DOCKERFILE], course, image
        )
        build_sandbox_docker_image(task.pk)

        task.refresh_from_db()
        self.assertEqual(ag_models.BuildImageStatus.done, task.status)
        self.assertEqual(0, task.return_code)
        self.assertFalse(task.timed_out)
        self.assertEqual('', task.validation_error_msg)
        self.assertEqual('', task.internal_error_msg)

        with open(task.output_filename) as f:
            output = f.read()
        self.assertNotEqual('', output)
        print(output)

        if image is None:
            image = ag_models.SandboxDockerImage.objects.get(
                display_name__startswith='New Image',
                course=course,
            )
            self.assertEqual(image, task.image)
        else:
            image = ag_models.SandboxDockerImage.objects.get(
                display_name=image.display_name,
                course=image.course,
            )
        self.assertIn(
            f'{settings.SANDBOX_IMAGE_REGISTRY_HOST}:{settings.SANDBOX_IMAGE_REGISTRY_PORT}'
            f'/build{task.pk}_result',
            image.tag
        )

    def test_image_is_invalid_has_cmd(self, push_image_mock) -> None:
        dockerfile_content = '''FROM jameslp/ag-ubuntu-16:1
CMD echo
'''
        self._do_invalid_image_test(dockerfile_content, 'CMD directive')
        push_image_mock.assert_not_called()

    def test_image_is_invalid_has_entrypoint(self, push_image_mock) -> None:
        dockerfile_content = '''FROM jameslp/ag-ubuntu-16:1
ENTRYPOINT echo
'''
        self._do_invalid_image_test(dockerfile_content, 'ENTRYPOINT directive')
        push_image_mock.assert_not_called()

    def test_image_is_invalid_has_cmd_and_entrypoint(self, push_image_mock) -> None:
        dockerfile_content = '''FROM jameslp/ag-ubuntu-16:1
ENTRYPOINT echo
CMD ls
'''
        self._do_invalid_image_test(
            dockerfile_content, 'CMD directive', 'ENTRYPOINT directive')
        push_image_mock.assert_not_called()

    def _do_invalid_image_test(self, dockerfile_content: str, *expected_in_error_msg: str):
        dockerfile = SimpleUploadedFile(
            'Dockerfile',
            dockerfile_content.encode(),
        )
        task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            [dockerfile], None
        )
        build_sandbox_docker_image(task.pk)

        task.refresh_from_db()
        self.assertEqual(ag_models.BuildImageStatus.image_invalid, task.status)
        for item in expected_in_error_msg:
            self.assertIn(item, task.validation_error_msg)

        self.assertFalse(
            ag_models.SandboxDockerImage.objects.filter(
                display_name__startswith='New Image').exists())
        self.assertEqual(task.internal_error_msg, '')

    def test_build_cancelled_before_starting(self, push_image_mock) -> None:
        task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            [_DOCKERFILE], None
        )
        task.status = ag_models.BuildImageStatus.cancelled
        task.save()

        build_sandbox_docker_image(task.pk)

        push_image_mock.assert_not_called()
        self.assertFalse(
            ag_models.SandboxDockerImage.objects.filter(display_name__startswith='New Image'))
        self.assertEqual(task.internal_error_msg, '')

    def test_build_timeout(self, push_image_mock) -> None:
        with mock.patch('autograder.core.tasks.IMAGE_BUILD_TIMEOUT', new=2):
            task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
                [_make_dockerfile_with_sleep(5)], None
            )
            build_sandbox_docker_image(task.pk)

            task.refresh_from_db()
            self.assertEqual(task.internal_error_msg, '')
            with open(task.output_filename) as f:
                print(f.read())
            self.assertTrue(task.timed_out)
            self.assertEqual(ag_models.BuildImageStatus.failed, task.status)

    def test_image_build_failed(self, push_image_mock) -> None:
        dockerfile = SimpleUploadedFile(
            'Dockerfile',
            b'''FROM jameslp/ag-ubuntu-16:1
RUN false
            ''',
        )
        task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            [dockerfile], None
        )
        build_sandbox_docker_image(task.pk)

        task.refresh_from_db()
        self.assertNotEqual(0, task.return_code)
        self.assertIsNotNone(task.return_code)
        self.assertFalse(
            ag_models.SandboxDockerImage.objects.filter(display_name__startswith='New Image'))
        push_image_mock.assert_not_called()
        self.assertEqual(task.internal_error_msg, '')
        self.assertEqual(ag_models.BuildImageStatus.failed, task.status)

    def test_called_process_error_output_recorded(self, push_image_mock) -> None:
        error_text = 'This is an error it is such badness'
        mock_build_method = mock.Mock(side_effect=self._get_called_process_error(error_text))
        with mock.patch('autograder.core.tasks._ImageBuilder.build', new=mock_build_method):
            task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
                [_DOCKERFILE], None
            )
            build_sandbox_docker_image(task.pk)

            push_image_mock.assert_not_called()
            task.refresh_from_db()
            self.assertIn('CalledProcessError', task.internal_error_msg)
            self.assertIn(error_text, task.internal_error_msg)

    def _get_called_process_error(self, error_text: str):
        try:
            subprocess.run(
                ['bash', '-c', f'echo {error_text}; false'], stdout=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError as e:
            return e

    def test_top_level_unexpected_error_handled(self, push_image_mock) -> None:
        mock_build_method = mock.Mock(side_effect=RuntimeError('I am errorrrr'))
        with mock.patch('autograder.core.tasks._ImageBuilder.build', new=mock_build_method):
            task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
                [_DOCKERFILE], None
            )
            build_sandbox_docker_image(task.pk)

            push_image_mock.assert_not_called()
            task.refresh_from_db()
            self.assertIn('RuntimeError', task.internal_error_msg)
            self.assertIn('I am error', task.internal_error_msg)


@mock.patch('autograder.core.tasks.push_image')
@mock.patch('autograder.utils.retry.sleep', new=mock.Mock())
class CancelBuildSandboxDockerImageTestCase(TransactionUnitTestBase):
    def test_build_cancelled_after_starting(self, push_image_mock) -> None:
        task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            [_make_dockerfile_with_sleep(60)], None
        )
        build_thread = threading.Thread(target=build_sandbox_docker_image, args=(task.pk,))
        build_thread.start()

        time.sleep(3)
        task.status = ag_models.BuildImageStatus.cancelled
        task.save()

        build_thread.join(5)
        self.assertFalse(build_thread.is_alive())

        push_image_mock.assert_not_called()
        self.assertFalse(
            ag_models.SandboxDockerImage.objects.filter(display_name__startswith='New Image'))

        task.refresh_from_db()
        self.assertEqual(ag_models.BuildImageStatus.cancelled, task.status)


def _make_dockerfile_with_sleep(sleep_time: int):
    return SimpleUploadedFile(
        'Dockerfile',
        f'''FROM jameslp/ag-ubuntu-16:1
RUN sleep {sleep_time}
        '''.encode(),
    )
