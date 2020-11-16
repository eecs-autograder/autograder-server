from typing import Dict

from django.core import exceptions
from django.db import transaction
from django.utils.decorators import method_decorator
from rest_framework import decorators, mixins, permissions, response, status, viewsets

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
from autograder.core import constants
from autograder.rest_api.schema import (AGDetailViewSchemaGenerator, AGListViewSchemaMixin,
                                        APITags, ContentType, CustomViewSchema, MediaTypeObject,
                                        as_content_obj, as_schema_ref)
from autograder.rest_api.size_file_response import SizeFileResponse
from autograder.rest_api.views.ag_model_views import (AGModelAPIView, AGModelDetailView,
                                                      NestedModelView,
                                                      convert_django_validation_error,
                                                      require_body_params)


class _Schema(AGListViewSchemaMixin, CustomViewSchema):
    pass


_INSTRUCTOR_FILE_BODY_SCHEMA: Dict[ContentType, MediaTypeObject] = {
    'multipart/form-data': {
        'schema': {
            'type': 'object',
            'properties': {
                'file_obj': {
                    'type': 'string',
                    'format': 'binary',
                    'description': 'The form-encoded file.'
                }
            }
        }
    }
}


class ListCreateInstructorFileView(NestedModelView):
    schema = _Schema([APITags.instructor_files], api_class=ag_models.InstructorFile, data={
        'POST': {
            'operation_id': 'createInstructorFile',
            'request': {
                'content': _INSTRUCTOR_FILE_BODY_SCHEMA
            },
            'responses': {
                '201': {
                    'content': as_content_obj(ag_models.InstructorFile),
                    'description': ''
                }
            }
        }
    })

    permission_classes = [ag_permissions.is_admin_or_read_only_staff()]

    model_manager = ag_models.Project.objects
    nested_field_name = 'instructor_files'
    parent_obj_field_name = 'project'

    def get(self, *args, **kwargs):
        return self.do_list()

    @convert_django_validation_error
    @transaction.atomic
    @method_decorator(require_body_params('file_obj'))
    def post(self, *args, **kwargs):
        instructor_file = ag_models.InstructorFile.objects.validate_and_create(
            project=self.get_object(),
            file_obj=self.request.data['file_obj']
        )
        return response.Response(instructor_file.to_dict(), status=status.HTTP_201_CREATED)


class InstructorFileDetailView(AGModelDetailView):
    schema = AGDetailViewSchemaGenerator([APITags.instructor_files])

    permission_classes = [ag_permissions.is_admin_or_read_only_staff()]
    model_manager = ag_models.InstructorFile.objects

    def get(self, *args, **kwargs):
        return self.do_get()

    def patch(self, *args, **kwargs):
        return self.do_patch()

    def delete(self, *args, **kwargs):
        return self.do_delete()


class RenameInstructorFileView(AGModelAPIView):
    schema = CustomViewSchema([APITags.instructor_files], {
        'PUT': {
            'operation_id': 'renameInstructorFile',
            'request': {
                'content': {
                    'application/json': {
                        'schema': {'type': 'string'}
                    }
                },
            },
            'responses': {
                '200': {
                    'content': as_content_obj(ag_models.InstructorFile),
                    'description': ''
                }
            }
        }
    })

    permission_classes = [ag_permissions.is_admin_or_read_only_staff()]
    model_manager = ag_models.InstructorFile.objects

    @transaction.atomic()
    @method_decorator(require_body_params('name'))
    def put(self, *args, **kwargs):
        uploaded_file = self.get_object()
        try:
            uploaded_file.rename(self.request.data['name'])
            return response.Response(uploaded_file.to_dict())
        except exceptions.ValidationError as e:
            return response.Response(e.message_dict,
                                     status=status.HTTP_400_BAD_REQUEST)


class InstructorFileContentView(AGModelAPIView):
    schema = CustomViewSchema([APITags.instructor_files], {
        'GET': {
            'operation_id': 'getInstructorFileContent',
            'responses': {
                '200': {
                    'content': {
                        'application/octet-stream': {
                            'schema': {'type': 'string', 'format': 'binary'}
                        }
                    },
                    'description': ''
                }
            }
        },
        'PUT': {
            'operation_id': 'setInstructorFileContent',
            'request': {
                'content': _INSTRUCTOR_FILE_BODY_SCHEMA
            },
            'responses': {
                '201': {
                    'content': as_content_obj(ag_models.InstructorFile),
                    'description': ''
                }
            }
        }
    })

    permission_classes = [ag_permissions.is_admin_or_read_only_staff()]
    model_manager = ag_models.InstructorFile.objects

    def get(self, *args, **kwargs):
        return SizeFileResponse(self.get_object().file_obj)

    @method_decorator(require_body_params('file_obj'))
    @transaction.atomic()
    def put(self, *args, **kwargs):
        uploaded_file = self.get_object()
        uploaded_file.save(update_fields=['last_modified'])

        if self.request.data['file_obj'].size > constants.MAX_INSTRUCTOR_FILE_SIZE:
            return response.Response(
                {
                    'content': 'Project files cannot be bigger than {} bytes'.format(
                        constants.MAX_INSTRUCTOR_FILE_SIZE)
                },
                status=status.HTTP_400_BAD_REQUEST)
        with open(uploaded_file.abspath, 'wb') as f:
            for chunk in self.request.data['file_obj'].chunks():
                f.write(chunk)
        return response.Response(uploaded_file.to_dict())
