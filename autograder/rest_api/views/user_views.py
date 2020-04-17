from typing import List, Mapping, Sequence

from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import decorators, mixins, permissions, response
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.views import APIView

import autograder.core.models as ag_models
from autograder.rest_api.schema import (AGDetailViewSchemaGenerator,
                                        AGListCreateViewSchemaGenerator, APITags, ContentObj,
                                        ContentTypeVal, CustomViewSchema, MediaTypeObject,
                                        RequestParam)
from autograder.rest_api.serialize_user import serialize_user
from autograder.rest_api.views.ag_model_views import (AGModelAPIView, AGModelDetailView,
                                                      AlwaysIsAuthenticatedMixin, NestedModelView,
                                                      require_body_params, require_query_params)


class _Permissions(permissions.BasePermission):
    def has_permission(self, *args, **kwargs):
        return True

    def has_object_permission(self, request, view, ag_test):
        return view.kwargs['pk'] == request.user.pk


class CurrentUserView(AGModelAPIView):
    schema = AGDetailViewSchemaGenerator(tags=[APITags.users], api_class=User)

    def get(self, *args, **kwargs):
        return response.Response(serialize_user(self.request.user))


class UserDetailView(AGModelDetailView):
    schema = AGDetailViewSchemaGenerator(tags=[APITags.users])
    permission_classes = [_Permissions]
    model_manager = User.objects

    def get(self, *args, **kwargs):
        return self.do_get()

    def serialize_object(self, obj):
        return serialize_user(obj)


class _UserCoursesViewBase(NestedModelView):
    schema = AGListCreateViewSchemaGenerator(
        tags=[APITags.users, APITags.courses],
        api_class=ag_models.Course
    )

    model_manager = User.objects

    permission_classes = [_Permissions]

    def get(self, *args, **kwargs):
        return self.do_list()


class CoursesIsAdminForView(_UserCoursesViewBase):
    nested_field_name = 'courses_is_admin_for'


class CoursesIsStaffForView(_UserCoursesViewBase):
    nested_field_name = 'courses_is_staff_for'


class CoursesIsEnrolledInView(_UserCoursesViewBase):
    nested_field_name = 'courses_is_enrolled_in'


class CoursesIsHandgraderForView(_UserCoursesViewBase):
    nested_field_name = 'courses_is_handgrader_for'


class GroupsIsMemberOfView(NestedModelView):
    schema = AGListCreateViewSchemaGenerator(
        tags=[APITags.users, APITags.groups],
        api_class=ag_models.Group
    )

    model_manager = User.objects
    nested_field_name = 'groups_is_member_of'

    permission_classes = [_Permissions]

    def get(self, *args, **kwargs):
        return self.do_list()


class _InvitationViewBase(NestedModelView):
    schema = AGListCreateViewSchemaGenerator(
        tags=[APITags.users, APITags.groups],
        api_class=ag_models.GroupInvitation
    )

    model_manager = User.objects

    permission_classes = [_Permissions]

    def get(self, *args, **kwargs):
        return self.do_list()


class GroupInvitationsSentView(_InvitationViewBase):
    nested_field_name = 'group_invitations_sent'


class GroupInvitationsReceivedView(_InvitationViewBase):
    nested_field_name = 'group_invitations_received'


class CurrentUserCanCreateCoursesView(AlwaysIsAuthenticatedMixin, APIView):
    schema = CustomViewSchema([APITags.users], {
        'GET': {
            'operation_id': 'currentUserCanCreateCourses',
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

    def get(self, request: Request, *args, **kwargs):
        """
        Indicates whether the current user can create empty courses.
        """
        return response.Response(request.user.has_perm('core.create_course'))


class UserLateDaysView(AlwaysIsAuthenticatedMixin, APIView):
    _LATE_DAYS_REMAINING_BODY: ContentObj = {
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

    _PARAMS: Sequence[RequestParam] = [
        {
            'name': 'username_or_id',
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
        },
        {
            'name': 'course_pk',
            'in': 'query',
            'required': True,
            'schema': {'type': 'integer', 'format': 'id'}
        }
    ]

    schema = CustomViewSchema([APITags.courses, APITags.users], {
        'GET': {
            'operation_id': 'getUserLateDaysRemaining',
            'parameters': _PARAMS,
            'responses': {
                '200': {'content': _LATE_DAYS_REMAINING_BODY}
            }
        },
        'PUT': {
            'operation_id': 'setUserLateDaysRemaining',
            'parameters': _PARAMS,
            'request': {'content': _LATE_DAYS_REMAINING_BODY},
            'responses': {
                '200': {'content': _LATE_DAYS_REMAINING_BODY}
            }
        }
    })

    @method_decorator(require_query_params('course_pk'))
    def get(self, request: Request, *args, **kwargs):
        try:
            user = get_object_or_404(User.objects, pk=int(kwargs['username_or_id']))
        except ValueError:
            user = get_object_or_404(User.objects, username=kwargs['username_or_id'])

        course = get_object_or_404(ag_models.Course.objects, pk=request.query_params['course_pk'])
        remaining = ag_models.LateDaysRemaining.objects.get_or_create(user=user, course=course)[0]

        self._check_read_permissions(remaining)

        return response.Response({'late_days_remaining': remaining.late_days_remaining})

    @method_decorator(require_body_params('late_days_remaining'))
    def put(self, request: Request, *args, **kwargs):
        try:
            user = get_object_or_404(User.objects, pk=int(kwargs['username_or_id']))
        except ValueError:
            user = get_object_or_404(User.objects, username=kwargs['username_or_id'])

        course = get_object_or_404(ag_models.Course.objects, pk=request.query_params['course_pk'])

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
