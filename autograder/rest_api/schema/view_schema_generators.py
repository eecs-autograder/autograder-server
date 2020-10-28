from __future__ import annotations
from autograder.rest_api.schema.utils import stderr

import enum
from typing import Dict, List, Optional, TypedDict, Union, cast

from rest_framework.schemas.openapi import AutoSchema  # type: ignore

from autograder import utils
from autograder.rest_api.schema.model_schema_generators import (API_OBJ_TYPE_NAMES,
                                                                AGModelSchemaGenerator,
                                                                APIClassType, as_schema_ref,
                                                                assert_not_ref)
from autograder.rest_api.schema.openapi_types import (ContentType, HTTPMethodName, MediaTypeObject,
                                                      OperationObject, OrRef, ParameterObject,
                                                      ReferenceObject, RequestBodyObject,
                                                      ResponseObject, SchemaObject)


# Defines the order of API tags and provides a single point of
# maintenance for their string values.
class APITags(enum.Enum):
    users = 'users'
    courses = 'courses'
    rosters = 'rosters'

    projects = 'projects'
    instructor_files = 'instructor_files'
    expected_student_files = 'expected_student_files'

    sandbox_docker_images = 'sandbox_docker_images'

    ag_test_suites = 'ag_test_suites'
    ag_test_cases = 'ag_test_cases'
    ag_test_commands = 'ag_test_commands'

    mutation_test_suites = 'mutation_test_suites'

    group_invitations = 'group_invitations'
    groups = 'groups'

    submissions = 'submissions'
    submission_output = 'submission_output'
    rerun_submissions_tasks = 'rerun_submissions_tasks'

    handgrading_rubrics = 'handgrading_rubrics'
    handgrading_results = 'handgrading_results'

    criteria = 'criteria'
    annotations = 'annotations'

    criterion_results = 'criterion_results'
    applied_annotations = 'applied_annotations'
    comments = 'comments'


# Drf stubs doesn't have stubs for rest_framework.schemas.openapi yet.
class AGViewSchemaGenerator(AutoSchema):  # type: ignore
    def __init__(
        self,
        tags: List[APITags],
        api_class: Optional[APIClassType] = None,
        operation_id_override: Optional[str] = None
    ):
        super().__init__()
        self._tags = [tag.value for tag in tags]
        self._api_class = api_class
        self._operation_id_override = operation_id_override

    def get_operation(self, path: str, method: HTTPMethodName) -> OperationObject:
        result = self.get_operation_impl(path, method)
        result['tags'] = self._tags
        if self._operation_id_override is not None:
            result['operationId'] = self._operation_id_override
        else:
            result['operationId'] = self._get_operation_id(path, method)

        return result

    # Derived classes will typically override this.
    def get_operation_impl(self, path: str, method: HTTPMethodName) -> OperationObject:
        # Drf stubs doesn't have stubs for rest_framework.schemas.openapi yet.
        return cast(OperationObject, super().get_operation(path, method))

    def _get_operation_id(self, path: str, method: HTTPMethodName) -> str:
        return self._get_operation_id_impl(path, method)

    def _get_operation_id_impl(self, path: str, method: HTTPMethodName) -> str:
        raise NotImplementedError(
            f'Unable to create operation ID for {type(self.view).__name__} {method} {path}.\n'
            'You must either use an appropriate "AGxxSchema" class or provide the '
            '"operation_id" key to "CustomViewSchema".'
        )

    def generate_list_op_schema(self, base_result: OperationObject) -> OperationObject:
        ok_200_response = assert_not_ref(base_result['responses']['200'])
        schema = assert_not_ref(ok_200_response['content']['application/json']['schema'])
        schema['items'] = (
            as_schema_ref(self.get_api_class())
        )
        return base_result

    def generate_create_op_schema(self, base_result: OperationObject) -> OperationObject:
        if '200' in base_result['responses']:
            response_schema = assert_not_ref(base_result['responses'].pop('200'))
        else:
            response_schema = assert_not_ref(base_result['responses'].pop('201'))

        response_schema['content']['application/json']['schema'] = (
            as_schema_ref(self.get_api_class())
        )
        base_result['responses']['201'] = response_schema

        base_result['requestBody'] = self.make_api_class_request_body(include_required=True)

        return base_result

    def generate_retrieve_op_schema(self, base_result: OperationObject) -> OperationObject:
        ok_200_response = assert_not_ref(base_result['responses']['200'])
        ok_200_response['content']['application/json']['schema'] = (
            as_schema_ref(self.get_api_class())
        )

        return base_result

    def generate_patch_op_schema(self, base_result: OperationObject) -> OperationObject:
        ok_200_response = assert_not_ref(base_result['responses']['200'])
        ok_200_response['content']['application/json']['schema'] = (
            as_schema_ref(self.get_api_class())
        )

        base_result['requestBody'] = self.make_api_class_request_body(include_required=False)

        return base_result

    def get_api_class(self) -> APIClassType:
        if self._api_class is not None:
            return self._api_class

        if not hasattr(self.view, 'model_manager'):
            raise Exception(
                'View class has no "model_manager" and '
                'the value provided for "api_class" was None'
            )

        if self.view.model_manager is None:
            raise Exception(
                'Either the class\'s ".model_manager" or '
                'the value provided for "api_class" must be non-None'
            )

        return cast(APIClassType, self.view.model_manager.model)

    def make_api_class_request_body(self, *, include_required: bool) -> RequestBodyObject:
        body_schema = AGModelSchemaGenerator.factory(
            self.get_api_class()).generate_request_body_schema(include_required=include_required)
        schema: OrRef[SchemaObject] = (
            body_schema if body_schema is not None
            else as_schema_ref(self.get_api_class())
        )
        return {
            'required': True,
            'content': {
                'application/json': {
                    'schema': schema
                }
            }
        }


