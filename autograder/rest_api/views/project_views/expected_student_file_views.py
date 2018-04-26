from rest_framework import permissions

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api.views.ag_model_views import ListCreateNestedModelViewSet, \
    AGModelGenericViewSet, TransactionRetrievePatchDestroyMixin
from autograder.rest_api.views.permission_components import user_can_view_project


class ListCreateExpectedStudentFilesViewSet(ListCreateNestedModelViewSet):
    serializer_class = ag_serializers.ExpectedStudentFileSerializer
    permission_classes = (ag_permissions.is_admin_or_read_only_can_view_project(),)

    model_manager = ag_models.Project.objects
    to_one_field_name = 'project'
    reverse_to_one_field_name = 'expected_student_files'


class _Permissions(permissions.BasePermission):
    def has_object_permission(self, request, view, pattern):
        if request.method in permissions.SAFE_METHODS:
            return user_can_view_project(request.user, pattern.project)

        return pattern.project.course.is_admin(request.user)


class ExpectedStudentFilePatternDetailViewSet(TransactionRetrievePatchDestroyMixin,
                                              AGModelGenericViewSet):
    serializer_class = ag_serializers.ExpectedStudentFileSerializer
    permission_classes = (ag_permissions.is_admin_or_read_only_can_view_project(),)

    model_manager = ag_models.ExpectedStudentFile.objects
