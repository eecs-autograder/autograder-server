from rest_framework import viewsets, mixins, permissions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from ..load_object_mixin import build_load_object_mixin


class IsAdminOrReadOnlyStaffOrStudent(permissions.BasePermission):
    def has_object_permission(self, request, view, course):
        is_admin = course.is_administrator(request.user)
        is_staff = course.is_course_staff(request.user)
        read_only = request.method in permissions.SAFE_METHODS
        is_enrolled = course.is_enrolled_student(request.user)

        return is_admin or (read_only and (is_staff or is_enrolled))


class CourseProjectsViewSet(build_load_object_mixin(ag_models.Course),
                            mixins.CreateModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    serializer_class = ag_serializers.ProjectSerializer
    permission_classes = (permissions.IsAuthenticated,
                          IsAdminOrReadOnlyStaffOrStudent)

    def get_queryset(self):
        course = self.load_object(self.kwargs['course_pk'])
        if course.is_course_staff(self.request.user):
            return course.projects.all()

        return course.projects.filter(visible_to_students=True)

    def create(self, request, course_pk, *args, **kwargs):
        request.data['course'] = self.load_object(course_pk)
        return super().create(request, *args, **kwargs)