# TYPES UNSAFE ------------------------------------------------------------------------------------
# mypy has some shortcomings with mixins. Note that while adding a
# protocol for "self" in these mixins helps with most errors, there
# are (as of Aug 2020) still mypy errors that show up when calling super().
#
# We are deciding to supress the mixin-related type errors for now and
# will revisit this in the future.


class AGListViewSchemaMixin:
    def get_operation_impl(self, path: str, method: str) -> OperationObject:
        base_result = super().get_operation_impl(path, method)  # type: ignore
        if method == 'GET':
            return self.generate_list_op_schema(base_result)  # type: ignore

        return base_result  # type: ignore

    def _get_operation_id_impl(self, path: str, method: str) -> str:
        if method == 'GET':
            return f'list{API_OBJ_TYPE_NAMES[self.get_api_class()]}s'  # type: ignore

        return super()._get_operation_id_impl(path, method)  # type: ignore


class AGCreateViewSchemaMixin:
    def get_operation_impl(self, path: str, method: str) -> OperationObject:
        base_result = super().get_operation_impl(path, method)  # type: ignore
        if method == 'POST':
            return self.generate_create_op_schema(base_result)  # type: ignore

        return base_result  # type: ignore

    def _get_operation_id_impl(self, path: str, method: str) -> str:
        if method == 'POST':
            return f'create{API_OBJ_TYPE_NAMES[self.get_api_class()]}'  # type: ignore

        return super()._get_operation_id_impl(path, method)  # type: ignore


class AGListCreateViewSchemaGenerator(
    AGListViewSchemaMixin, AGCreateViewSchemaMixin, AGViewSchemaGenerator
):
    pass


class AGRetrieveViewSchemaMixin:
    def get_operation_impl(self, path: str, method: str) -> OperationObject:
        base_result = super().get_operation_impl(path, method)  # type: ignore
        if method == 'GET':
            return self.generate_retrieve_op_schema(base_result)  # type: ignore

        return base_result  # type: ignore

    def _get_operation_id_impl(self, path: str, method: str) -> str:
        if method == 'GET':
            return f'get{API_OBJ_TYPE_NAMES[self.get_api_class()]}'  # type: ignore

        return super()._get_operation_id_impl(path, method)  # type: ignore


class AGPatchViewSchemaMixin:
    def get_operation_impl(self, path: str, method: str) -> OperationObject:
        base_result = super().get_operation_impl(path, method)  # type: ignore
        if method == 'PATCH':
            return self.generate_patch_op_schema(base_result)  # type: ignore

        return base_result  # type: ignore

    def _get_operation_id_impl(self, path: str, method: str) -> str:
        if method == 'PATCH':
            return f'update{API_OBJ_TYPE_NAMES[self.get_api_class()]}'  # type: ignore

        return super()._get_operation_id_impl(path, method)  # type: ignore


class AGDetailViewSchemaGenerator(
    AGRetrieveViewSchemaMixin, AGPatchViewSchemaMixin, AGViewSchemaGenerator
):
    def _get_operation_id_impl(self, path: str, method: str) -> str:
        if method == 'DELETE':
            return f'delete{API_OBJ_TYPE_NAMES[self.get_api_class()]}'

        return super()._get_operation_id_impl(path, method)


# END TYPE UNSAFE ---------------------------------------------------------------------------------


class CustomViewDict(TypedDict, total=False):
    GET: CustomViewMethodData
    POST: CustomViewMethodData
    PUT: CustomViewMethodData
    PATCH: CustomViewMethodData
    DELETE: CustomViewMethodData


