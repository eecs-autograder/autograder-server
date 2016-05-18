from rest_framework import viewsets, mixins, permissions
from rest_framework import decorators

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

    # -------------------------------------------------------------------------

    @decorators.list_route(url_path='admins')
    def list_course_admins(self, request, pk):
        pass

    @decorators.detail_route(methods=['post'], url_path='admins')
    def add_course_admins(self, request, pk):
        pass

    @decorators.detail_route(methods=['delete'], url_path='admins')
    def remove_course_admins(self, request, pk):
        pass

    # -------------------------------------------------------------------------

    @decorators.list_route(url_path='semesters')
    def list_semesters(self, request, pk):
        pass

    @decorators.detail_route(methods=['post'], url_path='semesters')
    def create_semester(self, request, pk):
        pass
