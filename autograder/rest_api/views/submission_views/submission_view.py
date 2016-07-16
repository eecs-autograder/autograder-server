from django.core import exceptions
from django.http.response import FileResponse

from rest_framework import (
    viewsets, mixins, permissions, decorators, response, status)

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from ..permission_components import user_can_view_group
from ..load_object_mixin import build_load_object_mixin


class _Permissions(permissions.BasePermission):
    def has_object_permission(self, request, view, submission):
        if request.method not in permissions.SAFE_METHODS:
            return submission.submission_group.project.course.is_administrator(
                request.user)

        return user_can_view_group(request.user, submission.submission_group)


class SubmissionViewset(build_load_object_mixin(ag_models.Submission),
                        mixins.RetrieveModelMixin,
                        mixins.UpdateModelMixin,
                        viewsets.GenericViewSet):
    queryset = ag_models.Submission.objects.all()
    serializer_class = ag_serializers.SubmissionSerializer
    permission_classes = (permissions.IsAuthenticated, _Permissions)

    @decorators.detail_route()
    def file(self, request, *args, **kwargs):
        submission = self.get_object()

        try:
            filename = request.query_params['filename']
            return FileResponse(submission.get_file(filename))
        except KeyError:
            return response.Response(
                'Missing required query parameter "filename"',
                status=status.HTTP_400_BAD_REQUEST)
        except exceptions.ObjectDoesNotExist:
            return response.Response('File "{}" not found'.format(filename),
                                     status=status.HTTP_404_NOT_FOUND)
