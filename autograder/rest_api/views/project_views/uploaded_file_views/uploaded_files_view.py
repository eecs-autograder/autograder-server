from django.core import exceptions
from django.db import transaction

from rest_framework import viewsets, mixins, permissions, response, status

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder.rest_api.views.project_views.permissions import IsAdminOrReadOnlyStaff
from autograder.rest_api.views.load_object_mixin import build_load_object_mixin


class UploadedFilesViewSet(build_load_object_mixin(ag_models.Project),
                           mixins.CreateModelMixin,
                           mixins.ListModelMixin,
                           viewsets.GenericViewSet):
    serializer_class = ag_serializers.UploadedFileSerializer
    permission_classes = (permissions.IsAuthenticated,
                          IsAdminOrReadOnlyStaff)

    def get_queryset(self):
        project = self.load_object(self.kwargs['project_pk'])
        return project.uploaded_files.all()

    @transaction.atomic()
    def create(self, *args, **kwargs):
        try:
            return super().create(*args, **kwargs)
        except exceptions.ValidationError as e:
            return response.Response(e.message_dict,
                                     status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        serializer.save(project=self.load_object(self.kwargs['project_pk']))
