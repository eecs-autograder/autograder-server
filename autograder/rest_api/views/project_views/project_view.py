from rest_framework import viewsets, mixins, permissions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from ..load_object_mixin import build_load_object_mixin


class ProjectPermissions(permissions.BasePermission):
    def has_object_permission(self, request, view, project):
        if request.method not in permissions.SAFE_METHODS:
            return project.course.is_administrator(request.user)

        if project.course.is_course_staff(request.user):
            return True

        if not project.visible_to_students:
            return False

        if project.course.is_enrolled_student(request.user):
            return True

        return project.allow_submissions_from_non_enrolled_students


class ProjectViewSet(build_load_object_mixin(ag_models.Project),
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     viewsets.GenericViewSet):
    serializer_class = ag_serializers.ProjectSerializer
    permission_classes = (permissions.IsAuthenticated, ProjectPermissions)

    def get_object(self):
        return self.load_object(self.kwargs['pk'])
