from django.db import transaction
from rest_framework import response
from rest_framework.views import APIView

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, ListCreateNestedModelViewSet, TransactionRetrievePatchDestroyMixin,
    GetObjectLockOnUnsafeMixin)


class AGTestCommandListCreateView(ListCreateNestedModelViewSet):
    serializer_class = ag_serializers.AGTestCommandSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_case: ag_test_case.ag_test_suite.project.course)
    ]

    pk_key = 'ag_test_case_pk'
    model_manager = ag_models.AGTestCase.objects.select_related('ag_test_suite__project__course')
    to_one_field_name = 'ag_test_case'
    reverse_to_one_field_name = 'ag_test_commands'


class AGTestCommandOrderView(GetObjectLockOnUnsafeMixin, APIView):
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_case: ag_test_case.ag_test_suite.project.course)
    ]

    pk_key = 'ag_test_case_pk'
    model_manager = ag_models.AGTestCase.objects.select_related('ag_test_suite__project__course')

    def get(self, request, *args, **kwargs):
        ag_test_case = self.get_object()
        return response.Response(list(ag_test_case.get_agtestcommand_order()))

    def put(self, request, *args, **kwargs):
        with transaction.atomic():
            ag_test_case = self.get_object()
            ag_test_case.set_agtestcommand_order(request.data)
            return response.Response(list(ag_test_case.get_agtestcommand_order()))


class AGTestCommandDetailViewSet(TransactionRetrievePatchDestroyMixin, AGModelGenericViewSet):
    serializer_class = ag_serializers.AGTestCommandSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_command: ag_test_command.ag_test_case.ag_test_suite.project.course
        )
    ]
    model_manager = ag_models.AGTestCommand.objects.select_related(
        'ag_test_case__ag_test_suite__project__course',
        'normal_fdbk_config',
        'ultimate_submission_fdbk_config',
        'past_limit_submission_fdbk_config',
        'staff_viewer_fdbk_config',
    )
