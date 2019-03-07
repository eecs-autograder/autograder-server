from drf_composable_permissions.p import P
from rest_framework import mixins, permissions
from rest_framework.permissions import BasePermission

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins
from autograder.rest_api.views.ag_model_views import AGModelGenericViewSet
from autograder.rest_api.views.schema_generation import APITags


class IsAdminForAnyCourse(BasePermission):
    def has_permission(self, request, view):
        return request.user.courses_is_admin_for.count() > 0

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


is_superuser_or_readonly_admin_for_any_course = (
    P(ag_permissions.IsSuperuser) | (P(ag_permissions.IsReadOnly) & P(IsAdminForAnyCourse))
)


class SandboxDockerImageViewSet(mixins.ListModelMixin,
                                mixins.RetrieveModelMixin,
                                transaction_mixins.TransactionPartialUpdateMixin,
                                transaction_mixins.TransactionCreateMixin,
                                AGModelGenericViewSet):
    serializer_class = ag_serializers.SandboxDockerImageSerializer
    permission_classes = (
        permissions.IsAuthenticated, is_superuser_or_readonly_admin_for_any_course
    )

    model_manager = ag_models.SandboxDockerImage.objects

    api_tags = [APITags.ag_test_suites]

    def get_queryset(self):
        return ag_models.SandboxDockerImage.objects.all()
