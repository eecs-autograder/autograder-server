from django.core import exceptions
from django.db import transaction
from django.http import FileResponse
from django.utils.decorators import method_decorator
from drf_yasg.openapi import Parameter
from drf_yasg.utils import swagger_auto_schema
from rest_framework import decorators, mixins, permissions, response, status, viewsets

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.core import constants
from autograder.rest_api import transaction_mixins
from autograder.rest_api.views.ag_model_views import (
    ListCreateNestedModelViewSet, AGModelGenericViewSet, require_body_params, AGModelAPIView)
from autograder.rest_api.views.schema_generation import APITags


_create_file_params = [
    Parameter(
        'file_obj',
        'form',
        type='file',
        required=True,
        description='The contents for this file, as multipart/form-data.'
    )
]


@method_decorator(
    name='post',
    decorator=swagger_auto_schema(request_body_parameters=_create_file_params))
class ListCreateInstructorFilesViewSet(ListCreateNestedModelViewSet):
    serializer_class = ag_serializers.UploadedFileSerializer
    permission_classes = (ag_permissions.is_admin_or_read_only_staff(),)

    model_manager = ag_models.Project.objects
    to_one_field_name = 'project'
    reverse_to_one_field_name = 'instructor_files'


def _get_course(instructor_file: ag_models.InstructorFile):
    return instructor_file.project.course


_rename_file_params = [
    Parameter(
        'name',
        'body',
        type='string',
        required=True,
        description='The new name for this file.'
    )
]


_update_content_params = [
    Parameter(
        'file_obj',
        'form',
        type='file',
        required=True,
        description='The new contents for this file, as multipart/form-data.'
    )
]


class InstructorFileDetailViewSet(mixins.RetrieveModelMixin,
                                  transaction_mixins.TransactionDestroyMixin,
                                  AGModelGenericViewSet):
    serializer_class = ag_serializers.UploadedFileSerializer
    permission_classes = (ag_permissions.is_admin_or_read_only_staff(_get_course),)

    model_manager = ag_models.InstructorFile.objects

    api_tags = [APITags.instructor_files]

    @swagger_auto_schema(responses={'200': 'Returns the updated InstructorFile metadata.'},
                         request_body_parameters=_rename_file_params)
    @transaction.atomic()
    @method_decorator(require_body_params('name'))
    @decorators.detail_route(methods=['put'])
    def name(self, *args, **kwargs):
        uploaded_file = self.get_object()
        try:
            uploaded_file.rename(self.request.data['name'])
            return response.Response(uploaded_file.to_dict())
        except exceptions.ValidationError as e:
            return response.Response(e.message_dict,
                                     status=status.HTTP_400_BAD_REQUEST)


class InstructorFileContentView(AGModelAPIView):
    serializer_class = ag_serializers.UploadedFileSerializer
    permission_classes = (ag_permissions.is_admin_or_read_only_staff(_get_course),)

    model_manager = ag_models.InstructorFile.objects

    api_tags = [APITags.instructor_files]

    @swagger_auto_schema(response_content_type='text/html',
                         responses={'200': 'Returns the file contents.'})
    def get(self, *args, **kwargs):
        return FileResponse(self.get_object().file_obj)

    @swagger_auto_schema(request_body_parameters=_update_content_params,
                         responses={'200': 'Returns the updated InstructorFile metadata.'})
    @method_decorator(require_body_params('file_obj'))
    @transaction.atomic()
    def put(self, *args, **kwargs):
        uploaded_file = self.get_object()
        uploaded_file.save(update_fields=['last_modified'])

        if self.request.data['file_obj'].size > constants.MAX_PROJECT_FILE_SIZE:
            return response.Response(
                {
                    'content': 'Project files cannot be bigger than {} bytes'.format(
                        constants.MAX_PROJECT_FILE_SIZE)
                },
                status=status.HTTP_400_BAD_REQUEST)
        with open(uploaded_file.abspath, 'wb') as f:
            for chunk in self.request.data['file_obj'].chunks():
                f.write(chunk)
        return response.Response(uploaded_file.to_dict())
