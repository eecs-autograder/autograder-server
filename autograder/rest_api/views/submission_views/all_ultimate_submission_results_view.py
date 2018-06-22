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

from autograder.core.models.get_ultimate_submissions import get_ultimate_submissions, \
    get_ultimate_submission
from autograder.core.submission_feedback import AGTestPreLoader, SubmissionResultFeedback
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
            ('total_points', Schema(
                type='float',
            )),
            ('total_points_possible', Schema(
                type='float',
            )),
        ])
    )

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
                description='When true, includes additional SubmissionResultFeedback details. '
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

        results = []
        for submission_fdbk in ultimate_submissions:
            submission = submission_fdbk._submission
            group = submission.group
            if group.extended_due_date is not None and group.extended_due_date > timezone.now():
                submission_data = None
            else:
                submission_data = self._get_submission_data_with_results(
                    submission_fdbk, full_results)

            group_data = group.to_dict()

            for username in group.member_names:
                user_data = {
                    'username': username,
                    'group': group_data,
                }

                if username in submission.does_not_count_for:
                    user_ultimate_submission = get_ultimate_submission(
                        group, group.members.get(username=username))
                    # NOTE: Do NOT overwrite submission_data
                    user_submission_data = self._get_submission_data_with_results(
                        SubmissionResultFeedback(
                            user_ultimate_submission, ag_models.FeedbackCategory.max,
                            ag_test_preloader),
                        full_results
                    )
                    user_data['ultimate_submission'] = user_submission_data
                else:
                    user_data['ultimate_submission'] = submission_data

                results.append(user_data)

        return paginator.get_paginated_response(results)

    def _get_submission_data_with_results(self, submission_fdbk: SubmissionResultFeedback,
                                          full_results: bool):
        submission_data = submission_fdbk.submission.to_dict()

        if not full_results:
            submission_results = {
                'total_points': submission_fdbk.total_points,
                'total_points_possible': submission_fdbk.total_points_possible
            }
        else:
            submission_results = submission_fdbk.to_dict()

        submission_data['results'] = submission_results

        return submission_data
