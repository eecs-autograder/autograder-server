import autograder.handgrading.models as handgrading_models
import autograder.handgrading.serializers as handgrading_serializers
import autograder.rest_api.permissions as ag_permissions
from rest_framework import response
from django.db import transaction

from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, ListCreateNestedModelView, TransactionRetrieveUpdateDestroyMixin,
    AGModelGenericView
)


class AnnotationListCreateView(ListCreateNestedModelView):
    serializer_class = handgrading_serializers.AnnotationSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda handgrading_rubric: handgrading_rubric.project.course)]

    pk_key = 'handgrading_rubric_pk'
    model_manager = handgrading_models.HandgradingRubric.objects.select_related('project__course')
    foreign_key_field_name = 'handgrading_rubric'
    reverse_foreign_key_field_name = 'annotations'


class AnnotationDetailViewSet(TransactionRetrieveUpdateDestroyMixin, AGModelGenericViewSet):
    serializer_class = handgrading_serializers.AnnotationSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda annotation: annotation.handgrading_rubric.project.course)
    ]
    model_manager = handgrading_models.Annotation.objects.select_related(
        'handgrading_rubric__project__course',
    )

class AnnotationOrderView(AGModelGenericView):
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda handgrading_rubric: handgrading_rubric.project.course)]

    pk_key = 'handgrading_rubric_pk'
    model_manager = handgrading_models.HandgradingRubric.objects.select_related('project__course')

    def get(self, request, *args, **kwargs):
        handgrading_rubric = self.get_object()
        return response.Response(list(handgrading_rubric.get_annotation_order()))

    def put(self, request, *args, **kwargs):
        with transaction.atomic():
            handgrading_rubric = self.get_object()
            handgrading_rubric.set_annotation_order(request.data)
            return response.Response(list(handgrading_rubric.get_annotation_order()))
