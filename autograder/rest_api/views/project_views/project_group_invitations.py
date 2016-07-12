from django.contrib.auth.models import User

from rest_framework import viewsets, mixins, permissions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from .permissions import IsAdminOrReadOnlyStaff, user_can_view_project
from ..load_object_mixin import build_load_object_mixin


class GroupInvitationsPermissions(IsAdminOrReadOnlyStaff):
    def has_object_permission(self, request, view, project):
        if request.method.lower() == 'get':
            return super().has_object_permission(request, view, project)

        return user_can_view_project(request.user, project)


class ProjectGroupInvitationsViewset(
        build_load_object_mixin(ag_models.Project),
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        viewsets.GenericViewSet):
    serializer_class = ag_serializers.SubmissionGroupInvitationSerializer
    permission_classes = (permissions.IsAuthenticated,
                          GroupInvitationsPermissions)

    def get_queryset(self):
        project = self.load_object(self.kwargs['project_pk'])
        return project.submission_group_invitations.all()

    def create(self, request, project_pk, *args, **kwargs):
        request.data['project'] = self.load_object(project_pk)
        request.data['invitation_creator'] = request.user
        request.data['invited_users'] = [
            User.objects.select_for_update().get_or_create(username=username)[0]
            for username in request.data['invited_usernames']]
        return super().create(request, *args, **kwargs)
