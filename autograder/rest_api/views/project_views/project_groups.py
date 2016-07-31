from django.contrib.auth.models import User
from django.db import transaction

from rest_framework import viewsets, mixins, permissions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

import autograder.core.shared.utilities as ut

from .permissions import IsAdminOrReadOnlyStaff
from ..load_object_mixin import build_load_object_mixin


class ProjectGroupsViewSet(
        build_load_object_mixin(ag_models.Project, lock_on_unsafe_method=False),
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        viewsets.GenericViewSet):
    serializer_class = ag_serializers.SubmissionGroupSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrReadOnlyStaff)

    def get_queryset(self):
        project = self.load_object(self.kwargs['project_pk'])
        return project.submission_groups.all()

    @transaction.atomic()
    def create(self, request, project_pk, *args, **kwargs):
        project = self.load_object(project_pk)
        request.data['project'] = project

        users = [
            User.objects.get_or_create(username=username)[0]
            for username in request.data.pop('member_names')]

        ut.lock_users(users)
        # Keep this hook immediately after locking the users.
        ut.mocking_hook()

        request.data['members'] = users
        request.data['check_group_size_limits'] = (
            not project.course.is_administrator(request.user))

        return super().create(request, *args, **kwargs)
