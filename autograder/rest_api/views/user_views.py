from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from drf_yasg.openapi import Schema, Parameter
from drf_yasg.utils import swagger_auto_schema

from rest_framework import mixins, permissions, decorators, response
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.views import APIView

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api.views.ag_model_views import AGModelGenericViewSet, require_query_params, \
    require_body_params, AGModelAPIView, AlwaysIsAuthenticatedMixin
from autograder.rest_api.views.schema_generation import APITags, AGModelSchemaBuilder, \
    AGModelViewAutoSchema


class _Permissions(permissions.BasePermission):
    def has_permission(self, *args, **kwargs):
        return True

    def has_object_permission(self, request, view, ag_test):
        return view.kwargs['pk'] == str(request.user.pk)


_course_list_schema = Schema(
    type='array', items=AGModelSchemaBuilder.get().get_schema(ag_models.Course))


class UserViewSet(mixins.RetrieveModelMixin,
                  AGModelGenericViewSet):
    serializer_class = ag_serializers.UserSerializer
    permission_classes = (_Permissions,)

    model_manager = User.objects

    api_tags = [APITags.permissions]

    @decorators.list_route()
    @swagger_auto_schema(responses={'200': ag_serializers.UserSerializer})
    def current(self, request, *args, **kwargs):
        return response.Response(
            ag_serializers.UserSerializer(request.user).data)

    @swagger_auto_schema(responses={'200': _course_list_schema})
    @decorators.detail_route()
    def courses_is_admin_for(self, request, *args, **kwargs):
        user = self.get_object()
        return response.Response(
            ag_serializers.CourseSerializer(user.courses_is_admin_for.all(),
                                            many=True).data)

    @swagger_auto_schema(responses={'200': _course_list_schema})
    @decorators.detail_route()
    def courses_is_staff_for(self, request, *args, **kwargs):
        user = self.get_object()
        return response.Response(
            ag_serializers.CourseSerializer(user.courses_is_staff_for.all(),
                                            many=True).data)

    @swagger_auto_schema(responses={'200': _course_list_schema})
    @decorators.detail_route()
    def courses_is_handgrader_for(self, request, *args, **kwargs):
        user = self.get_object()
        return response.Response(
            ag_serializers.CourseSerializer(user.courses_is_handgrader_for.all(),
                                            many=True).data)

    @swagger_auto_schema(responses={'200': _course_list_schema})
    @decorators.detail_route()
    def courses_is_enrolled_in(self, request, *args, **kwargs):
        user = self.get_object()
        return response.Response(
            ag_serializers.CourseSerializer(user.courses_is_enrolled_in.all(),
                                            many=True).data)

    @swagger_auto_schema(
        responses={'200': Schema(type='array',
                                 items=AGModelSchemaBuilder.get().get_schema(ag_models.Group))})
    @decorators.detail_route()
    def groups_is_member_of(self, request, *args, **kwargs):
        user = self.get_object()
        queryset = user.groups_is_member_of.select_related(
            'project').prefetch_related('members').all()
        return response.Response(
            ag_serializers.SubmissionGroupSerializer(queryset, many=True).data)

    @swagger_auto_schema(
        responses={
            '200': Schema(type='array',
                          items=AGModelSchemaBuilder.get().get_schema(ag_models.GroupInvitation))})
    @decorators.detail_route()
    def group_invitations_received(self, request, *args, **kwargs):
        user = self.get_object()
        return response.Response(
            ag_serializers.SubmissionGroupInvitationSerializer(
                user.group_invitations_received.all(), many=True).data)

    @swagger_auto_schema(
        responses={
            '200': Schema(type='array',
                          items=AGModelSchemaBuilder.get().get_schema(ag_models.GroupInvitation))})
    @decorators.detail_route()
    def group_invitations_sent(self, request, *args, **kwargs):
        user = self.get_object()
        return response.Response(
            ag_serializers.SubmissionGroupInvitationSerializer(
                user.group_invitations_sent.all(), many=True).data)


class UserLateDaysView(AlwaysIsAuthenticatedMixin, APIView):
    swagger_schema = AGModelViewAutoSchema

    api_tags = [APITags.courses]

    @swagger_auto_schema(
        manual_parameters=[Parameter('course_pk', in_='query', type='integer', required=True)],
        responses={
            '200': Schema(
                type='object',
                properties=[Parameter('late_days_remaining', in_='body', type='integer')])
        }
    )
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

    @swagger_auto_schema(
        manual_parameters=[Parameter('course_pk', in_='query', type='integer', required=True)],
        request_body_parameters=[
            Parameter('late_days_remaining', in_='body', type='integer', required=True)],
        responses={
            '200': Schema(
                type='object',
                properties=[Parameter('late_days_remaining', in_='body', type='integer')])
        }
    )
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
