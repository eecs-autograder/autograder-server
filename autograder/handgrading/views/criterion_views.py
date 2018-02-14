import autograder.handgrading.models as handgrading_models
import autograder.handgrading.serializers as handgrading_serializers
import autograder.rest_api.permissions as ag_permissions
from rest_framework import response

from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, ListCreateNestedModelView, TransactionRetrieveUpdateDestroyMixin,
    AGModelGenericView)


class CriterionListCreateView(ListCreateNestedModelView):
    serializer_class = handgrading_serializers.CriterionSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda handgrading_rubric: handgrading_rubric.project.course)]

    pk_key = 'handgrading_rubric_pk'
    model_manager = handgrading_models.HandgradingRubric.objects.select_related('project__course')
    foreign_key_field_name = 'handgrading_rubric'
    reverse_foreign_key_field_name = 'criteria'


class CriterionDetailViewSet(TransactionRetrieveUpdateDestroyMixin, AGModelGenericViewSet):
    serializer_class = handgrading_serializers.CriterionSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda criterion: criterion.handgrading_rubric.project.course)]

    model_manager = handgrading_models.Criterion.objects.select_related(
        'handgrading_rubric__project__course',)


class CriterionOrderView(AGModelGenericView):
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda handgrading_rubric: handgrading_rubric.project.course)]

    pk_key = 'handgrading_rubric_pk'
    model_manager = handgrading_models.Criterion.objects.select_related(
        'handgrading_rubric__project__course',)

    def get(self, request, *args, **kwargs):
        ag_test_suite = self.get_object()
        return response.Response(list(ag_test_suite.get_agtestcase_order()))

    def put(self, request, *args, **kwargs):
        with transaction.atomic():
            ag_test_suite = self.get_object()
            ag_test_suite.set_agtestcase_order(request.data)
            return response.Response(list(ag_test_suite.get_agtestcase_order()))
