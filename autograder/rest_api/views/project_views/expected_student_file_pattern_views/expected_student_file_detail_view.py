from rest_framework import viewsets, mixins, permissions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins
from autograder.rest_api.views.load_object_mixin import build_load_object_mixin
from autograder.rest_api.views.permission_components import user_can_view_project


class _Permissions(permissions.BasePermission):
    def has_object_permission(self, request, view, pattern):
        if request.method in permissions.SAFE_METHODS:
            return user_can_view_project(request.user, pattern.project)

        return pattern.project.course.is_admin(request.user)


class ExpectedStudentFilePatternDetailViewSet(
        build_load_object_mixin(ag_models.ExpectedStudentFile),
        mixins.RetrieveModelMixin,
        transaction_mixins.TransactionPartialUpdateMixin,
        transaction_mixins.TransactionDestroyMixin,
        viewsets.GenericViewSet):
    queryset = ag_models.ExpectedStudentFile.objects.all()
    serializer_class = ag_serializers.ExpectedStudentFilePatternSerializer
    permission_classes = (permissions.IsAuthenticated, _Permissions)
