from rest_framework import viewsets, mixins, permissions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from .permissions import IsAdminOrReadOnlyStaff
from ..load_object_mixin import build_load_object_mixin


class ProjectUploadedFilesViewSet(build_load_object_mixin(ag_models.Project),
                                  mixins.CreateModelMixin,
                                  mixins.ListModelMixin,
                                  viewsets.GenericViewSet):
    serializer_class = ag_serializers.UploadedFileSerializer
    permission_classes = (permissions.IsAuthenticated,
                          IsAdminOrReadOnlyStaff)

    def get_queryset(self):
        project = self.load_object(self.kwargs['project_pk'])
        return project.uploaded_files.all()

    def create(self, request, project_pk, *args, **kwargs):
        request.data['project'] = self.load_object(project_pk)
        return super().create(request, *args, **kwargs)