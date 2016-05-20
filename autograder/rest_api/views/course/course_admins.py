from django.contrib.auth.models import User

from rest_framework import (
    viewsets, mixins, permissions, response, status, exceptions)

import autograder.rest_api.serializers as ag_serializers
import autograder.core.models as ag_models


class IsSuperuserOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, course):
        return (request.user.is_superuser or
                course.is_administrator(request.user))


class CourseAdminViewSet(mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    serializer_class = ag_serializers.UserSerializer
    permission_classes = (IsSuperuserOrAdmin),

    def get_object(self, pk):
        course = ag_models.Course.objects.get(pk=pk)
        self.check_object_permissions(self.request, course)
        return course

    def get_queryset(self):
        course = self.get_object(self.kwargs['course_pk'])
        return course.administrators.all()

    def post(self, request, course_pk):
        users_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.getlist('new_admins')]
        self.get_object(course_pk).administrators.add(*users_to_add)

        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, course_pk):
        users_to_remove = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.getlist('remove_admins')]

        if request.user in users_to_remove:
            raise exceptions.ValidationError(
                {'remove_admins':
                    ["You cannot remove your own admin privileges."]})

        self.get_object(course_pk).administrators.remove(*users_to_remove)

        return response.Response(status=status.HTTP_204_NO_CONTENT)
