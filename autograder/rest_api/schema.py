from __future__ import annotations

import sys
from abc import abstractmethod
from decimal import Decimal
from enum import Enum
from functools import singledispatch
from typing import (Any, Dict, List, Literal, Optional, Sequence, Tuple, Type,
                    TypedDict, Union, cast, get_args, get_origin,
                    get_type_hints)

import django.contrib.postgres.fields as pg_fields
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Field, fields
from django.db.models.fields.reverse_related import ForeignObjectRel
from django.utils.functional import cached_property
from rest_framework.schemas.openapi import AutoSchema, SchemaGenerator
from timezone_field.fields import TimeZoneField

import autograder.core.fields as ag_fields
import autograder.core.models as ag_models
import autograder.handgrading.models as hg_models
from autograder import utils
from autograder.core.models.ag_model_base import (AutograderModel,
                                                  DictSerializableMixin,
                                                  ToDictMixin)
from autograder.core.submission_feedback import (AGTestCaseResultFeedback,
                                                 AGTestCommandResultFeedback,
                                                 AGTestSuiteResultFeedback,
                                                 SubmissionResultFeedback)
from autograder.rest_api.views.schema_generation import APITags


def stderr(*args, **kwargs):
    """
    Thin wrapper for print() that sends output to stderr.
    Use for debugging schema generation.
    """
    print(*args, **kwargs, file=sys.stderr)


class AGSchemaGenerator(SchemaGenerator):
    def __init__(
        self,
        title=None,
        url=None,
        description=None,
        patterns=None,
        urlconf=None,
        version=None
    ):
        super().__init__(
            title='Autograder.io API',
            url=url,
            description=description,
            patterns=patterns,
            urlconf=urlconf,
            version=settings.VERSION,
        )

    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request=request, public=public)
        schema['components'] = self._get_model_schemas()
        schema['tags'] = [{'name': item.value} for item in APITags]
        return schema

    def _get_model_schemas(self) -> dict:
        result = {
            'schemas': {
                name: APIClassSchemaGenerator.factory(class_).generate()
                for class_, name in API_OBJ_TYPE_NAMES.items()
            }
        }

        result['schemas']['UserRoles'] = {
            'type': 'object',
            'properties': {
                'is_admin': {'type': 'boolean'},
                'is_staff': {'type': 'boolean'},
                'is_student': {'type': 'boolean'},
                'is_handgrader': {'type': 'boolean'},
            }
        }

        result['schemas']['UserID'] = {
            'type': 'object',
            'required': ['pk'],
            'properties': {
                'pk': _PK_SCHEMA,
                'username': {'type': 'string', 'format': 'email'}
            }
        }

        return result


