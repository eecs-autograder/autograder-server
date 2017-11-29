import autograder.handgrading.models as handgrading_models
import autograder.handgrading.serializers as handgrading_serializers
import autograder.rest_api.permissions as ag_permissions

from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, ListCreateNestedModelView, TransactionRetrieveUpdateDestroyMixin,
)


class CommentListCreateView(ListCreateNestedModelView):
    serializer_class = handgrading_serializers.CommentSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda handgrading_result: handgrading_result.handgrading_rubric.project.course)]

    pk_key = 'handgrading_result_pk'
    model_manager = handgrading_models.HandgradingResult.objects.select_related(
        'handgrading_rubric__project__course')
    foreign_key_field_name = 'handgrading_result'
    reverse_foreign_key_field_name = 'comments'


class CommentDetailViewSet(TransactionRetrieveUpdateDestroyMixin, AGModelGenericViewSet):
    serializer_class = handgrading_serializers.CommentSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda comment: comment.handgrading_result.handgrading_rubric.project.course)
    ]
    model_manager = handgrading_models.Comment.objects.select_related(
        'handgrading_result__handgrading_rubric__project__course'
    )
