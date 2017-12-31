from rest_framework import response, status
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import Http404
from django.db import transaction
from drf_composable_permissions.p import P

import autograder.core.models as ag_models
import autograder.handgrading.models as handgrading_models
import autograder.handgrading.serializers as handgrading_serializers

import autograder.rest_api.permissions as ag_permissions
from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, TransactionRetrieveUpdateDestroyMixin, RetrieveCreateNestedModelView)


class HandgradingRubricRetrieveCreateView(RetrieveCreateNestedModelView):
    serializer_class = handgrading_serializers.HandgradingRubricSerializer
    permission_classes = [
        (P(ag_permissions.is_admin_or_read_only_staff(lambda project: project.course)) |
        P(ag_permissions.is_handgrader(lambda project: project.course)))]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')
    one_to_one_field_name = 'project'
    reverse_one_to_one_field_name = 'handgrading_rubric'

    def retrieve(self, *args, **kwargs):
        project = self.get_object()
        try:
            handgrading_rubric = project.handgrading_rubric
        except ObjectDoesNotExist:
            raise Http404('Project {} has no HandgradingRubric (handgrading not enabled)'
                          .format(project.pk))

        serializer = self.get_serializer(handgrading_rubric)
        return response.Response(serializer.data)

    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        project = self.get_object()  # type: ag_models.Project
        is_admin = project.course.is_administrator(request.user)

        if not is_admin:
            raise PermissionDenied

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return response.Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class HandgradingRubricDetailViewSet(TransactionRetrieveUpdateDestroyMixin, AGModelGenericViewSet):
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