API_OBJ_TYPE_NAMES = {
    User: 'User',
    ag_models.Course: ag_models.Course.__name__,
    ag_models.Semester: ag_models.Semester.__name__,
    ag_models.Project: ag_models.Project.__name__,
    ag_models.UltimateSubmissionPolicy: ag_models.UltimateSubmissionPolicy.__name__,
    ag_models.ExpectedStudentFile: ag_models.ExpectedStudentFile.__name__,
    ag_models.InstructorFile: ag_models.InstructorFile.__name__,
    ag_models.DownloadTask: ag_models.DownloadTask.__name__,
    ag_models.DownloadType: ag_models.DownloadType.__name__,
    ag_models.Group: ag_models.Group.__name__,
    ag_models.GroupInvitation: ag_models.GroupInvitation.__name__,
    ag_models.Submission: ag_models.Submission.__name__,

    ag_models.Command: ag_models.Command.__name__,

    ag_models.SandboxDockerImage: ag_models.SandboxDockerImage.__name__,
    ag_models.BuildSandboxDockerImageTask: ag_models.BuildSandboxDockerImageTask.__name__,
    ag_models.BuildImageStatus: ag_models.BuildImageStatus.__name__,
    ag_models.AGTestSuite: ag_models.AGTestSuite.__name__,
    ag_models.NewAGTestSuiteFeedbackConfig: 'AGTestSuiteFeedbackConfig',
    ag_models.AGTestCase: ag_models.AGTestCase.__name__,
    ag_models.NewAGTestCaseFeedbackConfig: 'AGTestCaseFeedbackConfig',
    ag_models.AGTestCommand: ag_models.AGTestCommand.__name__,
    ag_models.NewAGTestCommandFeedbackConfig: 'AGTestCommandFeedbackConfig',

    ag_models.StdinSource: ag_models.StdinSource.__name__,
    ag_models.ExpectedOutputSource: ag_models.ExpectedOutputSource.__name__,
    ag_models.ExpectedReturnCode: ag_models.ExpectedReturnCode.__name__,
    ag_models.ValueFeedbackLevel: ag_models.ValueFeedbackLevel.__name__,

    SubmissionResultFeedback: SubmissionResultFeedback.__name__,
    AGTestSuiteResultFeedback: AGTestSuiteResultFeedback.__name__,
    AGTestCaseResultFeedback: AGTestCaseResultFeedback.__name__,
    AGTestCommandResultFeedback: AGTestCommandResultFeedback.__name__,
    ag_models.FeedbackCategory: ag_models.FeedbackCategory.__name__,

    ag_models.StudentTestSuite: ag_models.StudentTestSuite.__name__,
    ag_models.NewStudentTestSuiteFeedbackConfig: 'StudentTestSuiteFeedbackConfig',
    # Hack: SubmissionResultFeedback.student_test_suite_results returns
    # List[StudentTestSuiteResult], but it gets serialized to StudentTestSuiteResultFeedback
    ag_models.StudentTestSuiteResult: 'StudentTestSuiteResultFeedback',
    ag_models.StudentTestSuiteResult.FeedbackCalculator: 'StudentTestSuiteResultFeedback',
    ag_models.BugsExposedFeedbackLevel: ag_models.BugsExposedFeedbackLevel.__name__,

    ag_models.RerunSubmissionsTask: ag_models.RerunSubmissionsTask.__name__,

    hg_models.HandgradingRubric: hg_models.HandgradingRubric.__name__,
    hg_models.PointsStyle: hg_models.PointsStyle.__name__,
    hg_models.Criterion: hg_models.Criterion.__name__,
    hg_models.Annotation: hg_models.Annotation.__name__,
    hg_models.HandgradingResult: hg_models.HandgradingResult.__name__,
    hg_models.CriterionResult: hg_models.CriterionResult.__name__,
    hg_models.AppliedAnnotation: hg_models.AppliedAnnotation.__name__,
    hg_models.Comment: hg_models.Comment.__name__,
    hg_models.NewLocation: 'Location',
}


APIClassType = Union[
    Type[AutograderModel],
    Type[ToDictMixin],
    Type[DictSerializableMixin],
    Type[User]
]
FieldType = Union[Field, ForeignObjectRel, property, cached_property]


class APIClassSchemaGenerator:
    _class: APIClassType

    @classmethod
    def factory(cls, class_: APIClassType) -> APIClassSchemaGenerator:
        if issubclass(class_, AutograderModel):
            return AGModelSchemaGenerator(cast(Type[AutograderModel], class_))

        if issubclass(class_, DictSerializableMixin):
            return DictSerializableSchemaGenerator(cast(Type[DictSerializableMixin], class_))

        if issubclass(class_, ToDictMixin):
            return HasToDictMixinSchemaGenerator(class_)

        if issubclass(class_, User):
            return UserSchemaGenerator(class_)

        if issubclass(class_, Enum):
            return EnumSchemaGenerator(class_)

        assert False

    def generate(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                name: _get_field_schema(_extract_field(name, self._class), self._class, name)
                for name in self._field_names()
            }
        }

    def _field_names(self) -> Sequence[str]:
        return []


class HasToDictMixinSchemaGenerator(APIClassSchemaGenerator):
    def __init__(self, class_: Type[ToDictMixin]):
        self._class = class_

    def _field_names(self) -> Sequence[str]:
        return self._class.get_serializable_fields()


class AGModelSchemaGenerator(HasToDictMixinSchemaGenerator):
    def __init__(self, class_: Type[AutograderModel]):
        self._class = class_

    def generate(self) -> dict:
        result = super().generate()
        result['required'] = self._get_required_fields()
        return result

    def _get_required_fields(self):
        return [
            field_name for field_name in self._class.get_serializable_fields()
            if self._field_is_required(field_name)
        ]

    def _field_is_required(self, field_name) -> bool:
        override = _PROP_FIELD_IS_REQUIRED_OVERRIDES.get(self._class, {}).get(field_name, None)
        if override is not None:
            return override

        try:
            field = cast(Type[AutograderModel], self._class)._meta.get_field(field_name)
            return (
                not field.many_to_many
                and not field.blank
                and field.default == fields.NOT_PROVIDED
            )
        except (FieldDoesNotExist, AttributeError):
            return False


