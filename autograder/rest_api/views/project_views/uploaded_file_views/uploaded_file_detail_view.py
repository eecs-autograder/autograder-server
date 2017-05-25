# from wsgiref.util import FileWrapper

from django.core import exceptions
from django.db import transaction
from django.http import FileResponse

from rest_framework import (
    viewsets, mixins, permissions, decorators, response, status)

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins

from autograder.rest_api.views.load_object_mixin import build_load_object_mixin


class _Permissions(permissions.BasePermission):
    def has_object_permission(self, request, view, uploaded_file):
        if not uploaded_file.project.course.is_course_staff(request.user):
            return False

        if not uploaded_file.project.course.is_administrator(request.user):
            return request.method in permissions.SAFE_METHODS

        return True


class UploadedFileDetailViewSet(build_load_object_mixin(ag_models.UploadedFile),
                                mixins.RetrieveModelMixin,
                                transaction_mixins.TransactionDestroyMixin,
                                viewsets.GenericViewSet):
    queryset = ag_models.UploadedFile.objects.all()
    serializer_class = ag_serializers.UploadedFileSerializer
    permission_classes = (permissions.IsAuthenticated, _Permissions)

    @transaction.atomic()
    @decorators.detail_route(methods=['put'])
    def name(self, request, pk):
        uploaded_file = self.load_object(pk)
        try:
            uploaded_file.rename(request.data['name'])
            return response.Response(uploaded_file.to_dict())
        except exceptions.ValidationError as e:
            return response.Response(e.message_dict,
                                     status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic()
    @decorators.detail_route(methods=['get', 'put'])
    def content(self, request, pk):
        uploaded_file = self.load_object(pk)
        if request.method.lower() == 'put':
            with open(uploaded_file.abspath, 'wb') as f:
                for chunk in request.data['file_obj'].chunks():
                    f.write(chunk)
            return response.Response(uploaded_file.to_dict())
        else:
            return FileResponse(uploaded_file.file_obj)
