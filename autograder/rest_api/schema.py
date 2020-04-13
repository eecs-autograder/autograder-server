from __future__ import annotations

import enum
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
        stderr('Try to generate better operationIds')
        stderr('Fix anyOf and oneOf examples')
        schema = super().get_schema(request=request, public=public)
        schema['components'] = self._get_model_schemas()
        schema['components']['parameters'] = self._get_parameter_schemas()
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

        result['schemas']['SubmissionWithResults'] = {
            'allOf': [
                as_schema_ref(ag_models.Submission),
                {
                    'type': 'object',
                    'properties': {
                        'results': as_schema_ref(SubmissionResultFeedback)
                    }
                }
            ]
        }

        return result

    def _get_parameter_schemas(self) -> dict:
        fdbk_category = {
            'name': 'feedback_category',
            'in': 'query',
            'schema': as_schema_ref(ag_models.FeedbackCategory),
            'description': f'''
The category of feedback being requested. Must be one of the following
values:

- {ag_models.FeedbackCategory.normal.value}: Can be requested by
    students before or after the project deadline on their
    submissions that did not exceed the daily limit.
- {ag_models.FeedbackCategory.past_limit_submission.value}: Can be
    requested by students on their submissions that exceeded the
    daily limit.
- {ag_models.FeedbackCategory.ultimate_submission.value}: Can be
    requested by students on their own ultimate (a.k.a. final
    graded) submission once the project deadline has passed and
    hide_ultimate_submission_fdbk has been set to False on the
    project. Can similarly be requested by staff when looking
    up another user's ultimate submission results after the
    deadline.
- {ag_models.FeedbackCategory.staff_viewer.value}: Can be requested
    by staff when looking up another user's submission results.
- {ag_models.FeedbackCategory.max.value}: Can be requested by staff
    on their own submissions.'''.strip()
        }

        required_fdbk_category: dict = dict(fdbk_category)
        required_fdbk_category['required'] = True

        return {'feedbackCategory': fdbk_category, 'requiredFeedbackCategory': fdbk_category}


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
    ag_models.BugsExposedFeedbackLevel: ag_models.BugsExposedFeedbackLevel.__name__,
    # Hack: SubmissionResultFeedback.student_test_suite_results returns
    # List[StudentTestSuiteResult], but it gets serialized to StudentTestSuiteResultFeedback
    ag_models.StudentTestSuiteResult: 'StudentTestSuiteResultFeedback',
    ag_models.StudentTestSuiteResult.FeedbackCalculator: 'StudentTestSuiteResultFeedback',

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

    # Generate a version of the schema for this class that includes
    # only the fields that are allowed in create (POST) and update (PATCH)
    # requests.
    def generate_request_body_schema(self, *, include_required: bool) -> Optional[dict]:
        return None

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

    def generate_request_body_schema(self, *, include_required: bool):
        result = {
            'type': 'object',
            'properties': {
                name: _get_field_schema(
                    _extract_field(name, self._class),
                    self._class,
                    name,
                    include_readonly=True
                )
                for name in self._field_names()
            }
        }
        if include_required:
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
def _get_field_schema(
    field: FieldType,
    api_class: APIClassType,
    name: str,
    include_readonly: bool = False
) -> dict:
    return {'type': 'unknown'}


@_get_field_schema.register(ForeignObjectRel)
@_get_field_schema.register(Field)
def _django_field(
    field: Union[Field, ForeignObjectRel],
    api_class: Union[Type[AutograderModel], Type[User]],
    name: str,
    include_readonly: bool = False
) -> dict:
    read_only = False
    if issubclass(api_class, AutograderModel) and name not in api_class.get_editable_fields():
        read_only = True

    result: dict = {
        # str() is used to force processing of django lazy eval
        'description': str(field.help_text).strip() if hasattr(field, 'help_text') else '',
        'nullable': field.null,
    }

    if include_readonly:
        result['readOnly'] = read_only

    if type(field) in _FIELD_TYPES:
        result.update(_FIELD_TYPES[type(field)])
        return result

    if isinstance(field, pg_fields.ArrayField):
        result.update({
            'type': 'array',
            # We want include_readonly to be False for recursive calls.
            'items': _get_field_schema(field.base_field, api_class, name),
        })
        return result

    if isinstance(field, ag_fields.ValidatedJSONField):
        result.update({
            'allOf': [as_schema_ref(field.serializable_class)]
        })
        return result

    if isinstance(field, ag_fields.EnumField):
        result.update({
            'allOf': [as_schema_ref(field.enum_type)]
        })
        return result

    if field.is_relation:
        model_class: Union[Type[AutograderModel], Type[User]] = field.model
        if field.many_to_many or field.one_to_many:
            if isinstance(field, ForeignObjectRel):
                result['nullable'] = False
            if field.name in model_class.get_serialize_related_fields():
                result.update({
                    'type': 'array',
                    'items': as_schema_ref(field.related_model),
                })
                return result
            else:
                result.update({
                    'type': 'array',
                    'items': _PK_SCHEMA,
                })
                return result

        if field.name in model_class.get_serialize_related_fields():
            result.update({
                'allOf': [as_schema_ref(field.related_model)]
            })
            return result
        else:
            result.update(_PK_SCHEMA)
            return result

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
def _property(
    prop: property,
    api_class: APIClassType,
    name: str,
    include_readonly: bool = False
) -> dict:
    if name == 'pk':
        return _PK_SCHEMA_READ_ONLY if include_readonly else _PK_SCHEMA

    result: dict = {
        'description': _get_prop_description(prop),
    }
    if include_readonly:
        result['readOnly'] = True
    result.update(_get_py_type_schema(get_type_hints(prop.fget).get('return', Any)))
    result.update(_PROP_FIELD_OVERRIDES.get(api_class, {}).get(name, {}))
    return result


