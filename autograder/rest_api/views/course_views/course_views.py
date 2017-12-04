from rest_framework import viewsets, mixins, permissions, decorators, response, exceptions
from django.contrib.auth.models import User

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins
import autograder.rest_api.permissions as ag_permissions

from ..load_object_mixin import build_load_object_mixin


class CoursePermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if view.action in ['list', 'create']:
            return request.user.is_superuser

        return True

    def has_object_permission(self, request, view, course):
        if view.action == 'retrieve' or request.method.lower() == 'get':
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

    @decorators.detail_route()
    def my_roles(self, request, *args, **kwargs):
        course = self.get_object()
        return response.Response({
            'is_admin': course.is_administrator(request.user),
            'is_staff': course.is_course_staff(request.user),
            'is_enrolled': course.is_enrolled_student(request.user),
            'is_handgrader': course.is_handgrader(request.user)
        })

    @decorators.detail_route(permission_classes=[permissions.IsAuthenticated,
                                                 ag_permissions.is_admin(lambda course: course)],
                             methods=["get", "post", "delete"])
    def handgraders(self, request, *args, **kwargs):
        course = self.get_object()

        if request.method == "get":
            return course.handgraders.all()
        elif request.method == "post":
            self.add_handgraders(course, request.data['new_handgraders'])
        elif request.method == "delete":
            self.remove_handgraders(course, request.data['remove_handgraders'])

    def add_handgraders(self, course, usernames):
        users_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in usernames]
        course.handgraders.add(*users_to_add)

    def remove_handgraders(self, course, usernames):
        users_to_remove = User.objects.filter(pk__in=[user['pk'] for user in usernames])

        if self.request.user in users_to_remove:
            raise exceptions.ValidationError(
                {'remove_handgraders':
                    ["You cannot remove your own handgrader privileges."]})

        course.handgraders.remove(*users_to_remove)
