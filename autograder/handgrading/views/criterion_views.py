from django.db import transaction
from rest_framework import response, status

import autograder.handgrading.models as hg_models
import autograder.rest_api.permissions as ag_permissions
from autograder.rest_api.schema import (AGDetailViewSchemaGenerator,
                                        AGListCreateViewSchemaGenerator, APITags, OrderViewSchema)
from autograder.rest_api.views.ag_model_views import (AGModelAPIView, AGModelDetailView,
                                                      AGModelGenericViewSet,
                                                      ListCreateNestedModelViewSet,
                                                      NestedModelView,
                                                      TransactionRetrievePatchDestroyMixin,
                                                      convert_django_validation_error)


class ListCreateCriterionView(NestedModelView):
    schema = AGListCreateViewSchemaGenerator([APITags.criteria], hg_models.Criterion)

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda handgrading_rubric: handgrading_rubric.project.course)]

    pk_key = 'handgrading_rubric_pk'
    model_manager = hg_models.HandgradingRubric.objects.select_related('project__course')
    nested_field_name = 'criteria'
    parent_obj_field_name = 'handgrading_rubric'

    def get(self, *args, **kwargs):
        return self.do_list()

    @convert_django_validation_error
    @transaction.atomic()
    def post(self, request, *args, **kwargs):
        handgrading_rubric = self.get_object()

        response = self.do_create()
        criterion = hg_models.Criterion.objects.get(pk=response.data['pk'])
        results = hg_models.HandgradingResult.objects.filter(handgrading_rubric=handgrading_rubric)

        # Create CriterionResult for every HandgradingResult with the same HandgradingRubric
        for result in results:
            hg_models.CriterionResult.objects.validate_and_create(
                selected=False,
                criterion=criterion,
                handgrading_result=result)

        return response


class CriterionDetailView(AGModelDetailView):
    schema = AGDetailViewSchemaGenerator([APITags.criteria])

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda criterion: criterion.handgrading_rubric.project.course)
    ]

    model_manager = hg_models.Criterion.objects.select_related(
        'handgrading_rubric__project__course')

    def get(self, *args, **kwargs):
        return self.do_get()

    def patch(self, *args, **kwargs):
        return self.do_patch()

    def delete(self, *args, **kwargs):
        return self.do_delete()


class CriterionOrderView(AGModelAPIView):
    schema = OrderViewSchema([APITags.criteria])

    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda handgrading_rubric: handgrading_rubric.project.course)]

    pk_key = 'handgrading_rubric_pk'
    model_manager = hg_models.HandgradingRubric.objects.select_related('project__course')

    def get(self, request, *args, **kwargs):
        handgrading_rubric = self.get_object()
        return response.Response(list(handgrading_rubric.get_criterion_order()))

    def put(self, request, *args, **kwargs):
        with transaction.atomic():
            handgrading_rubric = self.get_object()
            handgrading_rubric.set_criterion_order(request.data)
            return response.Response(list(handgrading_rubric.get_criterion_order()))
