from rest_framework import permissions

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api.views.ag_model_views import (
    ListCreateNestedModelViewSet,
    AGModelGenericViewSet, TransactionRetrievePatchDestroyMixin)


class ListCreateExpectedStudentFilesViewSet(ListCreateNestedModelViewSet):
    serializer_class = ag_serializers.ExpectedStudentFileSerializer
    permission_classes = (ag_permissions.is_admin_or_read_only_can_view_project(),)

    model_manager = ag_models.Project.objects
    to_one_field_name = 'project'
    reverse_to_one_field_name = 'expected_student_files'


class ExpectedStudentFilePatternDetailViewSet(TransactionRetrievePatchDestroyMixin,
                                              AGModelGenericViewSet):
    serializer_class = ag_serializers.ExpectedStudentFileSerializer
    permission_classes = (ag_permissions.is_admin_or_read_only_can_view_project(),)

    model_manager = ag_models.ExpectedStudentFile.objects
