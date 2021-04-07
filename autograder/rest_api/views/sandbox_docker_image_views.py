import tempfile
import zipfile

from django.db import transaction
from drf_composable_permissions.p import P
from rest_framework import exceptions, permissions, response, status

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
from autograder import utils
from autograder.core.tasks import build_sandbox_docker_image
from autograder.rest_api.schema import (
    AGDetailViewSchemaGenerator, APITags, CustomViewMethodData, CustomViewSchema,
    as_array_content_obj, as_content_obj, as_schema_ref
)
from autograder.rest_api.serve_file import serve_file
from autograder.rest_api.size_file_response import SizeFileResponse
from autograder.rest_api.views.ag_model_views import convert_django_validation_error

from . import ag_model_views as ag_views


class IsAdminForAnyCourse(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.courses_is_admin_for.count() > 0


def _make_build_image_schema(operation_id: str) -> CustomViewMethodData:
    result: CustomViewMethodData = {'operation_id': operation_id}
    result.update(_BUILD_IMAGE_SCHEMA)
    return result


_BUILD_IMAGE_SCHEMA: CustomViewMethodData = {
    'request': {
        'content': {
            'multipart/form-data': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'files': {
                            'description': (
                                'The form-encoded files. One file must be named "Dockerfile"'),
                            'type': 'array',
                            'items': {
                                'type': 'string',
                                'format': 'binary',
                            },
                        }
                    }
                }
            }
        }
    },
    'responses': {
        '202': {
            'content': as_content_obj(ag_models.BuildSandboxDockerImageTask),
            'description': 'The build task has been started.'
        }
    }
}


class ListCreateGlobalSandboxDockerImageView(ag_views.AGModelAPIView):
    schema = CustomViewSchema(
        [APITags.sandbox_docker_images],
        api_class=ag_models.SandboxDockerImage,
        data={
            'GET': {
                'operation_id': 'listGlobalSandboxDockerImages',
                'responses': {
                    '200': {
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'array',
                                    'items': as_schema_ref(ag_models.SandboxDockerImage)
                                }
                            }
                        },
                        'description': ''
                    }
                }
            },
            'POST': _make_build_image_schema('createGlobalSandboxDockerImage')
        }
    )

    permission_classes = [
        P(ag_permissions.IsSuperuser) | (P(ag_permissions.IsReadOnly) & P(IsAdminForAnyCourse))
    ]

    def get(self, *args, **kwargs):
        """
        Lists all global sandbox images (ones that don't belong to a course).
        """
        return response.Response([
            image.to_dict() for image in
            ag_models.SandboxDockerImage.objects.filter(course=None)
        ])

    @convert_django_validation_error
    def post(self, request, *args, **kwargs):
        """
        Build a new global sandbox image.
        """
        build_task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            request.data.getlist('files'), None
        )

        return _start_build_task(build_task)


class ListCreateSandboxDockerImageForCourseView(ag_views.NestedModelView):
    schema = CustomViewSchema([APITags.sandbox_docker_images], {
        'GET': {
            'operation_id': 'listSandboxDockerImagesForCourse',
            'responses': {
                '200': {
                    'content': as_array_content_obj(ag_models.SandboxDockerImage),
                    'description': ''
                }
            }
        },
        'POST': _make_build_image_schema('createSandboxDockerImageForCourse')
    }
    )
    permission_classes = [ag_permissions.is_admin()]

    model_manager = ag_models.Course.objects
    nested_field_name = 'sandbox_docker_images'
    parent_obj_field_name = 'course'

    def get(self, *args, **kwargs):
        return self.do_list()

    @convert_django_validation_error
    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            course = self.get_object()
            build_task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
                request.data.getlist('files'), course
            )

        return _start_build_task(build_task)


class ListGlobalBuildTasksView(ag_views.AGModelAPIView):
    schema = CustomViewSchema([APITags.sandbox_docker_images], {
        'GET': {
            'operation_id': 'listGlobalBuildSandboxDockerImageTasks',
            'responses': {
                '200': {
                    'content': as_array_content_obj(ag_models.BuildSandboxDockerImageTask),
                    'description': ''
                }
            }
        }
    })
    permission_classes = [ag_permissions.IsSuperuser]

    def get(self, *args, **kwargs):
        """
        List all global (not belonging to a course) image build tasks.
        """
        return response.Response([
            task.to_dict() for task in
            ag_models.BuildSandboxDockerImageTask.objects.filter(course=None)
        ])


class ListBuildTasksForCourseView(ag_views.NestedModelView):
    schema = CustomViewSchema([APITags.sandbox_docker_images], {
        'GET': {
            'operation_id': 'listBuildSandboxDockerImageTasksForCourse',
            'responses': {
                '200': {
                    'content': as_array_content_obj(ag_models.BuildSandboxDockerImageTask),
                    'description': ''
                }
            }
        }
    })

    permission_classes = [ag_permissions.is_admin()]
    model_manager = ag_models.Course.objects
    nested_field_name = 'build_sandbox_docker_image_tasks'
    parent_obj_field_name = 'course'

    def get(self, *args, **kwargs):
        """
        List all image build tasks for the specified course.
        """
        return self.do_list()


class ImageBuildTaskDetailPermissions(permissions.BasePermission):
    def has_object_permission(
        self, request, view, obj: ag_models.BuildSandboxDockerImageTask
    ) -> bool:
        if obj.course is not None:
            return obj.course.is_admin(request.user)

        return request.user.is_superuser


