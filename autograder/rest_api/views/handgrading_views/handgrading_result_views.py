import autograder.core.models as ag_models
import autograder.handgrading.models as handgrading_models
import autograder.handgrading.serializers as handgrading_serializers
import autograder.rest_api.permissions as ag_permissions

from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, ListCreateNestedModelView, TransactionRetrieveUpdateDestroyMixin,
)


class HandgradingResultListCreateView(ListCreateNestedModelView):
    serializer_class = handgrading_serializers.HandgradingResultSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(lambda project: project.course)]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')
    # TODO: HOW TO FIND PROJECT
    foreign_key_field_name = 'submission.submission_group.project'
    reverse_foreign_key_field_name = 'handgrading_result'


class HandgradingResultDetailViewSet(TransactionRetrieveUpdateDestroyMixin, AGModelGenericViewSet):
    serializer_class = handgrading_serializers.HandgradingResultSerializer
    # TODO: Check if this is right (accessing project through submission group
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda handgrading_result: handgrading_result.submission.submission_group.project.course)
    ]
    model_manager = handgrading_models.HandgradingResult.objects.select_related(
        'applied_annotations',
        'arbitrary_points',
        'comments',
        'criterion_results',
    )
