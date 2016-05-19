from django.contrib.auth.models import User

from rest_framework import viewsets, mixins, permissions, response, status
# from rest_framework import decorators

import autograder.rest_api.serializers as ag_serializers
import autograder.core.models as ag_models


class CoursePermissions(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        if view.action in ['list', 'create']:
            return request.user.is_superuser

        return True

    def has_object_permission(self, request, view, course):
        if view.action == 'retrieve':
            return True

        return course.is_administrator(request.user)


class CourseViewSet(mixins.CreateModelMixin,
                    mixins.UpdateModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    serializer_class = ag_serializers.CourseSerializer
    permission_classes = (CoursePermissions,)

    def get_queryset(self):
        return ag_models.Course.objects.all()

    # @decorators.permission_classes((permissions.IsAuthenticated,
    #                                 IsSuperuserOrAdmin))
    # @decorators.detail_route(methods=['post'], url_path='admins')
    # def spam(self, request, pk):
    #     print('waaaaaaa')
    #     pass

    # @decorators.permission_classes((permissions.IsAuthenticated,
    #                                 IsSuperuserOrAdmin))
    # @decorators.detail_route(methods=['get'], url_path='admins')
    # def blah(self, request, pk):
    #     print('bloooo')
    #     pass

    # @decorators.permission_classes((permissions.IsAuthenticated,
    #                                 IsSuperuserOrAdmin))
    # @decorators.detail_route(methods=['get'], url_path='admins')
    # def add_course_admins(self, request, pk):
    #     print('marp')
    #     pass

    # @decorators.detail_route(methods=['delete'], url_path='admins')
    # def remove_course_admins(self, request, pk):
    #     # print(value, ...)
    #     pass

    # # -------------------------------------------------------------------------

    # @decorators.detail_route(url_path='semesters')
    # def list_semesters(self, request, pk):
    #     pass

    # @decorators.detail_route(methods=['post'], url_path='semesters')
    # def create_semester(self, request, pk):
    #     pass


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

    def create(self, request, course_pk):
        users_to_add = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.getlist('new_admins')]
        self.get_object(course_pk).administrators.add(*users_to_add)

        return response.Response(status=status.HTTP_204_NO_CONTENT)
