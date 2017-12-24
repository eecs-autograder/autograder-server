import autograder.core.models as ag_models
import autograder.handgrading.models as handgrading_models
import autograder.handgrading.serializers as handgrading_serializers
import autograder.rest_api.permissions as ag_permissions
from rest_framework import response
from django.http import Http404
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from autograder.core.models.get_ultimate_submissions import get_ultimate_submission

from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, RetrieveCreateNestedModelView, TransactionRetrieveUpdateDestroyMixin,
)


class HandgradingResultView(RetrieveCreateNestedModelView):
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

    #
    #     try:
    #         filename = request.query_params['filename']
    #         return FileResponse(submission.get_file(filename))
    #     except KeyError:
    #         return response.Response(
    #             'Missing required query parameter "filename"',
    #             status=status.HTTP_400_BAD_REQUEST)
    #     except exceptions.ObjectDoesNotExist:
    #         return response.Response('File "{}" not found'.format(filename),
    #                                  status=status.HTTP_404_NOT_FOUND)


    @transaction.atomic()
    def create(self, *args, **kwargs):
        group = self.get_object()
        try:
            handgrading_rubric = group.project.handgrading_rubric
        except ObjectDoesNotExist:
            raise Http404('Project {} has not enabled handgrading (no handgrading rubric found)'
                          .format(group.project.pk))

        ultimate_submission = get_ultimate_submission(group.project, group.pk)

        if not ultimate_submission:
            raise Http404('Group {} has no submissions'.format(group.pk))

        handgrading_result, created = handgrading_models.HandgradingResult.objects.get_or_create(
            defaults={'submission': ultimate_submission},
            handgrading_rubric=handgrading_rubric,
            submission_group=group,
        )

        for criterion in handgrading_rubric.criteria.all():
            handgrading_models.CriterionResult.objects.get_or_create(
                defaults={'selected': False},
                criterion=criterion,
                handgrading_result=handgrading_result,
            )

        serializer = self.get_serializer(handgrading_result)
        return response.Response(serializer.data)
