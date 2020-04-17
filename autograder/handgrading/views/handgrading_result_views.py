import copy
import itertools
from collections import OrderedDict

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import transaction
from django.db.models import Prefetch
from drf_composable_permissions.p import P
from rest_framework import exceptions, mixins, permissions, response, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission

import autograder.core.models as ag_models
import autograder.handgrading.models as hg_models
import autograder.rest_api.permissions as ag_permissions
from autograder import utils
from autograder.core.models.get_ultimate_submissions import get_ultimate_submission
from autograder.rest_api.schema import (AGPatchViewSchemaMixin, AGRetrieveViewSchemaMixin, APITags,
                                        CustomViewDict, CustomViewSchema, as_content_obj,
                                        as_paginated_content_obj, as_schema_ref)
from autograder.rest_api.size_file_response import SizeFileResponse
from autograder.rest_api.views.ag_model_views import (AGModelAPIView, NestedModelView,
                                                      convert_django_validation_error,
                                                      handle_object_does_not_exist_404,
                                                      require_query_params)
from django.utils.decorators import method_decorator

is_admin = ag_permissions.is_admin(lambda group: group.project.course)
is_staff = ag_permissions.is_staff(lambda group: group.project.course)
is_handgrader = ag_permissions.is_handgrader(lambda group: group.project.course)
can_view_project = ag_permissions.can_view_project(lambda group: group.project)


class HandgradingResultsPublished(BasePermission):
    def has_object_permission(self, request, view, group: ag_models.Group):
        return group.project.handgrading_rubric.show_grades_and_rubric_to_students


student_permission = (
    P(ag_permissions.IsReadOnly)
    & P(can_view_project)
    & P(ag_permissions.is_group_member())
    & P(HandgradingResultsPublished)
)


class _HandgradingResultViewSchema(
    AGRetrieveViewSchemaMixin, AGPatchViewSchemaMixin, CustomViewSchema
):
    def __init__(self, data: CustomViewDict):
        super().__init__([APITags.handgrading_results], data, hg_models.HandgradingResult)


