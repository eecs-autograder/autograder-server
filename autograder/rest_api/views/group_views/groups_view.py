from django.contrib.auth.models import User
from django.db import transaction

from rest_framework import (
    viewsets, mixins, permissions, decorators, response, status)

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api.views.permission_components import user_can_view_project

from autograder import utils
import autograder.utils.testing as test_ut

from autograder.rest_api.views.project_views.permissions import IsAdminOrReadOnlyStaff
from autograder.rest_api.views.load_object_mixin import build_load_object_mixin


class _CreateSoloGroupPermissions(permissions.BasePermission):
    def has_object_permission(self, request, view, project):
        if project.course.is_course_staff(request.user):
            return True

        return user_can_view_project(request.user, project)


class GroupsViewSet(
        build_load_object_mixin(ag_models.Project, lock_on_unsafe_method=False,
                                pk_key='project_pk'),
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        viewsets.GenericViewSet):
    serializer_class = ag_serializers.SubmissionGroupSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrReadOnlyStaff)

    def get_queryset(self):
        project = self.get_object()
        return project.submission_groups.all()

    @transaction.atomic()
    def create(self, request, project_pk, *args, **kwargs):
        project = self.get_object()
        request.data['project'] = project

        users = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.pop('member_names')]

        utils.lock_users(users)
        # Keep this hook immediately after locking the users.
        test_ut.mocking_hook()

        request.data['members'] = users
        request.data['check_group_size_limits'] = (
            not project.course.is_administrator(request.user))

        return super().create(request, *args, **kwargs)

    @transaction.atomic()
    @decorators.list_route(methods=['post'],
                           permission_classes=[permissions.IsAuthenticated,
                                               _CreateSoloGroupPermissions])
    def solo_group(self, request, *args, **kwargs):
        project = self.get_object()

        utils.lock_users([request.user])

        data = {
            'project': project,
            'members': [request.user],
            'check_group_size_limits': (
                not project.course.is_course_staff(request.user))
        }
        serializer = self.get_serializer(data=data)
        serializer.is_valid()
        serializer.save()

        return response.Response(serializer.data,
                                 status=status.HTTP_201_CREATED)
