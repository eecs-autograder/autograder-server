from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Prefetch

from rest_framework import response, status, permissions

from drf_composable_permissions.p import P

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import permissions as ag_permissions

from autograder import utils
import autograder.utils.testing as test_ut
from autograder.rest_api.views.ag_model_views import (
    ListCreateNestedModelView, AGModelGenericView)


is_admin = ag_permissions.is_admin(lambda project: project.course)
is_staff = ag_permissions.is_staff(lambda project: project.course)
is_handgrader = ag_permissions.is_handgrader(lambda project: project.course)


class _CanCreateSoloGroup(permissions.BasePermission):
    def has_object_permission(self, request, view, project):
        if project.course.is_course_staff(request.user):
            return True

        if not project.visible_to_students:
            return False

        return (project.course.is_enrolled_student(request.user) or
                project.guests_can_submit)


class GroupsViewSet(ListCreateNestedModelView):
    serializer_class = ag_serializers.SubmissionGroupSerializer
    permission_classes = (P(is_admin) |
                          ((P(is_staff) | P(is_handgrader)) & ag_permissions.IsReadOnly),)

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')
    foreign_key_field_name = 'project'
    reverse_foreign_key_field_name = 'submission_groups'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.method.lower() == 'get':
            queryset = queryset.prefetch_related(
                Prefetch('members', User.objects.order_by('username')), 'submissions')
            queryset = list(
                sorted(queryset.all(), key=lambda group: group.members.first().username))

        return queryset

    @transaction.atomic()
    def create(self, request, *args, **kwargs):
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


class CreateSoloGroupView(AGModelGenericView):
    permission_classes = (_CanCreateSoloGroup,)
    serializer_class = ag_serializers.SubmissionGroupSerializer

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')

    @transaction.atomic()
    def post(self, request, *args, **kwargs):
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
