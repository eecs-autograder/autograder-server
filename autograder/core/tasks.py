import json
import signal
import subprocess
import threading
import time
import traceback
import typing
import uuid

import celery
from django.conf import settings
from django.db import transaction

import autograder.core.models as ag_models
from autograder.utils.retry import retry_should_recover


@celery.shared_task(acks_late=True)
def build_sandbox_docker_image(build_task_pk: int):
    @retry_should_recover
    def load_build_task():
        return ag_models.BuildSandboxDockerImageTask.objects.get(pk=build_task_pk)

    try:
        task = load_build_task()

        if task.status == ag_models.BuildImageStatus.cancelled:
            return

        tag = (f'localhost:{settings.SANDBOX_IMAGE_REGISTRY_PORT}'
               f'/build{task.pk}_result{uuid.uuid4().hex}')
        builder = _ImageBuilder(
            build_dir=task.build_dir, output_filename=task.output_filename, tag=tag
        )
        builder.start()
        builder.build_process_started.wait()

        while builder.is_alive():
            time.sleep(1)
            task.refresh_from_db()
            if task.status == ag_models.BuildImageStatus.cancelled:
                builder.cancel()
        builder.join()

        if builder.internal_error is not None:
            _save_internal_error_msg(task, builder.internal_error)
            return

        @retry_should_recover
        def _save_return_code():
            task.return_code = builder.return_code
            task.timed_out = builder.timed_out
            task.save()
        _save_return_code()

        if builder.cancelled or builder.timed_out or builder.return_code != 0:
            return

        assert builder.tag is not None
        if not _validate_image_config(builder.tag, task):
            return

        push_image(builder.tag)

        @retry_should_recover
        @transaction.atomic
        def _create_or_save_image():
            if task.image_to_update is None:
                ag_models.SandboxDockerImage.objects.validate_and_create(
                    course=task.course,
                    display_name=f'New Image {uuid.uuid4().hex}',
                    tag=builder.tag,
                )
            else:
                image = task.image_to_update
                # Make sure we don't overwrite, say, "display_name"
                ag_models.SandboxDockerImage.objects.select_for_update().filter(
                    pk=image.pk
                ).update(tag=builder.tag)

            task.status = ag_models.BuildImageStatus.done
            task.save()

        _create_or_save_image()
    except subprocess.CalledProcessError as e:
        print(traceback.format_exc(), flush=True)
        _save_internal_error_msg(task, traceback.format_exc() + '\n' + e.stdout)
    except Exception:
        print(traceback.format_exc(), flush=True)
        _save_internal_error_msg(task, traceback.format_exc())


# Thin wrapper for mocking the "docker push" step.
def push_image(tag: str):
    _run_and_check_cmd(['docker', 'push', tag])


def _run_and_check_cmd(cmd: typing.List[str]):
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding='utf-8',
        errors='surrogateescape',
        check=True
    )


def _validate_image_config(tag: str, task: ag_models.BuildSandboxDockerImageTask) -> bool:
    inspect_result = _run_and_check_cmd(
        ['docker', 'inspect', '--format', '{{json .Config}}', tag]
    )

    config = json.loads(inspect_result.stdout)

    error_msg = ''
    entrypoint = config['Entrypoint']
    cmd = config['Cmd']
    if entrypoint is not None:
        error_msg += 'Custom images may not use the ENTRYPOINT directive.\n'

    if cmd not in [['/bin/bash'], ['/bin/sh']]:
        error_msg += ('Custom images may not use the CMD directive. '
                      f'Expected ["/bin/bash"] but was "{cmd}".\n')

    if error_msg:
        _save_validation_error_msg(task, error_msg)

    return error_msg == ''


@retry_should_recover
def _save_validation_error_msg(build_task: ag_models.BuildSandboxDockerImageTask, error_msg: str):
    build_task.validation_error_msg = error_msg
    build_task.status = ag_models.BuildImageStatus.image_invalid
    build_task.save()


@retry_should_recover
def _save_internal_error_msg(build_task: ag_models.BuildSandboxDockerImageTask, error_msg: str):
    build_task.internal_error_msg = error_msg
    build_task.status = ag_models.BuildImageStatus.internal_error
    build_task.save()


IMAGE_BUILD_TIMEOUT = 60 * 10


class _ImageBuilder(threading.Thread):
    def __init__(self, *, build_dir: str, output_filename: str, tag: str):
        super().__init__()

        self.build_dir = build_dir
        self.output_filename = output_filename
        self.tag = tag

        self._process = None

        self.cancelled = False
        self.return_code = None
        self.timed_out = False

        self.build_process_started = threading.Event()
        self.internal_error = None

    def run(self):
        try:
            self.build()
        except Exception:
            print(traceback.format_exc(), flush=True)
            # Don't block the main thread if an error occurs early in the build
            self.build_process_started.set()
            self.internal_error = traceback.format_exc()

    def build(self):
        if self.cancelled:
            return

        with open(self.output_filename, 'wb') as output:
            with subprocess.Popen(
                [
                    'docker', 'build',
                    '--no-cache',
                    '--memory', '8GB',
                    '--memory-swap', '8GB',
                    '--ulimit', 'nproc=1000:1000',
                    # Use up to 50% of the CPU(s)
                    '--cpu-period=100000',
                    '--cpu-quota=50000',
                    '-t', self.tag,
                    self.build_dir,
                ],
                stdout=output,
                stderr=subprocess.STDOUT
            ) as process:
                self._process = process
                self.build_process_started.set()
                try:
                    self._process.communicate(None, timeout=IMAGE_BUILD_TIMEOUT)
                    self.return_code = self._process.poll()
                except subprocess.TimeoutExpired:
                    self.timed_out = True
                    self._process.kill()
                    self._process.wait()
                    self.return_code = self._process.poll()
                except:  # noqa
                    self._process.kill()
                    self._process.wait()
                    raise

    @property
    def is_finished(self):
        assert self._process is not None
        return self._process.poll() is not None

    def cancel(self):
        assert self._process is not None
        if self.cancelled or self.is_finished:
            return

        try:
            self._process.terminate()
            self._process.wait(3)
            self.cancelled = True
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()
