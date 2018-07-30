import copy
import itertools
from collections import OrderedDict

from django.utils import timezone
from drf_composable_permissions.p import P
from drf_yasg import openapi
from drf_yasg.openapi import Parameter, Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission

from autograder.core.models.get_ultimate_submissions import get_ultimate_submissions
from autograder.core.submission_feedback import AGTestPreLoader
from autograder.rest_api.serialize_ultimate_submission_results import (
    serialize_ultimate_submission_results)
from autograder.rest_api.views.ag_model_views import AGModelAPIView
import autograder.rest_api.permissions as ag_permissions
import autograder.core.models as ag_models
from autograder.rest_api.views.schema_generation import APITags, AGModelSchemaBuilder


class _UltimateSubmissionsAvailable(BasePermission):
    def has_object_permission(self, request, view, project: ag_models.Project):
        closing_time_past = project.closing_time is None or project.closing_time < timezone.now()
        return not project.hide_ultimate_submission_fdbk and closing_time_past


def _build_ultimate_submission_result_schema():
    ultimate_submission_schema = Schema(
        type='object',
        properties=copy.deepcopy(
            AGModelSchemaBuilder.get().get_schema(ag_models.Submission).properties)
    )
    assert (ultimate_submission_schema.properties is not
            AGModelSchemaBuilder.get().get_schema(ag_models.Submission).properties)

    ultimate_submission_schema.properties['results'] = Schema(
        type='object',
        properties=OrderedDict([
            ('total_points', Schema(type='string(float)')),
            ('total_points_possible', Schema(type='string(float)')),

            (
                'ag_test_suite_results',
                Schema(type='AGTestSuiteResultFeedback',
                       description='Only included if full_results is true.')
            ),
            (
                'student_test_suite_results',
                Schema(type='StudentTestSuiteResultFeedback',
                       description='Only included if full_results is true.')
            )
        ])
    )

    ultimate_submission_schema.properties.move_to_end('results', last=False)

    return Schema(
        type='object',
        properties=OrderedDict([
            ('username', Schema(type='string')),
            ('group', AGModelSchemaBuilder.get().get_schema(ag_models.Group)),
            ('ultimate_submission', ultimate_submission_schema)
        ])
    )


_all_ultimate_submission_results_schema = Schema(
    type='object',
    properties=OrderedDict([
        ('count', openapi.Schema(type=openapi.TYPE_INTEGER)),
        ('next', openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI)),
        ('previous', openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI)),
        ('results', Schema(
            type='array',
            items=_build_ultimate_submission_result_schema()

        )),
    ])
)


class UltimateSubmissionPaginator(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'groups_per_page'
    max_page_size = 200


class AllUltimateSubmissionResults(AGModelAPIView):
    permission_classes = (
        P(ag_permissions.is_admin())
        | (P(ag_permissions.is_staff()) & P(_UltimateSubmissionsAvailable)),)
    model_manager = ag_models.Project
    pk_key = 'project_pk'

    api_tags = (APITags.submissions,)

    @swagger_auto_schema(
        manual_parameters=[
            Parameter(name='page', type='integer', in_='query'),
            Parameter(name='groups_per_page', type='integer', in_='query',
                      default=UltimateSubmissionPaginator.page_size,
                      description='Max groups per page: {}'.format(
                          UltimateSubmissionPaginator.max_page_size)),
            Parameter(
                name='full_results', type='string', enum=['true', 'false'], in_='query',
                description='When true, includes all SubmissionResultFeedback fields. '
                            'Defaults to false.'
            ),
            Parameter(
                name='include_staff', type='string', enum=['true', 'false'], in_='query',
                description='When false, excludes staff and admin users '
                            'from the results. Defaults to true.'
            )
        ],
        responses={'200': _all_ultimate_submission_results_schema}
    )
    def get(self, *args, **kwargs):
        project: ag_models.Project = self.get_object()

        include_staff = self.request.query_params.get('include_staff', 'true') == 'true'
        if include_staff:
            groups = project.groups.all()
        else:
            staff = list(
                itertools.chain(project.course.staff.all(),
                                project.course.admins.all())
            )
            groups = project.groups.exclude(members__in=staff)

        full_results = self.request.query_params.get('full_results') == 'true'

        paginator = UltimateSubmissionPaginator()
        page = paginator.paginate_queryset(queryset=groups, request=self.request, view=self)

        ag_test_preloader = AGTestPreLoader(project)
        ultimate_submissions = get_ultimate_submissions(
            project, *page, ag_test_preloader=ag_test_preloader)

        results = serialize_ultimate_submission_results(
            ultimate_submissions, full_results=full_results)

        return paginator.get_paginated_response(results)
