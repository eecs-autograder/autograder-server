from rest_framework import viewsets, mixins, permissions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder.rest_api.views.ag_model_views import ListCreateNestedModelView


class IsAdminOrReadOnlyStaffOrStudent(permissions.BasePermission):
    def has_object_permission(self, request, view, course):
        is_admin = course.is_administrator(request.user)
        is_staff = course.is_course_staff(request.user)
        read_only = request.method in permissions.SAFE_METHODS
        is_enrolled = course.is_enrolled_student(request.user)

        return is_admin or (read_only and (is_staff or is_enrolled))


class ListCreateProjectView(ListCreateNestedModelView):
    serializer_class = ag_serializers.ProjectSerializer
    permission_classes = (IsAdminOrReadOnlyStaffOrStudent,)

    model_manager = ag_models.Course.objects
    foreign_key_field_name = 'course'
    reverse_foreign_key_field_name = 'projects'
