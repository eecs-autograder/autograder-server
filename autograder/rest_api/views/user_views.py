from django.contrib.auth.models import User
from drf_yasg.openapi import Schema
from drf_yasg.utils import swagger_auto_schema

from rest_framework import viewsets, mixins, permissions, decorators, response

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api.views.ag_model_views import AGModelGenericViewSet
from autograder.rest_api.views.schema_generation import APITags, AGModelSchemaBuilder


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
