import autograder.handgrading.models as handgrading_models
import autograder.handgrading.serializers as handgrading_serializers
import autograder.rest_api.permissions as ag_permissions

from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, ListCreateNestedModelViewSet, TransactionRetrievePatchDestroyMixin,
)


class CriterionResultListCreateView(ListCreateNestedModelViewSet):
    serializer_class = handgrading_serializers.CriterionResultSerializer
    permission_classes = [
        ag_permissions.is_admin_or_staff_or_handgrader(
            lambda handgrading_result: handgrading_result.handgrading_rubric.project.course)]

    pk_key = 'handgrading_result_pk'
    model_manager = handgrading_models.HandgradingResult.objects.select_related(
        'handgrading_rubric__project__course')
    to_one_field_name = 'handgrading_result'
    reverse_to_one_field_name = 'criterion_results'


class CriterionResultDetailViewSet(TransactionRetrievePatchDestroyMixin, AGModelGenericViewSet):
    serializer_class = handgrading_serializers.CriterionResultSerializer
    permission_classes = [
        ag_permissions.is_admin_or_staff_or_handgrader(
            lambda criterion_result: (
                criterion_result.handgrading_result.handgrading_rubric.project.course)
        )
    ]
    model_manager = handgrading_models.CriterionResult.objects.select_related(
        'handgrading_result__handgrading_rubric__project__course'
    ).prefetch_related(
        'criterion'
    )
