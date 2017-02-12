from rest_framework import viewsets, mixins, permissions, decorators, response

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
        project = self.get_object()
        num_queued_submissions = ag_models.Submission.objects.filter(
            status=ag_models.Submission.GradingStatus.queued,
            submission_group__project=project).count()

        return response.Response(data=num_queued_submissions)
