import itertools

from django.utils import timezone
from drf_composable_permissions.p import P
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
from autograder.core.models.get_ultimate_submissions import get_ultimate_submissions
from autograder.core.submission_feedback import AGTestPreLoader, SubmissionResultFeedback
from autograder.rest_api.schema import (
    APITags, CustomViewSchema, as_paginated_content_obj, as_schema_ref)
from autograder.rest_api.serialize_ultimate_submission_results import \
    serialize_ultimate_submission_results
from autograder.rest_api.views.ag_model_views import AGModelAPIView


class _UltimateSubmissionsAvailable(BasePermission):
    def has_object_permission(self, request, view, project: ag_models.Project):
        closing_time_past = project.closing_time is None or project.closing_time < timezone.now()
        return not project.hide_ultimate_submission_fdbk and closing_time_past


class UltimateSubmissionPaginator(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'groups_per_page'
    max_page_size = 200


class AllUltimateSubmissionResults(AGModelAPIView):
    schema = CustomViewSchema([APITags.submissions], {
        'GET': {
            'operation_id': 'getAllUltimateSubmissionResults',
            'parameters': [
                {'$ref': '#/components/parameters/page'},
                {
                    'name': 'groups_per_page',
                    'in': 'query',
                    'description': (
                        'The number of groups per page. '
                        'Note that this is NOT the same as the length of the "results" '
                        'array, as that array has one entry per student. '
                        'Maximum value is {}'.format(UltimateSubmissionPaginator.max_page_size)
                    ),
                    'schema': {
                        'type': 'integer',
                        'default': UltimateSubmissionPaginator.page_size,
                        'maximum': UltimateSubmissionPaginator.max_page_size,
                    }
                },
                {
                    'name': 'full_results',
                    'in': 'query',
                    'description': '''When "false", the submission result data
                        will not contain the "ag_test_suite_results"
                        or "mutation_test_suite_results" fields.
                        Defaults to "false".
                    '''.strip(),
                    'schema': {
                        'type': 'string',
                        'enum': ['true', 'false'],
                        'default': 'false',
                    }
                },
                {'$ref': '#/components/parameters/includeStaff'}
            ],
            'responses': {
                '200': {
                    'description': '',
                    'content': as_paginated_content_obj({
                        'properties': {
                            'username': {
                                'type': 'string',
                                'description': (
                                    'The username of the student this entry applies to. '
                                    'Note that in some (rare) cases involving late day tokens, '
                                    'users in the same group can have different '
                                    'ultimate submissions.'
                                )
                            },
                            'group': as_schema_ref(ag_models.Group),
                            'ultimate_submission': {
                                'allOf': [
                                    as_schema_ref(ag_models.Submission),
                                    {
                                        'type': 'object',
                                        'properties': {
                                            'results': as_schema_ref(SubmissionResultFeedback)
                                        }
                                    }
                                ],
                                'nullable': True
                            }
                        }
                    })
                }
            }
        }
    })

    permission_classes = [
        P(ag_permissions.is_admin())
        | (P(ag_permissions.is_staff()) & P(_UltimateSubmissionsAvailable))
    ]
    model_manager = ag_models.Project
    pk_key = 'project_pk'

    def get(self, *args, **kwargs):
        project: ag_models.Project = self.get_object()

        include_staff = self.request.query_params.get('include_staff', 'true') == 'true'
        groups = project.groups.prefetch_related('members')
        if include_staff:
            groups = groups.all()
        else:
            staff = list(
                itertools.chain(project.course.staff.all(),
                                project.course.admins.all())
            )
            groups = groups.exclude(members__in=staff)

        full_results = self.request.query_params.get('full_results') == 'true'

        paginator = UltimateSubmissionPaginator()
        page = paginator.paginate_queryset(queryset=groups, request=self.request, view=self)

        ag_test_preloader = AGTestPreLoader(project)
        ultimate_submissions = get_ultimate_submissions(
            project, filter_groups=page, ag_test_preloader=ag_test_preloader)

        results = serialize_ultimate_submission_results(
            ultimate_submissions, full_results=full_results)

        return paginator.get_paginated_response(results)