class DictSerializableSchemaGenerator(HasToDictMixinSchemaGenerator):
    _class: Type[DictSerializableMixin]

    def __init__(self, class_: Type[DictSerializableMixin]):
        self._class = class_

    def generate(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                name: {
                    'description': self._class.get_field_descriptions().get(name, ''),
                    **_get_py_type_schema(self._class.get_field_type(name)),
                }
                for name in self._field_names()
            }
        }


class UserSchemaGenerator(APIClassSchemaGenerator):
    _fields = (
        'pk',
        'username',
        'first_name',
        'last_name',
        'is_superuser'
    )

    def __init__(self, class_: Type[User]):
        self._class = class_

    def generate(self) -> dict:
        result = super().generate()
        for name, prop in result['properties'].items():
            if name == 'username':
                prop['format'] = 'email'

        return result

    def _field_names(self) -> Sequence[str]:
        return self._fields


class EnumSchemaGenerator(APIClassSchemaGenerator):
    _class: Type[Enum]

    def __init__(self, class_: Type[Enum]):
        self._class = class_

    def generate(self) -> dict:
        return {
            'type': 'string',
            'enum': [item.value for item in self._class],
        }


def _extract_field(field_name: str, api_class: APIClassType) -> FieldType:
    """
    If api_class is a Django model, then returns the field's metadata.
    Otherwise, returns the class attribute named field_name using getattr.
    """
    try:
        return cast(Type[AutograderModel], api_class)._meta.get_field(field_name)
    except (FieldDoesNotExist, AttributeError):
        return getattr(api_class, field_name)


@singledispatch
def _get_field_schema(field: FieldType, api_class: APIClassType, name: str) -> dict:
    return {'type': 'unknown'}


@_get_field_schema.register(ForeignObjectRel)
@_get_field_schema.register(Field)
def _django_field(
    field: Union[Field, ForeignObjectRel],
    api_class: Union[Type[AutograderModel], Type[User]],
    name: str
) -> dict:
    read_only = False
    if issubclass(api_class, AutograderModel) and name not in api_class.get_editable_fields():
        read_only = True

    result: dict = {
        'readOnly': read_only,
        # str() is used to force processing of django lazy eval
        'description': str(field.help_text).strip() if hasattr(field, 'help_text') else '',
        'nullable': field.null,
    }

    if type(field) in _FIELD_TYPES:
        result.update(_FIELD_TYPES[type(field)])
        return result

    if isinstance(field, pg_fields.ArrayField):
        result.update({
            'type': 'array',
            'items': _get_field_schema(field.base_field, api_class, name),
        })
        return result

    if isinstance(field, ag_fields.ValidatedJSONField):
        result.update({
            'oneOf': [_as_schema_ref(field.serializable_class)]
        })
        return result

    if isinstance(field, ag_fields.EnumField):
        result.update({
            'oneOf': [_as_schema_ref(field.enum_type)]
        })
        return result

    if field.is_relation:
        model_class: Union[Type[AutograderModel], Type[User]] = field.model
        if field.many_to_many or field.one_to_many:
            result['nullable'] = False
            if field.name in model_class.get_serialize_related_fields():
                result.update({
                    'type': 'array',
                    'items': _as_schema_ref(field.related_model),
                })
                return result
            else:
                result.update({
                    'type': 'array',
                    'items': _PK_SCHEMA_READ_ONLY,
                })
                return result

        if field.name in model_class.get_serialize_related_fields():
            result.update({
                'oneOf': [_as_schema_ref(field.related_model)]
            })
            return result
        else:
            return _PK_SCHEMA_READ_ONLY

    return {'type': 'unknown'}


_FIELD_TYPES: Dict[Type[Field], dict] = {
    fields.IntegerField: {'type': 'integer'},
    fields.BigIntegerField: {'type': 'integer'},
    fields.FloatField: {'type': 'number'},
    fields.DecimalField: {'type': 'string', 'format': 'float'},
    fields.BooleanField: {'type': 'boolean'},
    fields.NullBooleanField: {'type': 'boolean'},
    fields.CharField: {'type': 'string'},
    fields.TextField: {'type': 'string'},
    fields.DateTimeField: {'type': 'string', 'format': 'date-time'},
    fields.TimeField: {'type': 'string', 'format': 'time'},
    fields.EmailField: {'type': 'string', 'format': 'email'},

    TimeZoneField: {'type': 'string', 'format': 'timezone'},

    pg_fields.JSONField: {'type': 'object'},

    ag_fields.ShortStringField: {'type': 'string'},
    ag_fields.StringArrayField: {'type': 'array', 'items': {'type': 'string'}},
}


