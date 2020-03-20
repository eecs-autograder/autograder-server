from django.db import transaction
from drf_composable_permissions.p import P
from rest_framework import mixins, permissions, decorators, response, status, exceptions

import autograder.core.models as ag_models
from autograder.core.tasks import build_sandbox_docker_image
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins
from autograder.rest_api.views.schema_generation import APITags

from . import ag_model_views as ag_views


class IsAdminForAnyCourse(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.courses_is_admin_for.count() > 0


class GlobalSandboxDockerImageViews(mixins.ListModelMixin, ag_views.AGModelGenericViewSet):
    serializer_class = ag_serializers.SandboxDockerImageSerializer
    permission_classes = (
        P(ag_permissions.IsSuperuser) | (P(ag_permissions.IsReadOnly) & P(IsAdminForAnyCourse)),
    )

    api_tags = [APITags.sandbox_docker_images]

    def get_queryset(self):
        return ag_models.SandboxDockerImage.objects.filter(course=None)

    def post(self, request, *args, **kwargs):
        build_task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            request.data.getlist('files'), None
        )

        return _start_build_task(build_task)

    @classmethod
    def as_view(cls, actions=None, **initkwargs):
        return super().as_view(actions={'get': 'list'}, **initkwargs)


class SandboxDockerImageForCourseViews(ag_views.ListNestedModelViewSet):
    serializer_class = ag_serializers.SandboxDockerImageSerializer
    permission_classes = (ag_permissions.is_admin(),)

    model_manager = ag_models.Course.objects
    to_one_field_name = 'course'
    reverse_to_one_field_name = 'sandbox_docker_images'

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        course = self.get_object()
        build_task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            request.data.getlist('files'), course
        )

        return _start_build_task(build_task)


class ListGlobalBuildTasksView(mixins.ListModelMixin, ag_views.AGModelGenericViewSet):
    permission_classes = (ag_permissions.IsSuperuser,)
    serializer_class = ag_serializers.BuildSandboxDockerImageTaskSerializer

    api_tags = [APITags.sandbox_docker_images]

    def get_queryset(self):
        return ag_models.BuildSandboxDockerImageTask.objects.filter(course=None)

    @classmethod
    def as_view(cls, actions=None, **initkwargs):
        return super().as_view(actions={'get': 'list'}, **initkwargs)


class ListBuildTasksForCourseView(ag_views.ListNestedModelViewSet):
    serializer_class = ag_serializers.BuildSandboxDockerImageTaskSerializer
    permission_classes = (ag_permissions.is_admin(),)

    model_manager = ag_models.Course.objects
    to_one_field_name = 'course'
    reverse_to_one_field_name = 'build_sandbox_docker_image_tasks'


class ImageBuildTaskDetailPermissions(permissions.BasePermission):
    def has_object_permission(
        self, request, view, obj: ag_models.BuildSandboxDockerImageTask
    ) -> bool:
        if obj.course is not None:
            return obj.course.is_admin(request.user)

        return request.user.is_superuser


class BuildTaskDetailViews(mixins.RetrieveModelMixin, ag_views.AGModelGenericViewSet):
    serializer_class = ag_serializers.BuildSandboxDockerImageTaskSerializer
    permission_classes = (
        ImageBuildTaskDetailPermissions,
    )

    model_manager = ag_models.BuildSandboxDockerImageTask.objects

    api_tags = [APITags.sandbox_docker_images]

    @decorators.detail_route(methods=['POST'])
    @transaction.atomic
    def cancel(self, *args, **kwargs):
        task = self.get_object()

        if task.status not in (ag_models.BuildImageStatus.queued,
                               ag_models.BuildImageStatus.in_progress):
            raise exceptions.ValidationError(
                'This image is finished processing and cannot be cancelled'
            )

        task.status = ag_models.BuildImageStatus.cancelled
        task.save()
        return response.Response(task.to_dict(), status.HTTP_200_OK)


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


class SandboxDockerImageDetailViewSet(mixins.RetrieveModelMixin,
                                      transaction_mixins.TransactionPartialUpdateMixin,
                                      ag_views.AGModelGenericViewSet):
    serializer_class = ag_serializers.SandboxDockerImageSerializer
    permission_classes = (
        SandboxDockerImageDetailPermissions,
    )

    model_manager = ag_models.SandboxDockerImage.objects

    api_tags = [APITags.sandbox_docker_images]

    @decorators.detail_route(methods=['PUT'])
    @transaction.atomic
    def rebuild(self, request, *args, **kwargs):
        image_to_update = self.get_object()
        build_task = ag_models.BuildSandboxDockerImageTask.objects.validate_and_create(
            request.data.getlist('files'), image_to_update.course, image_to_update
        )

        return _start_build_task(build_task)


def _start_build_task(build_task: ag_models.BuildSandboxDockerImageTask) -> response.Response:
    from autograder.celery import app
    build_sandbox_docker_image.apply_async((build_task.pk,), connection=app.connection())

    return response.Response(data=build_task.to_dict(), status=status.HTTP_202_ACCEPTED)
