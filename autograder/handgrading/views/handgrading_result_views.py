from django.http import FileResponse
from django.http import Http404
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from drf_composable_permissions.p import P
from rest_framework import status
from rest_framework.permissions import BasePermission

from autograder.core.models.get_ultimate_submissions import get_ultimate_submission

from rest_framework import response, mixins

import autograder.core.models as ag_models
import autograder.handgrading.models as handgrading_models
import autograder.handgrading.serializers as handgrading_serializers
import autograder.rest_api.permissions as ag_permissions
from autograder.rest_api.views.ag_model_views import AGModelGenericView

is_admin_or_read_only_staff = ag_permissions.is_admin_or_read_only_staff(
    lambda group: group.project.course)
is_handgrader = ag_permissions.is_handgrader(lambda group: group.project.course)
can_view_project = ag_permissions.can_view_project(lambda group: group.project)


class HandgradingResultsPublished(BasePermission):
    def has_object_permission(self, request, view, group: ag_models.SubmissionGroup):
        return group.project.handgrading_rubric.show_grades_and_rubric_to_students


student_permission = (
    P(ag_permissions.IsReadOnly) &
    P(can_view_project) &
    P(ag_permissions.is_group_member()) &
    P(HandgradingResultsPublished))


class HandgradingResultView(mixins.RetrieveModelMixin,
                            mixins.CreateModelMixin,
                            mixins.UpdateModelMixin,
                            AGModelGenericView):
    serializer_class = handgrading_serializers.HandgradingResultSerializer
    permission_classes = [
        (P(is_admin_or_read_only_staff) | P(is_handgrader) | student_permission)
    ]

    pk_key = 'group_pk'
    model_manager = ag_models.SubmissionGroup.objects.select_related(
        'project__course'
    )
    one_to_one_field_name = 'submission_group'
    reverse_one_to_one_field_name = 'handgrading_result'

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        try:
            group = self.get_object()  # type: ag_models.SubmissionGroup

            if 'filename' not in request.query_params:
                return response.Response(self.get_serializer(group.handgrading_result).data)

            submission = group.handgrading_result.submission

            filename = request.query_params['filename']
            return FileResponse(submission.get_file(filename))
        except ObjectDoesNotExist:
            return response.Response(status=status.HTTP_404_NOT_FOUND)

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
            submission_group=group)

        for criterion in handgrading_rubric.criteria.all():
            handgrading_models.CriterionResult.objects.get_or_create(
                defaults={'selected': False},
                criterion=criterion,
                handgrading_result=handgrading_result,
            )

        serializer = self.get_serializer(handgrading_result)
        return response.Response(
            serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        pass
