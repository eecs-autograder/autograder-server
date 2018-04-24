from django.db import transaction
from rest_framework import response
from rest_framework.views import APIView

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, ListCreateNestedModelViewSet, TransactionRetrievePatchDestroyMixin,
    GetObjectLockOnUnsafeMixin)


class AGTestSuiteListCreateView(ListCreateNestedModelViewSet):
    serializer_class = ag_serializers.AGTestSuiteSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(lambda project: project.course)]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')
    to_one_field_name = 'project'
    reverse_to_one_field_name = 'ag_test_suites'


class AGTestSuiteOrderView(GetObjectLockOnUnsafeMixin, APIView):
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(lambda project: project.course)
    ]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')

    def get(self, *args, **kwargs):
        project = self.get_object()
        return response.Response(list(project.get_agtestsuite_order()))

    def put(self, request, *args, **kwargs):
        with transaction.atomic():
            project = self.get_object()
            project.set_agtestsuite_order(request.data)
            return response.Response(list(project.get_agtestsuite_order()))


class AGTestSuiteDetailViewSet(TransactionRetrievePatchDestroyMixin, AGModelGenericViewSet):
    serializer_class = ag_serializers.AGTestSuiteSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_suite: ag_test_suite.project.course)
    ]
    model_manager = ag_models.AGTestSuite.objects.select_related(
        'project__course',
        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config',
    )
