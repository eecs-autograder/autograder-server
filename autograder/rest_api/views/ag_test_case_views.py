from rest_framework import viewsets, mixins, permissions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from .permission_components import is_admin_or_read_only_staff
from .load_object_mixin import build_load_object_mixin


class _Permissions(permissions.BasePermission):
    def has_object_permission(self, request, view, ag_test):
        return is_admin_or_read_only_staff(request, ag_test.project.course)


class AGTestCaseViewset(
        build_load_object_mixin(ag_models.AutograderTestCaseBase),
        mixins.RetrieveModelMixin,
        mixins.UpdateModelMixin,
        mixins.DestroyModelMixin,
        viewsets.GenericViewSet):
    serializer_class = ag_serializers.AGTestCaseSerializer
    permission_classes = (permissions.IsAuthenticated, _Permissions)
    queryset = ag_models.AutograderTestCaseBase.objects.all()
