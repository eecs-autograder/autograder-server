from drf_composable_permissions.p import P
from rest_framework import mixins, permissions

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins
from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, ListCreateNestedModelViewSet)
from autograder.rest_api.views.schema_generation import APITags


class ListCreateCourselessDockerImagePermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

        if request.method.lower() == 'get':
            return request.user.courses_is_admin_for.count() > 0

        return False


class ListCreateSandboxDockerImageViewSet(mixins.ListModelMixin,
                                          transaction_mixins.TransactionCreateMixin,
                                          AGModelGenericViewSet):
    serializer_class = ag_serializers.SandboxDockerImageSerializer
    permission_classes = (
        ListCreateCourselessDockerImagePermissions,
    )

    api_tags = [APITags.sandbox_docker_images]

    def get_queryset(self):
        return ag_models.SandboxDockerImage.objects.filter(course=None)


class SandboxDockerImagePermissions(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        if obj.course is None:
            if request.method.lower() == 'get':
                return request.user.courses_is_admin_for.count() > 0

            return request.user.is_superuser

        return obj.course.is_admin(request.user)


class SandboxDockerImageDetailViewSet(mixins.RetrieveModelMixin,
                                      transaction_mixins.TransactionPartialUpdateMixin,
                                      transaction_mixins.TransactionCreateMixin,
                                      AGModelGenericViewSet):
    serializer_class = ag_serializers.SandboxDockerImageSerializer
    permission_classes = (
        SandboxDockerImagePermissions,
    )

    model_manager = ag_models.SandboxDockerImage.objects

    api_tags = [APITags.sandbox_docker_images]


class SandboxDockerImageForCourseViewSet(ListCreateNestedModelViewSet):
    serializer_class = ag_serializers.SandboxDockerImageSerializer
    permission_classes = (ag_permissions.is_admin(),)

    model_manager = ag_models.Course.objects
    to_one_field_name = 'course'
    reverse_to_one_field_name = 'sandbox_docker_images'