@_get_field_schema.register
def _property(prop: property, api_class: APIClassType, name: str) -> dict:
    if name == 'pk':
        return _PK_SCHEMA_READ_ONLY

    result = {
        'readOnly': True,
        'description': _get_prop_description(prop),
    }
    result.update(_get_py_type_schema(get_type_hints(prop.fget).get('return', Any)))
    result.update(_PROP_FIELD_OVERRIDES.get(api_class, {}).get(name, {}))
    return result


@_get_field_schema.register
def _cached_property(prop: cached_property, api_class: APIClassType, name: str) -> dict:
    if name == 'pk':
        return _PK_SCHEMA_READ_ONLY

    result = {
        'readOnly': True,
        'description': _get_prop_description(prop),
    }
    result.update(_get_py_type_schema(get_type_hints(prop.func).get('return', Any)))
    result.update(_PROP_FIELD_OVERRIDES.get(api_class, {}).get(name, {}))
    return result


def _get_prop_description(prop: Union[property, cached_property]) -> str:
    description = ''
    if hasattr(prop, '__doc__') and prop.__doc__ is not None:
        description = prop.__doc__.strip()

    return description


_PROP_FIELD_OVERRIDES: Dict[APIClassType, Dict[str, dict]] = {
    ag_models.Group: {
        'member_names': {
            'readOnly': False,
        }
    }
}

_PROP_FIELD_IS_REQUIRED_OVERRIDES: Dict[APIClassType, Dict[str, bool]] = {
    ag_models.Group: {
        'member_names': True
    }
}


def _as_schema_ref(type: APIClassType) -> dict:
    return {'$ref': f'#/components/schemas/{API_OBJ_TYPE_NAMES[type]}'}


_PK_SCHEMA = {
    'type': 'integer',
    'format': 'id',
}


_PK_SCHEMA_READ_ONLY = {
    'type': 'integer',
    'format': 'id',
    'readOnly': True,
}


def _get_py_type_schema(type_: type) -> dict:
    origin = get_origin(type_)
    if origin is Union:
        result: dict = {}
        union_args = list(get_args(type_))
        if type(None) in union_args:
            result['nullable'] = True
            union_args.remove(type(None))

        if len(union_args) == 1:
            result.update(_get_py_type_schema(union_args[0]))
            return result

        result['anyOf'] = [_get_py_type_schema(arg) for arg in union_args]
        return result

    if origin is list or origin is tuple:
        return {
            'type': 'array',
            'items': _get_py_type_schema(get_args(type_)[0])
        }

    if type_ in API_OBJ_TYPE_NAMES:
        return _as_schema_ref(type_)

    # assert not isinstance(type_, ForwardRef), f'ForwardRef detected: {ForwardRef}'

    if type_ in _PY_ATTR_TYPES:
        return _PY_ATTR_TYPES[type_]

    if issubclass(type_, Enum):
        return {'oneOf': [_as_schema_ref(type_)]}

    return {'type': 'unknown'}


_PY_ATTR_TYPES = {
    int: {'type': 'integer'},
    float: {'type': 'number'},
    str: {'type': 'string'},
    bool: {'type': 'boolean'},
    Decimal: {'type': 'string', 'format': 'float'},
    dict: {'type': 'object'},
}

# =============================================================================


class AGViewSchemaGenerator(AutoSchema):
    def __init__(self, tags: List[APITags], api_class: Optional[APIClassType] = None):
        super().__init__()
        self._tags = [tag.value for tag in tags]
        self._api_class = api_class

    def get_operation(self, path, method) -> dict:
        result = self.get_operation_impl(path, method)
        result['tags'] = self._tags
        return result

    def get_operation_impl(self, path, method) -> dict:
        return super().get_operation(path, method)

    def generate_list_op_schema(self, base_result) -> dict:
        base_result['responses']['200']['content']['application/json']['schema']['items'] = (
            _as_schema_ref(self.get_api_class())
        )
        return base_result

    def generate_create_op_schema(self, base_result) -> dict:
        response_schema = base_result['responses'].pop('200')
        response_schema['content']['application/json']['schema'] = (
            _as_schema_ref(self.get_api_class())
        )
        base_result['responses']['201'] = response_schema

        base_result['requestBody'] = self.make_api_class_request_body()

        return base_result

    def generate_retrieve_op_schema(self, base_result):
        base_result['responses']['200']['content']['application/json']['schema'] = (
            _as_schema_ref(self.get_api_class())
        )

        return base_result

    def generate_patch_op_schema(self, base_result):
        base_result['responses']['200']['content']['application/json']['schema'] = (
            _as_schema_ref(self.get_api_class())
        )

        base_result['requestBody'] = self.make_api_class_request_body()

        return base_result

    def get_api_class(self) -> APIClassType:
        if self._api_class is not None:
            return self._api_class

        if not hasattr(self.view, 'model_manager'):
            raise Exception(
                'View class has no "model_manager" and '
                'the value provided for "api_class" was None'
            )

        return self.view.model_manager.model

    def make_api_class_request_body(self) -> dict:
        return {
            'required': True,
            'content': {
                'application/json': {
                    'schema': _as_schema_ref(self.get_api_class())
                }
            }
        }