class CustomViewMethodData(TypedDict, total=False):
    operation_id: str
    parameters: List[OrRef[ParameterObject]]
    # Key = param name, Value = schema dict
    # Use for fixing the types of DRF-generated URL params.
    param_schema_overrides: Dict[str, SchemaObject]
    request: RequestBodyObject
    # Key = response status
    responses: Dict[str, Optional[ResponseObject]]

    deprecated: bool


def as_content_obj(type_: APIClassType) -> Dict[ContentType, MediaTypeObject]:
    """
    Returns a value suitable for use under the "content" key of a
    RequestBodyObject or ResponseObject, but that uses a $ref to the given APIClassType
    as its "schema" value.
    """
    return {
        'application/json': {
            'schema': as_schema_ref(type_)
        }
    }


def as_array_content_obj(
    type_: Union[APIClassType, SchemaObject, ReferenceObject]
) -> Dict[ContentType, MediaTypeObject]:
    if isinstance(type_, dict):
        obj_dict = type_
    else:
        assert type_ in API_OBJ_TYPE_NAMES
        obj_dict = as_schema_ref(type_)

    return {
        'application/json': {
            'schema': {
                'type': 'array',
                'items': obj_dict
            }
        }
    }


def as_paginated_content_obj(
    type_: Union[APIClassType, SchemaObject, ReferenceObject]
) -> Dict[ContentType, MediaTypeObject]:
    if isinstance(type_, dict):
        obj_dict = type_
    else:
        assert type_ in API_OBJ_TYPE_NAMES
        obj_dict = as_schema_ref(type_)

    return {
        'application/json': {
            'schema': {
                'type': 'object',
                'properties': {
                    'count': {'type': 'integer'},
                    'next': {'type': 'string', 'format': 'url'},
                    'previous': {'type': 'string', 'format': 'url'},
                    'results': {
                        'type': 'array',
                        'items': obj_dict
                    }
                }
            }
        }
    }


class CustomViewSchema(AGViewSchemaGenerator):
    def __init__(self, tags: List[APITags],
                 data: CustomViewDict,
                 api_class: Optional[APIClassType] = None):
        super().__init__(tags, api_class=api_class)
        self.data: CustomViewDict = data

    def get_operation_impl(self, path: str, method: HTTPMethodName) -> OperationObject:
        result = super().get_operation_impl(path, method)
        method_data = self.data.get(method, None)
        if method_data is None:
            return result

        result.setdefault('parameters', [])
        if 'parameters' in method_data:
            result['parameters'] += method_data['parameters']

        for param_name, schema in method_data.get('param_schema_overrides', {}).items():
            param = utils.find_if(
                result['parameters'],
                lambda item: 'name' in item and assert_not_ref(item)['name'] == param_name
            )
            assert param is not None
            assert_not_ref(param)['schema'] = schema

        if 'request' in method_data:
            updates = cast(RequestBodyObject, {
                # See if type checking works with dict union in Python 3.9
                'required': True, **method_data['request']
            })
            if 'requestBody' in result:
                # mypy this appears to have a false positive here
                # See if type checking works with dict union in Python 3.9?
                # See https://github.com/python/mypy/issues/9335 for updates
                result['requestBody'].update(updates)  # type: ignore
            else:
                result['requestBody'] = updates

        responses: Dict[str, OrRef[ResponseObject]] = {}
        for status, response_data in method_data.get('responses', {}).items():
            if response_data is None:
                stderr('WAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAa', path, method)
            responses[status] = {'description': ''} if response_data is None else response_data

        if responses:
            result['responses'] = responses

        if 'deprecated' in method_data:
            result['deprecated'] = method_data['deprecated']

        return result

    def _get_operation_id_impl(self, path: str, method: HTTPMethodName) -> str:
        operation_id = self.data.get(method, {}).get('operation_id', None)
        if operation_id is not None:
            return operation_id

        return super()._get_operation_id_impl(path, method)


class OrderViewSchema(CustomViewSchema):
    def __init__(self, tags: List[APITags], api_class: APIClassType):
        super().__init__(tags, {
            'GET': {
                'operation_id': f'get{API_OBJ_TYPE_NAMES[api_class]}Order',
                'responses': {
                    '200': {
                        'description': '',
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'array',
                                    'items': {'type': 'integer', 'format': 'id'}
                                }
                            }
                        }
                    }
                }
            },
            'PUT': {
                'operation_id': f'set{API_OBJ_TYPE_NAMES[api_class]}Order',
                'request': {
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'array',
                                'items': {'type': 'integer', 'format': 'id'}
                            }
                        }
                    }
                },
                'responses': {
                    '200': {
                        'description': '',
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'array',
                                    'items': {'type': 'integer', 'format': 'id'}
                                }
                            }
                        }
                    }
                }
            }
        })