class HandgradingResultView(NestedModelView):
    schema = _HandgradingResultViewSchema({
        'POST': {
            'operation_id': 'getOrCreateHandgradingResult',
            'responses': {
                '200': {
                    'description': 'A HandgradingResult already exists for the group. '
                                   'That HandgradingResult is returned.',
                    'content': as_content_obj(hg_models.HandgradingResult)
                },
                '201': {
                    'description': 'A new HandgradingResult was created for the group.',
                    'content': as_content_obj(hg_models.HandgradingResult)
                }
            }
        },

        'DELETE': {'operation_id': 'deleteHandgradingResult'}
    })

    permission_classes = [
        P(is_admin) | P(is_staff) | P(is_handgrader) | student_permission
    ]

    pk_key = 'group_pk'
    model_manager = ag_models.Group.objects.select_related(
        'project__course'
    )

    @handle_object_does_not_exist_404
    def get(self, request, *args, **kwargs):
        group: ag_models.Group = self.get_object()
        return response.Response(group.handgrading_result.to_dict())

    @transaction.atomic()
    def post(self, *args, **kwargs):
        """
        Creates a new HandgradingResult for the specified Group, or returns
        an already existing one.
        """
        group: ag_models.Group = self.get_object()
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

        handgrading_result, created = hg_models.HandgradingResult.objects.get_or_create(
            defaults={'submission': ultimate_submission},
            handgrading_rubric=handgrading_rubric,
            group=group
        )

        for criterion in handgrading_rubric.criteria.all():
            hg_models.CriterionResult.objects.get_or_create(
                defaults={'selected': False},
                criterion=criterion,
                handgrading_result=handgrading_result,
            )

        return response.Response(
            handgrading_result.to_dict(),
            status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    @convert_django_validation_error
    @transaction.atomic()
    @handle_object_does_not_exist_404
    def patch(self, request, *args, **kwargs):
        group = self.get_object()  # type: ag_models.Group
        is_admin = group.project.course.is_admin(request.user)
        is_staff = group.project.course.is_staff(request.user)
        can_adjust_points = (
            is_admin or is_staff
            or group.project.course.is_handgrader(request.user)
            and group.project.handgrading_rubric.handgraders_can_adjust_points)

        if 'points_adjustment' in self.request.data and not can_adjust_points:
            raise PermissionDenied

        handgrading_result = group.handgrading_result
        handgrading_result.validate_and_update(**request.data)
        return response.Response(handgrading_result.to_dict())

    @transaction.atomic()
    @handle_object_does_not_exist_404
    def delete(self, *args, **kwargs):
        group = self.get_object()  # type: ag_models.Group
        group.handgrading_result.delete()

        return response.Response(status=status.HTTP_204_NO_CONTENT)


class HandgradingResultFileContentView(NestedModelView):
    schema = CustomViewSchema([APITags.handgrading_results], {
        'GET': {
            'operation_id': 'getHandgradingResultFile',
            'parameters': [{
                'name': 'filename',
                'in': 'query',
                'description': 'The name of a submitted file to return.',
                'schema': {'type': 'string'}
            }],
            'responses': {
                '200': {
                    'content': {
                        'application/octet-stream': {
                            'schema': {
                                'type': 'string',
                                'format': 'binary'
                            }
                        }
                    }
                }
            }
        }
    })

    permission_classes = [
        P(is_admin) | P(is_staff) | P(is_handgrader) | student_permission
    ]

    pk_key = 'group_pk'
    model_manager = ag_models.Group.objects.select_related(
        'project__course'
    )

    @method_decorator(require_query_params('filename'))
    @handle_object_does_not_exist_404
    def get(self, request, *args, **kwargs):
        group: ag_models.Group = self.get_object()
        filename = request.query_params['filename']
        return SizeFileResponse(group.handgrading_result.submission.get_file(filename))


class HandgradingResultHasCorrectSubmissionView(NestedModelView):
    schema = CustomViewSchema([APITags.handgrading_results], {
        'GET': {
            'operation_id': 'handgradingResultHasCorrectSubmission',
            'responses': {
                '200': {
                    'content': {
                        'application/json': {
                            'schema': {'type': 'boolean'}
                        }
                    }
                }
            }
        }
    })
    permission_classes = [
        P(is_admin) | P(is_staff) | P(is_handgrader) | student_permission
    ]

    pk_key = 'group_pk'
    model_manager = ag_models.Group.objects.select_related(
        'project__course'
    )

    @handle_object_does_not_exist_404
    def get(self, *args, **kwargs):
        """
        Returns true if the submission linked to the group's handgrading result
        is the same as that group's current final graded submission.
        """
        group: ag_models.Group = self.get_object()
        return response.Response(
            data=group.handgrading_result.submission == get_ultimate_submission(group),
            status=status.HTTP_200_OK
        )


is_handgrader_or_staff = (P(ag_permissions.is_staff(lambda project: project.course))
                          | P(ag_permissions.is_handgrader(lambda project: project.course)))


class HandgradingResultPaginator(PageNumberPagination):
    page_size = 500
    page_size_query_param = 'page_size'
    max_page_size = 1000


class ListHandgradingResultsView(AGModelAPIView):
    schema = CustomViewSchema([APITags.projects, APITags.handgrading_results], {
        'GET': {
            'operation_id': 'listHandgradingResults',
            'parameters': [
                {'$ref': '#/components/parameters/page'},
                {
                    'name': 'page_size',
                    'in': 'query',
                    'description': 'The page size. Maximum value is {}'.format(
                        HandgradingResultPaginator.max_page_size),
                    'schema': {
                        'type': 'integer',
                        'default': HandgradingResultPaginator.page_size,
                        'maximum': HandgradingResultPaginator.max_page_size,
                    }
                },
                {'$ref': '#/components/parameters/includeStaff'},
            ],
            'responses': {
                '200': {
                    'content': as_paginated_content_obj({
                        'allOf': [
                            as_schema_ref(ag_models.Group),
                            {
                                'type': 'object',
                                'properties': {
                                    'handgrading_result': {
                                        'description': (
                                            'When this value is null, indicates that '
                                            'handgrading has not started for this group.'
                                        ),
                                        'type': 'object',
                                        'properties': {
                                            'finished_grading': {'type': 'boolean'},
                                            'total_points': {'type': 'number', 'format': 'double'},
                                            'total_points_possible': {
                                                'type': 'number', 'format': 'double'
                                            },
                                        }
                                    }
                                }
                            }
                        ]
                    })
                }
            }
        }
    })

    permission_classes = [is_handgrader_or_staff]

    model_manager = ag_models.Project.objects

    api_tags = [APITags.projects, APITags.handgrading_results]

    @handle_object_does_not_exist_404
    def get(self, *args, **kwargs):
        project = self.get_object()  # type: ag_models.Project

        hg_result_queryset = hg_models.HandgradingResult.objects.select_related(
            'handgrading_rubric__project',
            'group',
            'submission'
        ).prefetch_related(
            'handgrading_rubric__annotations',
            'handgrading_rubric__criteria',
            'criterion_results__criterion__handgrading_rubric',
            'applied_annotations__annotation__handgrading_rubric',
            'applied_annotations',
            'comments'
        )

        groups = project.groups.prefetch_related(
            'submissions',
            Prefetch('handgrading_result', hg_result_queryset),
            Prefetch('members', User.objects.order_by('username')),
        ).all()

        include_staff = self.request.query_params.get('include_staff', 'true') == 'true'
        if not include_staff:
            staff = list(
                itertools.chain(project.course.staff.all(),
                                project.course.admins.all())
            )
            groups = groups.exclude(members__in=staff)

        paginator = HandgradingResultPaginator()
        page = paginator.paginate_queryset(queryset=groups, request=self.request, view=self)

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