class BuildTaskDetailView(ag_views.AGModelDetailView):
    schema = AGDetailViewSchemaGenerator([APITags.sandbox_docker_images])

    permission_classes = [ImageBuildTaskDetailPermissions]
    model_manager = ag_models.BuildSandboxDockerImageTask.objects

    def get(self, *args, **kwargs):
        return self.do_get()


class BuildTaskOutputView(ag_views.AGModelAPIView):
    schema = CustomViewSchema([APITags.sandbox_docker_images], {
        'GET': {
            'operation_id': 'getBuildSandboxDockerImageTaskOutput',
            'responses': {
                '200': {
                    'content': {
                        'application/octet-stream': {
                            'schema': {'type': 'string', 'format': 'binary'}
                        }
                    },
                    'description': ''
                }
            }
        }
    })

    permission_classes = [ImageBuildTaskDetailPermissions]
    model_manager = ag_models.BuildSandboxDockerImageTask.objects

    def get(self, *args, **kwargs):
        task = self.get_object()
        return serve_file(task.output_filename)


class CancelBuildTaskView(ag_views.AGModelAPIView):
    schema = CustomViewSchema([APITags.sandbox_docker_images], {
        'POST': {
            'operation_id': 'cancelBuildSandboxDockerImageTask',
            'responses': {
                '200': {
                    'content': as_content_obj(ag_models.BuildSandboxDockerImageTask),
                    'description': ''
                }
            }
        }
    })

    permission_classes = [ImageBuildTaskDetailPermissions]
    model_manager = ag_models.BuildSandboxDockerImageTask.objects

    @transaction.atomic
    def post(self, *args, **kwargs):
        task = self.get_object()

        if task.status not in (ag_models.BuildImageStatus.queued,
                               ag_models.BuildImageStatus.in_progress):
            raise exceptions.ValidationError(
                'This image is finished processing and cannot be cancelled'
            )

        task.status = ag_models.BuildImageStatus.cancelled
        task.save()
        return response.Response(task.to_dict(), status.HTTP_200_OK)


class DownloadBuildTaskFilesView(ag_views.AGModelAPIView):
    schema = CustomViewSchema([APITags.sandbox_docker_images], {
        'GET': {
            'operation_id': 'getBuildSandboxDockerImageTaskFiles',
            'responses': {
                '200': {
                    'content': {
                        'application/zip': {
                            'schema': {
                                'type': 'string',
                                'format': 'binary',
                            }
                        }
                    },
                    'description': 'A zip archive of the files included in the build.'
                }
            }
        }
    })

    permission_classes = [ImageBuildTaskDetailPermissions]
    model_manager = ag_models.BuildSandboxDockerImageTask.objects

    def get(self, *args, **kwargs):
        task = self.get_object()

        archive = tempfile.NamedTemporaryFile()
        with zipfile.ZipFile(archive, 'w') as z:
            with utils.ChangeDirectory(task.build_dir):
                for filename in task.filenames:
                    z.write(filename)

        archive.seek(0)
        return SizeFileResponse(archive)


class SandboxDockerImageDetailPermissions(permissions.BasePermission):
    def has_object_permission(
        self, request, view, obj: ag_models.SandboxDockerImage
    ) -> bool:
        if request.user.is_superuser:
            return True

        if obj.course is None:
            if request.method.lower() == 'get':
                return request.user.courses_is_admin_for.count() > 0

            return request.user.is_superuser

        return obj.course.is_admin(request.user)


class SandboxDockerImageDetailView(ag_views.AGModelDetailView):
    schema = AGDetailViewSchemaGenerator([APITags.sandbox_docker_images])

    permission_classes = [SandboxDockerImageDetailPermissions]
    model_manager = ag_models.SandboxDockerImage.objects

    def get(self, *args, **kwargs):
        return self.do_get()

    def patch(self, *args, **kwargs):
        return self.do_patch()

    @transaction.atomic
    def delete(self, *args, **kwargs):
        image = self.get_object()
        if image.display_name == 'Default':
            return response.Response(
                status=status.HTTP_400_BAD_REQUEST,
                data='You may not delete the default image.')

        image.delete()
        return response.Response(status=status.HTTP_204_NO_CONTENT)


class RebuildSandboxDockerImageView(ag_views.AGModelAPIView):
    schema = CustomViewSchema([APITags.sandbox_docker_images], {
        'PUT': _make_build_image_schema('rebuildSandboxDockerImage')
    })

    permission_classes = [SandboxDockerImageDetailPermissions]
    model_manager = ag_models.SandboxDockerImage.objects

    @convert_django_validation_error
    def put(self, request, *args, **kwargs):
        """
        Rebuild the specified image using the files uploaded.
        """
        with transaction.atomic():
            image_to_update = self.get_object()
            build_task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
                request.data.getlist('files'), image_to_update.course, image_to_update
            )

        return _start_build_task(build_task)


def _start_build_task(build_task: ag_models.BuildSandboxDockerImageTask) -> response.Response:
    from autograder.celery import app
    build_sandbox_docker_image.apply_async((build_task.pk,), connection=app.connection())

    return response.Response(data=build_task.to_dict(), status=status.HTTP_202_ACCEPTED)
