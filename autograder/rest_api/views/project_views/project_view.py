from rest_framework import viewsets, mixins, permissions, decorators

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins

from .permissions import ProjectPermissions
from ..load_object_mixin import build_load_object_mixin


class ProjectViewSet(build_load_object_mixin(ag_models.Project),  # type: ignore
                     mixins.RetrieveModelMixin,
                     transaction_mixins.TransactionUpdateMixin,
                     viewsets.GenericViewSet):
    serializer_class = ag_serializers.ProjectSerializer
    permission_classes = (permissions.IsAuthenticated, ProjectPermissions)

    @decorators.detail_route()
    def num_queued_submissions(self, *args, **kwargs):
        pass