class AGListViewSchemaMixin:
    def get_operation_impl(self, path, method):
        base_result = super().get_operation_impl(path, method)
        if method == 'GET':
            return self.generate_list_op_schema(base_result)

        return base_result


class AGCreateViewSchemaMixin:
    def get_operation_impl(self, path, method):
        base_result = super().get_operation_impl(path, method)
        if method == 'POST':
            return self.generate_create_op_schema(base_result)

        return base_result


class AGListCreateViewSchemaGenerator(
    AGListViewSchemaMixin, AGCreateViewSchemaMixin, AGViewSchemaGenerator
):
    pass


class AGRetrieveViewSchemaMixin:
    def get_operation_impl(self, path, method):
        base_result = super().get_operation_impl(path, method)
        if method == 'GET':
            return self.generate_retrieve_op_schema(base_result)

        return base_result


class AGPatchViewSchemaMixin:
    def get_operation_impl(self, path, method):
        base_result = super().get_operation_impl(path, method)
        if method == 'PATCH':
            return self.generate_patch_op_schema(base_result)

        return base_result


class AGDetailViewSchemaGenerator(
    AGRetrieveViewSchemaMixin, AGPatchViewSchemaMixin, AGViewSchemaGenerator
):
    pass


class CustomViewDict(TypedDict, total=False):
    GET: CustomViewMethodData
    POST: CustomViewMethodData
    PUT: CustomViewMethodData
    PATCH: CustomViewMethodData
    DELETE: CustomViewMethodData


class CustomViewMethodData(TypedDict, total=False):
    parameters: List[RequestParam]
    # Key = param name, Value = schema dict
    param_schema_overrides: Dict[str, dict]
    request_payload: RequestBodyData
    # Key = response status
    responses: Dict[str, Optional[ResponseSchemaData]]


# https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#parameter-object
RequestParam = TypedDict('RequestParam', {
    'name': str,
    'in': str,
    'schema': dict,
    'description': str,
    'required': bool,
    'deprecated': bool,
    'allowEmptyValue': bool
}, total=False)


class RequestBodyData(TypedDict, total=False):
    # Defaults to 'application/json'
    content_type: str
    # Stored under the 'schema' key
    body: dict

    examples: dict


class ResponseSchemaData(TypedDict, total=False):
    # Defaults to 'application/json'
    content_type: str
    # Stored under the 'schema' key
    body: dict


HTTPMethodName = Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE']


class CustomViewSchema(AGViewSchemaGenerator):
    def __init__(self, tags: List[APITags],
                 data: CustomViewDict,
                 api_class: Optional[APIClassType] = None):
        super().__init__(tags, api_class=api_class)
        self.data = data

    def get_operation_impl(self, path, method: HTTPMethodName) -> dict:
        result = super().get_operation_impl(path, method)
        method_data = self.data.get(method, None)
        if method_data is None:
            return result

        if 'parameters' in method_data:
            result['parameters'] = method_data['parameters']

        for param_name, schema in method_data.get('param_schema_overrides', {}).items():
            param = utils.find_if(result['parameters'], lambda item: item['name'] == param_name)
            param['schema'] = schema

        if 'request_payload' in method_data:
            request_data = method_data['request_payload']
            result['requestBody'] = {
                'required': True,
                'content': {
                    request_data.get('content_type', 'application/json'): {
                        'schema': request_data['body'],
                        'examples': request_data.get('examples', {})
                    },
                }
            }

        responses: Dict[str, dict] = {}
        for status, response_data in method_data.get('responses', {}).items():
            if response_data is None:
                responses[status] = {}
            elif 'body' in response_data:
                responses[status] = {
                    'content': {
                        response_data.get('content_type', 'application/json'): {
                            'schema': response_data['body']
                        }
                    }
                }

        if responses:
            result['responses'] = responses

        return result
