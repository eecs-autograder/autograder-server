import autograder.core.models as ag_models
import autograder.handgrading.models as handgrading_models
import autograder.handgrading.serializers as handgrading_serializers
import autograder.rest_api.permissions as ag_permissions
from rest_framework import response
from django.http import Http404
from django.db import transaction
from autograder.core.models.get_ultimate_submissions import get_ultimate_submission

from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, RetrieveCreateNestedModelView, TransactionRetrieveUpdateDestroyMixin,
)


class HandgradingResultRetrieveCreateView(RetrieveCreateNestedModelView):
    serializer_class = handgrading_serializers.HandgradingResultSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda submission_group: submission_group.project.course)]

    pk_key = 'group_pk'
    model_manager = ag_models.SubmissionGroup.objects.select_related(
        'project__course'
    )
    one_to_one_field_name = 'submission_group'
    reverse_one_to_one_field_name = 'handgrading_result'

    @transaction.atomic()
    def retrieve(self, *args, **kwargs):
        group = self.get_object()
        try:
            handgrading_result = getattr(group, self.reverse_one_to_one_field_name)
        except:
            # print(group.to_dict())
            ultimate_submission = get_ultimate_submission(group.project, group.pk)
            # print(ultimate_submission)
            if not ultimate_submission:
                raise Http404('Group {} has no submissions'.format(group.pk))

            handgrading_rubric = getattr(group.project, 'handgrading_rubric')
            handgrading_result = handgrading_models.HandgradingResult.objects.validate_and_create(
                submission=ultimate_submission,
                handgrading_rubric=handgrading_rubric,
                submission_group=group,
            )

        serializer = self.get_serializer(handgrading_result)
        return response.Response(serializer.data)


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
