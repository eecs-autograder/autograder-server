# import itertools

from django.contrib.auth.models import User
# from django.db import transaction

from rest_framework import viewsets, mixins, permissions, response, status

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from ..permission_components import user_can_view_group
from ..load_object_mixin import build_load_object_mixin


class _Permissions(permissions.BasePermission):
    def has_object_permission(self, request, view, group):
        if request.method not in permissions.SAFE_METHODS:
            return group.project.course.is_administrator(request.user)

        return user_can_view_group(request.user, group)


class GroupViewset(build_load_object_mixin(ag_models.SubmissionGroup),
                   mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin,
                   viewsets.GenericViewSet):
    queryset = ag_models.SubmissionGroup.objects.all()
    serializer_class = ag_serializers.SubmissionGroupSerializer
    permission_classes = (permissions.IsAuthenticated, _Permissions)

    def update(self, request, *args, **kwargs):
        if 'member_names' in request.data:
            request.data['members'] = [
                User.objects.get_or_create(username=username)[0]
                for username in request.data.pop('member_names')]
            request.data['check_group_size_limits'] = False
        return super().update(request, *args, **kwargs)
