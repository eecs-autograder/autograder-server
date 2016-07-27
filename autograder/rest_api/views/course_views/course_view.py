from rest_framework import viewsets, mixins, permissions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins

from ..load_object_mixin import build_load_object_mixin


class CoursePermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if view.action in ['list', 'create']:
            return request.user.is_superuser

        return True

    def has_object_permission(self, request, view, course):
        if view.action == 'retrieve':
            return True

        return course.is_administrator(request.user)


class CourseViewSet(build_load_object_mixin(ag_models.Course),
                    transaction_mixins.TransactionCreateMixin,
                    transaction_mixins.TransactionUpdateMixin,
                    mixins.RetrieveModelMixin,
                    mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    serializer_class = ag_serializers.CourseSerializer
    permission_classes = (permissions.IsAuthenticated, CoursePermissions,)

    def get_queryset(self):
        return ag_models.Course.objects.all()
