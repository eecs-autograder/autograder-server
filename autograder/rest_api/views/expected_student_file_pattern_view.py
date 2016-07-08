# from django.contrib.auth.models import User

from rest_framework import viewsets, mixins, permissions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from .permission_components import user_can_view_project
# from .permissions import IsAdminOrReadOnlyStaff
# from ..load_object_mixin import build_load_object_mixin


class _Permissions(permissions.BasePermission):
    def has_object_permission(self, request, view, pattern):
        if request.method in permissions.SAFE_METHODS:
            return user_can_view_project(request.user, pattern.project)

        return pattern.project.course.is_administrator(request.user)


class ExpectedStudentFilePatternViewset(mixins.RetrieveModelMixin,
                                        mixins.UpdateModelMixin,
                                        mixins.DestroyModelMixin,
                                        viewsets.GenericViewSet):
    queryset = ag_models.ExpectedStudentFilePattern.objects.all()
    serializer_class = ag_serializers.ExpectedStudentFilePatternSerializer
    permission_classes = (permissions.IsAuthenticated, _Permissions)
