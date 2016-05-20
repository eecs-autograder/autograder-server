from rest_framework import viewsets, mixins, permissions, response, status
from rest_framework.decorators import detail_route

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


class IsSuperuserOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, course):
        return (request.user.is_superuser or
                course.is_administrator(request.user))


# class detail_route_dispatcher:
#     def __init__(self, get=None, post=None, put=None, patch=None, delete=None):
#         def default_func(self):
#             return response.Response


class CourseViewSet(mixins.CreateModelMixin,
                    mixins.UpdateModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    serializer_class = ag_serializers.CourseSerializer
    permission_classes = (CoursePermissions,)

    def get_queryset(self):
        return ag_models.Course.objects.all()

    # @detail_route(methods=['get', 'post', 'delete'],
    #               permission_classes=[IsSuperuserOrAdmin])
    # def admins(self, request, pk):
    #     try:
    #         self._admins_methods[request.method.lower()](self)
    #     except KeyError:
    #         return response.Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    # def _list_admins(self):
    #     print('get')

    # def _add_admins(self):
    #     print('post')

    # def _remove_admins(self):
    #     print('delete')

    # _admins_methods = {
    #     'get': _list_admins,
    #     'post': _add_admins,
    #     'delete': _remove_admins,
    # }
