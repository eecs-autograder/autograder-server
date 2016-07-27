from django.db import transaction

from rest_framework import viewsets, mixins, permissions

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from .permissions import IsAdminOrReadOnlyStaff
from ..load_object_mixin import build_load_object_mixin


class ProjectAGTestsViewset(build_load_object_mixin(ag_models.Project),
                            mixins.ListModelMixin,
                            mixins.CreateModelMixin,
                            viewsets.GenericViewSet):
    permission_classes = (permissions.IsAuthenticated, IsAdminOrReadOnlyStaff)
    serializer_class = ag_serializers.AGTestCaseSerializer

    def get_queryset(self):
        project = self.load_object(self.kwargs['project_pk'])
        return project.autograder_test_cases.all()

    @transaction.atomic()
    def create(self, request, project_pk, *args, **kwargs):
        request.data['project'] = self.load_object(project_pk)
        return super().create(request, *args, **kwargs)
