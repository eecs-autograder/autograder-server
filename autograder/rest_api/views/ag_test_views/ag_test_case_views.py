from django.db import transaction
from drf_yasg.openapi import Parameter
from drf_yasg.utils import swagger_auto_schema
from rest_framework import response

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api.views.ag_model_views import (AGModelAPIView, AGModelGenericViewSet,
                                                      ListCreateNestedModelViewSet,
                                                      TransactionRetrievePatchDestroyMixin)
from autograder.rest_api.views.schema_generation import APITags


class AGTestCaseListCreateView(ListCreateNestedModelViewSet):
    serializer_class = ag_serializers.AGTestCaseSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_suite: ag_test_suite.project.course)
    ]

    pk_key = 'ag_test_suite_pk'
    model_manager = ag_models.AGTestSuite.objects.select_related('project__course')
    to_one_field_name = 'ag_test_suite'
    reverse_to_one_field_name = 'ag_test_cases'


class AGTestCaseOrderView(AGModelAPIView):
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_suite: ag_test_suite.project.course)
    ]

    pk_key = 'ag_test_suite_pk'
    model_manager = ag_models.AGTestSuite.objects.select_related('project__course')
    api_tags = [APITags.ag_test_cases]

    @swagger_auto_schema(
        responses={'200': 'Returns a list of AGTestCase IDs, in their assigned order.'})
    def get(self, request, *args, **kwargs):
        ag_test_suite = self.get_object()
        return response.Response(list(ag_test_suite.get_agtestcase_order()))

    @swagger_auto_schema(
        request_body_parameters=[
            Parameter(name='', in_='body',
                      type='List[string]',
                      description='A list of AGTestCase IDs, in the new order to set.')],
        responses={'200': 'Returns a list of AGTestCase IDs, in their new order.'}
    )
    def put(self, request, *args, **kwargs):
        with transaction.atomic():
            ag_test_suite = self.get_object()
            ag_test_suite.set_agtestcase_order(request.data)
            return response.Response(list(ag_test_suite.get_agtestcase_order()))


class AGTestCaseDetailViewSet(TransactionRetrievePatchDestroyMixin, AGModelGenericViewSet):
    serializer_class = ag_serializers.AGTestCaseSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda ag_test_case: ag_test_case.ag_test_suite.project.course
        )
    ]
    model_manager = ag_models.AGTestCase.objects.select_related(
        'ag_test_suite__project__course',
    )
