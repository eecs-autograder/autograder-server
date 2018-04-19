from rest_framework import viewsets, mixins, permissions, decorators, response, status
from django.contrib.auth.models import User
from django.db import transaction

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins
import autograder.rest_api.permissions as ag_permissions
from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, TransactionRetrieveUpdateDestroyMixin)

from ..load_object_mixin import build_load_object_mixin


class CoursePermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if view.action in ['list', 'create']:
            return request.user.is_superuser

        return True

    def has_object_permission(self, request, view, course):
        if view.action == 'retrieve' or request.method.lower() == 'get':
            return True

        return course.is_admin(request.user)


class CourseViewSet(TransactionRetrieveUpdateDestroyMixin,
                    transaction_mixins.TransactionCreateMixin,
                    mixins.ListModelMixin,
                    AGModelGenericViewSet):
    serializer_class = ag_serializers.CourseSerializer
    permission_classes = (permissions.IsAuthenticated, CoursePermissions,)

    model_manager = ag_models.Course.objects

    def get_queryset(self):
        return ag_models.Course.objects.all()

    @decorators.detail_route()
    def my_roles(self, request, *args, **kwargs):
        course = self.get_object()
        return response.Response({
            'is_admin': course.is_admin(request.user),
            'is_staff': course.is_staff(request.user),
            'is_student': course.is_student(request.user),
            'is_handgrader': course.is_handgrader(request.user)
        })
