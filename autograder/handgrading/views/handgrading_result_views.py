import autograder.core.models as ag_models
import autograder.handgrading.models as handgrading_models
import autograder.handgrading.serializers as handgrading_serializers
import autograder.rest_api.permissions as ag_permissions

from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, RetrieveCreateNestedModelView, TransactionRetrieveUpdateDestroyMixin,
)


# TODO: FIX VIEW
class HandgradingResultRetrieveCreateView(RetrieveCreateNestedModelView):
    serializer_class = handgrading_serializers.HandgradingResultSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda submission: submission.submission_group.project.course)]

    pk_key = 'submission_pk'
    model_manager = ag_models.Submission.objects.select_related(
        'submission_group__project__course'
    )
    one_to_one_field_name = 'submission'
    reverse_one_to_one_field_name = 'handgrading_results'


class HandgradingResultDetailViewSet(TransactionRetrieveUpdateDestroyMixin, AGModelGenericViewSet):
    serializer_class = handgrading_serializers.HandgradingResultSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda handgrading_result: handgrading_result.handgrading_rubric.project.course)
    ]

    model_manager = handgrading_models.HandgradingResult.objects.select_related(
        'handgrading_rubric__project__course'
    ).prefetch_related(
        'applied_annotations',
        'arbitrary_points',
        'comments',
        'criterion_results',
    )
