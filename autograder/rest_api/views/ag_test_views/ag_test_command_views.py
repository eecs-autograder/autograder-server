from django.db import transaction
from rest_framework import generics, response

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
import autograder.rest_api.permissions as ag_permissions

from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, ListCreateNestedModelView, TransactionRetrieveUpdateDestroyMixin,
    GetObjectLockOnUnsafeMixin)


class AGTestCommandListCreateView(ListCreateNestedModelView):
    serializer_class = ag_serializers.AGTestCommandSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_case: ag_test_case.ag_test_suite.project.course)
    ]

    pk_key = 'ag_test_case_pk'
    model_manager = ag_models.AGTestCase.objects.select_related('ag_test_suite__project__course')
    foreign_key_field_name = 'ag_test_case'
    reverse_foreign_key_field_name = 'ag_test_commands'


class AGTestCommandOrderView(GetObjectLockOnUnsafeMixin, generics.GenericAPIView):
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


class AGTestCommandDetailViewSet(TransactionRetrieveUpdateDestroyMixin, AGModelGenericViewSet):
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
