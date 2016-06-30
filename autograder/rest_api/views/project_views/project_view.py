from rest_framework import viewsets, mixins, permissions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from .permissions import ProjectPermissions
from ..load_object_mixin import build_load_object_mixin


class ProjectViewSet(build_load_object_mixin(ag_models.Project),
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     viewsets.GenericViewSet):
    serializer_class = ag_serializers.ProjectSerializer
    permission_classes = (permissions.IsAuthenticated, ProjectPermissions)

    def get_object(self):
        return self.load_object(self.kwargs['pk'])
