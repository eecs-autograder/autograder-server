import itertools

from django.contrib.auth.models import User
from django.db import transaction

from rest_framework import viewsets, mixins, permissions, exceptions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder import utils

from autograder.rest_api.views.project_views.permissions import IsAdminOrReadOnlyStaff, user_can_view_project
from autograder.rest_api.views.load_object_mixin import build_load_object_mixin


class GroupInvitationsPermissions(IsAdminOrReadOnlyStaff):
    def has_object_permission(self, request, view, project):
        if request.method.lower() == 'get':
            return super().has_object_permission(request, view, project)

        if (project.disallow_group_registration and
                not project.course.is_course_staff(request.user)):
            return False

        return user_can_view_project(request.user, project)


class GroupInvitationsViewSet(
        build_load_object_mixin(ag_models.Project, lock_on_unsafe_method=False),
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        viewsets.GenericViewSet):
    serializer_class = ag_serializers.SubmissionGroupInvitationSerializer
    permission_classes = (permissions.IsAuthenticated,
                          GroupInvitationsPermissions)

    def get_queryset(self):
        project = self.load_object(self.kwargs['project_pk'])
        return project.submission_group_invitations.all()

    @transaction.atomic()
    def create(self, request, project_pk, *args, **kwargs):
        for key in request.data:
            if key != 'invited_usernames':
                raise exceptions.ValidationError({'invalid_fields': [key]})

        request.data['project'] = self.load_object(project_pk)

        invited_users = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.pop('invited_usernames')]

        utils.lock_users(itertools.chain([request.user], invited_users))

        request.data['invitation_creator'] = request.user
        request.data['invited_users'] = invited_users
        return super().create(request, *args, **kwargs)