@_get_field_schema.register
def _cached_property(
    prop: cached_property,
    api_class: APIClassType,
    name: str,
    include_readonly: bool = False
) -> dict:
    if name == 'pk':
        return _PK_SCHEMA_READ_ONLY if include_readonly else _PK_SCHEMA

    result: dict = {
        'description': _get_prop_description(prop),
    }
    if include_readonly:
        result['readOnly'] = True
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


def as_schema_ref(type_: APIClassType) -> RefDict:
    return {'$ref': f'#/components/schemas/{API_OBJ_TYPE_NAMES[type_]}'}


_PK_SCHEMA: dict = {
    'type': 'integer',
    'format': 'id',
}


_PK_SCHEMA_READ_ONLY: dict = {
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
        return as_schema_ref(type_)

    # assert not isinstance(type_, ForwardRef), f'ForwardRef detected: {ForwardRef}'

    if type_ in _PY_ATTR_TYPES:
        return _PY_ATTR_TYPES[type_]

    if issubclass(type_, Enum):
        return {'allOf': [as_schema_ref(type_)]}

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


# Defines the order of API tags and provides a single point of
# maintenance for their string values.
class APITags(enum.Enum):
    users = 'users'
    courses = 'courses'
    rosters = 'rosters'
    permissions = 'permissions'

    projects = 'projects'
    instructor_files = 'instructor_files'
    expected_student_files = 'expected_student_files'

    sandbox_docker_images = 'sandbox_docker_images'

    ag_test_suites = 'ag_test_suites'
    ag_test_cases = 'ag_test_cases'
    ag_test_commands = 'ag_test_commands'

    student_test_suites = 'student_test_suites'

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
            as_schema_ref(self.get_api_class())
        )
        return base_result

    def generate_create_op_schema(self, base_result) -> dict:
        response_schema = base_result['responses'].pop('200')
        response_schema['content']['application/json']['schema'] = (
            as_schema_ref(self.get_api_class())
        )
        base_result['responses']['201'] = response_schema

        base_result['requestBody'] = self.make_api_class_request_body(include_required=True)

        return base_result

    def generate_retrieve_op_schema(self, base_result):
        base_result['responses']['200']['content']['application/json']['schema'] = (
            as_schema_ref(self.get_api_class())
        )

        return base_result

    def generate_patch_op_schema(self, base_result):
        base_result['responses']['200']['content']['application/json']['schema'] = (
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

        return self.view.model_manager.model

    def make_api_class_request_body(self, *, include_required: bool) -> dict:
        body_schema = AGModelSchemaGenerator.factory(
            self.get_api_class()).generate_request_body_schema(include_required=include_required)
        schema = (body_schema if body_schema is not None
                  else as_schema_ref(self.get_api_class()))
        return {
            'required': True,
            'content': {
                'application/json': {
                    'schema': schema
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
    parameters: List[Union[RequestParam, RefDict]]
    # Key = param name, Value = schema dict
    # Use for fixing the types of DRF-generated URL params.
    param_schema_overrides: Dict[str, dict]
    request_payload: RequestBodyData
    # Key = response status
    responses: Dict[str, Optional[ResponseSchemaData]]


RefDict = TypedDict('RefDict', {'$ref': str})


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
    description: str


class ResponseSchemaData(TypedDict, total=False):
    # Defaults to 'application/json'
    content_type: str
    # Stored under the 'schema' key
    body: dict

    examples: dict
    description: str


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

        result.setdefault('parameters', [])
        if 'parameters' in method_data:
            result['parameters'] += method_data['parameters']

        for param_name, schema in method_data.get('param_schema_overrides', {}).items():
            param = utils.find_if(result['parameters'], lambda item: item['name'] == param_name)
            param['schema'] = schema

        if 'request_payload' in method_data:
            request_data = method_data['request_payload']
            body = {
                'schema': request_data['body'],
            }
            if 'examples' in request_data:
                body['examples'] = request_data['examples']
            result['requestBody'] = {
                'required': True,
                'content': {
                    request_data.get('content_type', 'application/json'): body
                }
            }
            if 'description' in request_data:
                result['description'] = request_data['description']

        responses: Dict[str, dict] = {}
        for status, response_data in method_data.get('responses', {}).items():
            if response_data is None:
                responses[status] = {}
            elif 'body' in response_data:
                body = {
                    'schema': response_data['body']
                }
                if 'examples' in response_data:
                    body['examples'] = response_data['examples']
                responses[status] = {
                    'content': {
                        response_data.get('content_type', 'application/json'): body
                    }
                }
                if 'description' in response_data:
                    responses[status]['description'] = response_data['description']

        if responses:
            result['responses'] = responses

        return result


class OrderViewSchema(CustomViewSchema):
    def __init__(self, tags: List[APITags]):
        super().__init__(tags, {
            'GET': {
                'responses': {
                    '200': {
                        'body': {
                            'type': 'array',
                            'items': {'type': 'integer', 'format': 'id'}
                        }
                    }
                }
            },
            'PUT': {
                'request_payload': {
                    'body': {
                        'type': 'array',
                        'items': {'type': 'integer', 'format': 'id'}
                    }
                },
                'responses': {
                    '200': {
                        'body': {
                            'type': 'array',
                            'items': {'type': 'integer', 'format': 'id'}
                        }
                    }
                }
            }
        })
