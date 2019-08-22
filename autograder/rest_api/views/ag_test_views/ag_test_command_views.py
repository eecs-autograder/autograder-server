from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from drf_yasg.openapi import Parameter
from drf_yasg.utils import swagger_auto_schema
from rest_framework import response

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.core.caching import clear_submission_results_cache
from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, ListCreateNestedModelViewSet, TransactionRetrievePatchDestroyMixin,
    AGModelAPIView)
from autograder.rest_api.views.schema_generation import APITags


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


class AGTestCommandOrderView(AGModelAPIView):
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_case: ag_test_case.ag_test_suite.project.course)
    ]

    pk_key = 'ag_test_case_pk'
    model_manager = ag_models.AGTestCase.objects.select_related('ag_test_suite__project__course')
    api_tags = [APITags.ag_test_commands]

    @swagger_auto_schema(
        responses={'200': 'Returns a list of AGTestCommand IDs, in their assigned order.'})
    def get(self, request, *args, **kwargs):
        ag_test_case = self.get_object()
        return response.Response(list(ag_test_case.get_agtestcommand_order()))

    @swagger_auto_schema(
        request_body_parameters=[
            Parameter(name='', in_='body',
                      type='List[string]',
                      description='A list of AGTestCommand IDs, in the new order to set.')],
        responses={'200': 'Returns a list of AGTestCommand IDs, in their new order.'}
    )
    def put(self, request, *args, **kwargs):
        with transaction.atomic():
            ag_test_case = self.get_object()
            ag_test_case.set_agtestcommand_order(request.data)
            clear_submission_results_cache(ag_test_case.ag_test_suite.project_id)
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
    )
