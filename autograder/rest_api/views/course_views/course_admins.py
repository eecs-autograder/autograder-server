from django.contrib.auth.models import User

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


class CourseAdminViewSet(build_load_object_mixin(ag_models.Course),
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    serializer_class = ag_serializers.UserSerializer
    permission_classes = (permissions.IsAuthenticated,
                          IsSuperuserOrAdminOrReadOnlyStaff,)

    def get_queryset(self):
        course = self.load_object(self.kwargs['course_pk'])
        return course.administrators.all()

    def post(self, request, course_pk):
        users_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data['new_admins']]
        self.load_object(course_pk).administrators.add(*users_to_add)

        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, course_pk):
        users_to_remove = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data['remove_admins']]

        if request.user in users_to_remove:
            raise exceptions.ValidationError(
                {'remove_admins':
                    ["You cannot remove your own admin privileges."]})

        self.load_object(course_pk).administrators.remove(*users_to_remove)

        return response.Response(status=status.HTTP_204_NO_CONTENT)
