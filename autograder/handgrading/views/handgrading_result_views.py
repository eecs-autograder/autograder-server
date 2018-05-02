import copy
from django.contrib.auth.models import User
from django.db.models import Prefetch
from django.http import FileResponse
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from drf_yasg.openapi import Parameter, Schema
from drf_yasg.utils import swagger_auto_schema

from rest_framework import status, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework import response, mixins, exceptions
from drf_composable_permissions.p import P

import autograder.core.models as ag_models
from autograder.core.models.get_ultimate_submissions import get_ultimate_submission
import autograder.handgrading.models as handgrading_models
import autograder.handgrading.serializers as handgrading_serializers
import autograder.rest_api.permissions as ag_permissions
from autograder.rest_api.views.ag_model_views import (
    handle_object_does_not_exist_404, AGModelAPIView, AGModelGenericViewSet)
from autograder import utils
from autograder.rest_api.views.schema_generation import APITags, AGModelSchemaBuilder

is_admin_or_read_only_staff = ag_permissions.is_admin_or_read_only_staff(
    lambda group: group.project.course)
is_handgrader = ag_permissions.is_handgrader(lambda group: group.project.course)
can_view_project = ag_permissions.can_view_project(lambda group: group.project)


class HandgradingResultsPublished(BasePermission):
    def has_object_permission(self, request, view, group: ag_models.Group):
        return group.project.handgrading_rubric.show_grades_and_rubric_to_students


student_permission = (
    P(ag_permissions.IsReadOnly) &
    P(can_view_project) &
    P(ag_permissions.is_group_member()) &
    P(HandgradingResultsPublished))


class HandgradingResultView(AGModelGenericViewSet):
    serializer_class = handgrading_serializers.HandgradingResultSerializer
    permission_classes = [
        (P(is_admin_or_read_only_staff) | P(is_handgrader) | student_permission)
    ]

    pk_key = 'group_pk'
    model_manager = ag_models.Group.objects.select_related(
        'project__course'
    )
    one_to_one_field_name = 'group'
    reverse_one_to_one_field_name = 'handgrading_result'

    api_tags = [APITags.handgrading_results]

    @swagger_auto_schema(
        manual_parameters=[
            Parameter(
                name='filename', in_='query', type='string',
                description='The name of a submitted file. When this parameter is included, '
                            'this endpoint will return the contents of the requested file.')
        ]
    )
    @handle_object_does_not_exist_404
    def retrieve(self, request, *args, **kwargs):
        group = self.get_object()  # type: ag_models.Group

        if 'filename' not in request.query_params:
            return response.Response(self.get_serializer(group.handgrading_result).data)

        submission = group.handgrading_result.submission

        filename = request.query_params['filename']
        return FileResponse(submission.get_file(filename))

    @transaction.atomic()
    def create(self, *args, **kwargs):
        """
        Creates a new HandgradingResult for the specified Group, or returns
        an already existing one.
        """
        group = self.get_object()
        try:
            handgrading_rubric = group.project.handgrading_rubric
        except ObjectDoesNotExist:
            raise exceptions.ValidationError(
                {'handgrading_rubric':
                    'Project {} has not enabled handgrading'.format(group.project.pk)})

        ultimate_submission = get_ultimate_submission(group)
        if not ultimate_submission:
            raise exceptions.ValidationError(
                {'num_submissions': 'Group {} has no submissions'.format(group.pk)})

        handgrading_result, created = handgrading_models.HandgradingResult.objects.get_or_create(
            defaults={'submission': ultimate_submission},
            handgrading_rubric=handgrading_rubric,
            group=group)

        for criterion in handgrading_rubric.criteria.all():
            handgrading_models.CriterionResult.objects.get_or_create(
                defaults={'selected': False},
                criterion=criterion,
                handgrading_result=handgrading_result,
            )

        serializer = self.get_serializer(handgrading_result)
        return response.Response(
            serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @transaction.atomic()
    @handle_object_does_not_exist_404
    def partial_update(self, request, *args, **kwargs):
        group = self.get_object()  # type: ag_models.Group
        is_admin = group.project.course.is_admin(request.user)
        can_adjust_points = (
            is_admin or
            group.project.course.is_handgrader(request.user) and
            group.project.handgrading_rubric.handgraders_can_adjust_points)

        if 'points_adjustment' in self.request.data and not can_adjust_points:
            raise PermissionDenied

        handgrading_result = group.handgrading_result
        handgrading_result.validate_and_update(**request.data)
        return response.Response(self.get_serializer(handgrading_result).data)


is_handgrader_or_staff = (P(ag_permissions.is_staff(lambda project: project.course)) |
                          P(ag_permissions.is_handgrader(lambda project: project.course)))


def _buid_minimal_handgrading_resuit_schema():
    group_with_handgrading_result_schema = Schema(
        type='object',
        properties=copy.deepcopy(AGModelSchemaBuilder.get().get_schema(ag_models.Group).properties)
    )
    assert (group_with_handgrading_result_schema.properties is not
            AGModelSchemaBuilder.get().get_schema(ag_models.Group).properties)
    group_with_handgrading_result_schema.properties['handgrading_result'] = Schema(
        title='MinimalHandgradingResult',
        type='object',
        properties={
            'finished_grading': Schema(
                type='boolean',
                description="Indicates whether a human grader "
                            "has finished grading this group's code.",
            ),
            'total_points': Schema(
                type='float',
            ),
            'total_points_possible': Schema(
                type='float',
            ),
        }
    )

    return group_with_handgrading_result_schema


_handgrading_results_schema = Schema(
    type='object',
    properties={
        'results': Schema(
            type='array',
            items=_buid_minimal_handgrading_resuit_schema()

        )
    }

)


class ListHandgradingResultsView(AGModelAPIView):
    permission_classes = [is_handgrader_or_staff]

    model_manager = ag_models.Project.objects

    api_tags = [APITags.projects, APITags.handgrading_results]

    @swagger_auto_schema(responses={'200': _handgrading_results_schema})
    @handle_object_does_not_exist_404
    def get(self, *args, **kwargs):
        project = self.get_object()  # type: ag_models.Project

        hg_result_queryset = handgrading_models.HandgradingResult.objects.select_related(
            'handgrading_rubric__project',
            'group',
            'submission'
        ).prefetch_related(
            'handgrading_rubric__annotations',
            'handgrading_rubric__criteria',
            'criterion_results__criterion__handgrading_rubric',
            'applied_annotations__annotation__handgrading_rubric',
            'applied_annotations__location',
            'comments__location'
        )

        groups = project.groups.prefetch_related(
            'submissions',
            Prefetch('handgrading_result', hg_result_queryset),
            Prefetch('members', User.objects.order_by('username')),
        ).all()

        paginator = HandgradingResultPaginator()
        page = paginator.paginate_queryset(
            queryset=groups, request=self.request, view=self)

        results = []
        for group in page:
            data = group.to_dict()
            if not hasattr(group, 'handgrading_result'):
                data['handgrading_result'] = None
            else:
                data['handgrading_result'] = utils.filter_dict(
                    group.handgrading_result.to_dict(),
                    ['finished_grading', 'total_points', 'total_points_possible'])

            results.append(data)

        return paginator.get_paginated_response(results)


class HandgradingResultPaginator(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
