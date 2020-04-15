from django.db import transaction
from rest_framework import response

import autograder.handgrading.models as hg_models
import autograder.handgrading.serializers as handgrading_serializers
import autograder.rest_api.permissions as ag_permissions
from autograder.rest_api.schema import (AGDetailViewSchemaGenerator,
                                        AGListCreateViewSchemaGenerator, APITags, OrderViewSchema)
from autograder.rest_api.views.ag_model_views import (AGModelAPIView, AGModelDetailView,
                                                      NestedModelView)


class ListCreateAnnotationView(NestedModelView):
    schema = AGListCreateViewSchemaGenerator([APITags.annotations], hg_models.Annotation)

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda handgrading_rubric: handgrading_rubric.project.course)]

    pk_key = 'handgrading_rubric_pk'
    model_manager = hg_models.HandgradingRubric.objects.select_related('project__course')
    nested_field_name = 'annotations'
    parent_obj_field_name = 'handgrading_rubric'

    def get(self, *args, **kwargs):
        return self.do_list()

    def post(self, *args, **kwargs):
        return self.do_create()


class AnnotationDetailView(AGModelDetailView):
    schema = AGDetailViewSchemaGenerator([APITags.annotations])

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda annotation: annotation.handgrading_rubric.project.course)
    ]
    model_manager = hg_models.Annotation.objects.select_related(
        'handgrading_rubric__project__course',
    )

    def get(self, *args, **kwargs):
        return self.do_get()

    def patch(self, *args, **kwargs):
        return self.do_patch()

    def delete(self, *args, **kwargs):
        return self.do_delete()


class AnnotationOrderView(AGModelAPIView):
    schema = OrderViewSchema([APITags.annotations])

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda handgrading_rubric: handgrading_rubric.project.course)]

    pk_key = 'handgrading_rubric_pk'
    model_manager = hg_models.HandgradingRubric.objects.select_related('project__course')
    api_tags = [APITags.annotations]

    def get(self, request, *args, **kwargs):
        handgrading_rubric = self.get_object()
        return response.Response(list(handgrading_rubric.get_annotation_order()))

    def put(self, request, *args, **kwargs):
        with transaction.atomic():
            handgrading_rubric = self.get_object()
            handgrading_rubric.set_annotation_order(request.data)
            return response.Response(list(handgrading_rubric.get_annotation_order()))
