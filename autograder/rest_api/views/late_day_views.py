from typing import Dict, Sequence

from django.contrib.auth.models import User
from django.db import transaction
from django.utils.decorators import method_decorator
from rest_framework import response
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.request import Request
from django.shortcuts import get_object_or_404

import autograder.rest_api.permissions as ag_permissions
import autograder.core.models as ag_models
from autograder.rest_api.schema import (
    AGListViewSchemaMixin,
    AGViewSchemaGenerator,
    APITags,
    ContentType,
    SchemaObject,
    ParameterObject,
    CustomViewSchema
)
from autograder.rest_api.views.ag_model_views import (
    AlwaysIsAuthenticatedMixin,
    NestedModelView,
    require_body_params
)


class ListLateDayUsagesSchemaGenerator(AGListViewSchemaMixin, AGViewSchemaGenerator):
    pass


class ListUserLateDayUsageHistoryView(NestedModelView):
    schema = ListLateDayUsagesSchemaGenerator(
        [APITags.courses, APITags.users],
        ag_models.LateDayUsageRecord,
        operation_id_overrides={'GET': 'listUserLateDayUsageHistory'}
    )
    permission_classes = [
        ag_permissions.is_staff(),
    ]
    model_manager = ag_models.Course.objects

    def get_nested_manager(self):
        course = self.get_object(pk_override=self.kwargs.get('course_pk'))

        try:
            user = get_object_or_404(User.objects, pk=int(self.kwargs['username_or_pk']))
        except ValueError:
            user = get_object_or_404(User.objects, username=self.kwargs['username_or_pk'])

        return course.late_day_usage_records.filter(user_pk=user.pk)

    def get(self, *args, **kwargs):
        return self.do_list()


class ListLateDayUsageHistoryView(NestedModelView):
    schema = ListLateDayUsagesSchemaGenerator(
        [APITags.courses],
        ag_models.LateDayUsageRecord
    )
    permission_classes = [
        ag_permissions.is_staff(),
    ]
    model_manager = ag_models.Course.objects
    nested_field_name = 'late_day_usage_records'
    pk_key = 'course_pk'

    def get(self, *args, **kwargs):
        return self.do_list()


class UserLateDaysView(AlwaysIsAuthenticatedMixin, APIView):
    _LATE_DAYS_REMAINING_BODY: Dict[ContentType, SchemaObject] = {
        'application/json': {
            'schema': {
                'type': 'object',
                'required': ['late_days_remaining'],
                'properties': {
                    'late_days_remaining': {'type': 'integer'}
                }
            }
        }
    }

    _PARAMS: Sequence[ParameterObject] = [
        {
            'name': 'course_pk',
            'in': 'path',
            'required': True,
            'schema': {'type': 'integer', 'format': 'id'}
        },
        {
            'name': 'username_or_pk',
            'in': 'path',
            'required': True,
            'description': 'The ID or username of the user.',
            'schema': {
                # Note: swagger-ui doesn't seem to be able to render
                # oneOf for params.
                'oneOf': [
                    {'type': 'string', 'format': 'username'},
                    {'type': 'integer', 'format': 'id'},
                ]
            }
        }
    ]

    schema = CustomViewSchema([APITags.courses, APITags.users], {
        'GET': {
            'operation_id': 'getUserLateDaysRemaining',
            'parameters': _PARAMS,
            'responses': {
                '200': {
                    'content': _LATE_DAYS_REMAINING_BODY,
                    'description': ''
                }
            }
        },
        'PUT': {
            'operation_id': 'setUserLateDaysRemaining',
            'parameters': _PARAMS,
            'request': {'content': _LATE_DAYS_REMAINING_BODY},
            'responses': {
                '200': {
                    'content': _LATE_DAYS_REMAINING_BODY,
                    'description': ''
                }
            }
        }
    })

    def get(self, request: Request, *args, **kwargs):
        try:
            user = get_object_or_404(User.objects, pk=int(kwargs['username_or_pk']))
        except ValueError:
            user = get_object_or_404(User.objects, username=kwargs['username_or_pk'])

        course = get_object_or_404(ag_models.Course.objects, pk=kwargs['course_pk'])
        remaining = ag_models.LateDaysRemaining.objects.get_or_create(user=user, course=course)[0]

        self._check_read_permissions(remaining)

        return response.Response({'late_days_remaining': remaining.late_days_remaining})

    @method_decorator(require_body_params('late_days_remaining'))
    def put(self, request: Request, *args, **kwargs):
        try:
            user = get_object_or_404(User.objects, pk=int(kwargs['username_or_pk']))
        except ValueError:
            user = get_object_or_404(User.objects, username=kwargs['username_or_pk'])

        course = get_object_or_404(ag_models.Course.objects, pk=kwargs['course_pk'])

        with transaction.atomic():
            remaining = ag_models.LateDaysRemaining.objects.select_for_update().get_or_create(
                user=user, course=course)[0]

            self._check_read_permissions(remaining)
            self._check_write_permissions(remaining)

            remaining.late_days_remaining = request.data['late_days_remaining']
            remaining.save()

            return response.Response({'late_days_remaining': remaining.late_days_remaining})

    def _check_read_permissions(self, remaining: ag_models.LateDaysRemaining):
        user = self.request.user
        if user == remaining.user:
            return

        if remaining.course.is_staff(user):
            return

        raise PermissionDenied

    def _check_write_permissions(self, remaining: ag_models.LateDaysRemaining):
        if not remaining.course.is_admin(self.request.user):
            raise PermissionDenied
