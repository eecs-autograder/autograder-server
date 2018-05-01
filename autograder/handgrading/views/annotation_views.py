from django.db import transaction
from drf_yasg.openapi import Parameter
from drf_yasg.utils import swagger_auto_schema
from rest_framework import response

import autograder.handgrading.models as handgrading_models
import autograder.handgrading.serializers as handgrading_serializers
import autograder.rest_api.permissions as ag_permissions
from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, ListCreateNestedModelViewSet, TransactionRetrievePatchDestroyMixin,
    AGModelAPIView)
from autograder.rest_api.views.schema_generation import APITags


class AnnotationListCreateView(ListCreateNestedModelViewSet):
    serializer_class = handgrading_serializers.AnnotationSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda handgrading_rubric: handgrading_rubric.project.course)]

    pk_key = 'handgrading_rubric_pk'
    model_manager = handgrading_models.HandgradingRubric.objects.select_related('project__course')
    to_one_field_name = 'handgrading_rubric'
    reverse_to_one_field_name = 'annotations'


class AnnotationDetailViewSet(TransactionRetrievePatchDestroyMixin, AGModelGenericViewSet):
    serializer_class = handgrading_serializers.AnnotationSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda annotation: annotation.handgrading_rubric.project.course)
    ]
    model_manager = handgrading_models.Annotation.objects.select_related(
        'handgrading_rubric__project__course',
    )


class AnnotationOrderView(AGModelAPIView):
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda handgrading_rubric: handgrading_rubric.project.course)]

    pk_key = 'handgrading_rubric_pk'
    model_manager = handgrading_models.HandgradingRubric.objects.select_related('project__course')
    api_tags = [APITags.annotations]

    @swagger_auto_schema(
        responses={'200': 'Returns a list of Annotation IDs, in their assigned order.'})
    def get(self, request, *args, **kwargs):
        handgrading_rubric = self.get_object()
        return response.Response(list(handgrading_rubric.get_annotation_order()))

    @swagger_auto_schema(
        request_body_parameters=[
            Parameter(name='', in_='body',
                      type='List[string]',
                      description='A list of Annotation IDs, in the new order to set.')],
        responses={'200': 'Returns a list of Annotation IDs, in their new order.'}
    )
    def put(self, request, *args, **kwargs):
        with transaction.atomic():
            handgrading_rubric = self.get_object()
            handgrading_rubric.set_annotation_order(request.data)
            return response.Response(list(handgrading_rubric.get_annotation_order()))
