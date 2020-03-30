from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from drf_composable_permissions.p import P
from rest_framework import response

import autograder.core.models as ag_models
import autograder.handgrading.models as handgrading_models
import autograder.handgrading.serializers as handgrading_serializers
import autograder.rest_api.permissions as ag_permissions
from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, TransactionRetrievePatchDestroyMixin, RetrieveCreateNestedModelViewSet)
from autograder.rest_api.views.schema_generation import APITags

is_admin_or_read_only = ag_permissions.is_admin_or_read_only_staff(lambda project: project.course)
is_handgrader = ag_permissions.is_handgrader(lambda project: project.course)


# FIXME: Phase out RetrieveCreateNestedModelViewSet, just implement retrieve here
# as a one-off
class HandgradingRubricRetrieveCreateViewSet(RetrieveCreateNestedModelViewSet):
    serializer_class = handgrading_serializers.HandgradingRubricSerializer
    permission_classes = [
        (P(is_admin_or_read_only) | (P(is_handgrader) & P(ag_permissions.IsReadOnly)))]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')
    to_one_field_name = 'project'
    reverse_to_one_field_name = 'handgrading_rubric'

    api_tags = [APITags.handgrading_rubrics]

    def retrieve(self, *args, **kwargs):
        project = self.get_object()
        try:
            handgrading_rubric = project.handgrading_rubric
        except ObjectDoesNotExist:
            raise Http404('Project {} has no HandgradingRubric (handgrading not enabled)'
                          .format(project.pk))

        serializer = self.get_serializer(handgrading_rubric)
        return response.Response(serializer.data)


class HandgradingRubricDetailViewSet(TransactionRetrievePatchDestroyMixin, AGModelGenericViewSet):
    serializer_class = handgrading_serializers.HandgradingRubricSerializer
    permission_classes = [
        ag_permissions.is_admin_or_read_only_staff(
            lambda handgrading_rubric: handgrading_rubric.project.course)
    ]
    model_manager = handgrading_models.HandgradingRubric.objects.select_related(
        'project__course',
    ).prefetch_related(
        'criteria',
        'annotations'
    )
