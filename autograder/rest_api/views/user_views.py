from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import decorators, mixins, permissions, response
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.views import APIView

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api.schema import (AGDetailViewSchemaGenerator,
                                        AGListCreateViewSchemaGenerator)
from autograder.rest_api.serialize_user import serialize_user
from autograder.rest_api.views.ag_model_views import (
    AGModelAPIView, AGModelDetailView, AGModelGenericViewSet,
    AlwaysIsAuthenticatedMixin, NestedModelView, require_body_params,
    require_query_params)
from autograder.rest_api.views.schema_generation import APITags


class _Permissions(permissions.BasePermission):
    def has_permission(self, *args, **kwargs):
        return True

    def has_object_permission(self, request, view, ag_test):
        return view.kwargs['pk'] == request.user.pk


# _course_list_schema = Schema(
#     type='array', items=AGModelSchemaBuilder.get().get_schema(ag_models.Course))

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


class _RosterViewBase(NestedModelView):
    schema = AGListCreateViewSchemaGenerator(
        tags=[APITags.users, APITags.permissions, APITags.courses],
        api_class=ag_models.Course
    )

    model_manager = User.objects

    permission_classes = [_Permissions]

    def get(self, *args, **kwargs):
        return self.do_list()


class CoursesIsAdminForView(_RosterViewBase):
    nested_field_name = 'courses_is_admin_for'


class CoursesIsStaffForView(_RosterViewBase):
    nested_field_name = 'courses_is_staff_for'


class CoursesIsEnrolledInView(_RosterViewBase):
    nested_field_name = 'courses_is_enrolled_in'


class CoursesIsHandgraderForView(_RosterViewBase):
    nested_field_name = 'courses_is_handgrader_for'


class GroupsIsMemberOfView(NestedModelView):
    schema = AGListCreateViewSchemaGenerator(
        tags=[APITags.users, APITags.permissions, APITags.groups],
        api_class=ag_models.Group
    )

    model_manager = User.objects
    nested_field_name = 'groups_is_member_of'

    permission_classes = [_Permissions]

    def get(self, *args, **kwargs):
        return self.do_list()


class _InvitationViewBase(NestedModelView):
    schema = AGListCreateViewSchemaGenerator(
        tags=[APITags.users, APITags.permissions, APITags.groups],
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
    # swagger_schema = AGModelViewAutoSchema

    api_tags = [APITags.permissions]

    # @swagger_auto_schema(
    #     responses={
    #         '200': Schema(
    #             type='boolean',
    #             description='Whether or not the current user can create empty courses.'
    #         )
    #     }
    # )
    def get(self, request: Request, *args, **kwargs):
        return response.Response(request.user.has_perm('core.create_course'))


class UserLateDaysView(AlwaysIsAuthenticatedMixin, APIView):
    # swagger_schema = AGModelViewAutoSchema

    api_tags = [APITags.courses]

    # @swagger_auto_schema(
    #     manual_parameters=[Parameter('course_pk', in_='query', type='integer', required=True)],
    #     responses={
    #         '200': Schema(
    #             type='object',
    #             properties=[Parameter('late_days_remaining', in_='body', type='integer')])
    #     }
    # )
    @method_decorator(require_query_params('course_pk'))
    def get(self, request: Request, *args, **kwargs):
        try:
            user = get_object_or_404(User.objects, pk=int(kwargs['username_or_pk']))
        except ValueError:
            user = get_object_or_404(User.objects, username=kwargs['username_or_pk'])

        course = get_object_or_404(ag_models.Course.objects, pk=request.query_params['course_pk'])
        remaining = ag_models.LateDaysRemaining.objects.get_or_create(user=user, course=course)[0]

        self._check_read_permissions(remaining)

        return response.Response({'late_days_remaining': remaining.late_days_remaining})

    # @swagger_auto_schema(
    #     manual_parameters=[Parameter('course_pk', in_='query', type='integer', required=True)],
    #     request_body_parameters=[
    #         Parameter('late_days_remaining', in_='body', type='integer', required=True)],
    #     responses={
    #         '200': Schema(
    #             type='object',
    #             properties=[Parameter('late_days_remaining', in_='body', type='integer')])
    #     }
    # )
    @method_decorator(require_body_params('late_days_remaining'))
    def put(self, request: Request, *args, **kwargs):
        try:
            user = get_object_or_404(User.objects, pk=int(kwargs['username_or_pk']))
        except ValueError:
            user = get_object_or_404(User.objects, username=kwargs['username_or_pk'])

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
