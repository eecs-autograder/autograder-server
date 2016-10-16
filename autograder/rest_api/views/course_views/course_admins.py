from django.contrib.auth.models import User
from django.db import transaction

from rest_framework import (
    viewsets, mixins, permissions, response,
    status, exceptions)

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from ..load_object_mixin import build_load_object_mixin


class IsSuperuserOrAdminOrReadOnlyStaff(permissions.BasePermission):
    def has_object_permission(self, request, view, course):
        can_edit = (request.user.is_superuser or
                    course.is_administrator(request.user))

        staff_and_read_only = (course.is_course_staff(request.user) and
                               request.method in permissions.SAFE_METHODS)

        return can_edit or staff_and_read_only


class CourseAdminViewSet(build_load_object_mixin(ag_models.Course, pk_key='course_pk'),
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    serializer_class = ag_serializers.UserSerializer
    permission_classes = (permissions.IsAuthenticated,
                          IsSuperuserOrAdminOrReadOnlyStaff,)

    def get_queryset(self):
        course = self.get_object()
        return course.administrators.all()

    @transaction.atomic()
    def patch(self, request, *args, **kwargs):
        course = self.get_object()
        if 'new_admins' in request.data:
            self.add_admins(course, request.data['new_admins'])
        elif 'remove_admins' in request.data:
            self.remove_admins(course, request.data['remove_admins'])

        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def add_admins(self, course, usernames):
        users_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in usernames]
        course.administrators.add(*users_to_add)

    def remove_admins(self, course, users_json):
        users_to_remove = User.objects.filter(pk__in=[user['pk'] for user in users_json])

        if self.request.user in users_to_remove:
            raise exceptions.ValidationError(
                {'remove_admins':
                    ["You cannot remove your own admin privileges."]})

        course.administrators.remove(*users_to_remove)
