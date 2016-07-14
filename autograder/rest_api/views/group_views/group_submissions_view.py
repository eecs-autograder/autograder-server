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
        if request.method.lower() == 'post':
            # FIXME
            return False

        return user_can_view_group(request.user, group)


class GroupSubmissionsViewset(
        build_load_object_mixin(ag_models.SubmissionGroup, pk_key='group_pk'),
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        viewsets.GenericViewSet):
    serializer_class = ag_serializers.SubmissionSerializer
    permission_classes = (permissions.IsAuthenticated, _Permissions)

    def get_queryset(self):
        return self.get_object().submissions.all()
