import autograder.core.models as ag_models
import autograder.handgrading.models as handgrading_models
import autograder.handgrading.serializers as handgrading_serializers
import autograder.rest_api.permissions as ag_permissions

from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, ListCreateNestedModelView, TransactionRetrieveUpdateDestroyMixin,
)

# TODO: FINISH VIEWS
class AnnotationListCreateView(ListCreateNestedModelView):
    serializer_class = handgrading_serializers.AnnotationSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(lambda project: project.course)]

    pk_key = 'handgrading_rubric_pk'
    model_manager = handgrading_models.HandgradingRubric.objects.select_related('annotation')
    foreign_key_field_name = 'handgrading_rubric'
    reverse_foreign_key_field_name = 'annotation'


class AnnotationDetailViewSet(TransactionRetrieveUpdateDestroyMixin, AGModelGenericViewSet):
    serializer_class = handgrading_serializers.AnnotationSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda annotation: annotation.handgrading_rubric.project.course)
    ]
    model_manager = handgrading_models.Criterion.objects.select_related(
        '??',
    )
