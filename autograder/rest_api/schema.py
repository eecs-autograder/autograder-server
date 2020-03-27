from __future__ import annotations

import sys
from decimal import Decimal
from enum import Enum
from functools import singledispatch
from typing import (Any, Dict, ForwardRef, List, Sequence, Tuple, Type, Union,
                    cast, get_args, get_origin, get_type_hints)

import django.contrib.postgres.fields as pg_fields
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Field, fields
from django.db.models.fields.reverse_related import ForeignObjectRel
from django.utils.functional import cached_property
from rest_framework.schemas.openapi import SchemaGenerator
from timezone_field.fields import TimeZoneField

import autograder.core.fields as ag_fields
import autograder.core.models as ag_models
import autograder.handgrading.models as hg_models
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
        schema = super().get_schema(request=request, public=public)
        schema['components'] = self._get_model_schemas()
        return schema

    def _get_model_schemas(self) -> dict:
        return {
            'schemas': {
                name: APIClassSchemaGenerator.factory(class_).generate()
                for class_, name in API_OBJ_TYPE_NAMES.items()
            }
        }


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

    # def generate(self) -> dict:
    #     pass

    def _field_names(self) -> Sequence[str]:
        return self._class.get_serializable_fields()


class AGModelSchemaGenerator(HasToDictMixinSchemaGenerator):
    def __init__(self, class_: Type[AutograderModel]):
        self._class = class_

    # We'll build CreateModelRequest schemas separately
    # def generate(self) -> dict:
    #     result = super().generate()
    #     result['required'] = self._get_required_fields()
    #     return result

    # def _get_required_fields(self):
    #     return []


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
        'email',
        'is_superuser'
    )

    def __init__(self, class_: Type[User]):
        self._class = class_

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
        'read_only': read_only,
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
                    'items': _PK_SCHEMA,
                })
                return result

        if field.name in model_class.get_serialize_related_fields():
            result.update({
                'oneOf': [_as_schema_ref(field.related_model)]
            })
            return result
        else:
            return _PK_SCHEMA

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
        return _PK_SCHEMA

    result = {
        'readOnly': True,
        'description': _get_prop_description(prop),
    }
    result.update(_get_py_type_schema(get_type_hints(prop.fget).get('return', Any)))
    return result


@_get_field_schema.register
def _cached_property(prop: cached_property, api_class: APIClassType, name: str) -> dict:
    if name == 'pk':
        return _PK_SCHEMA

    result = {
        'readOnly': True,
        'description': _get_prop_description(prop),
    }
    result.update(_get_py_type_schema(get_type_hints(prop.func).get('return', Any)))
    return result


def _get_prop_description(prop: Union[property, cached_property]) -> str:
    description = ''
    if hasattr(prop, '__doc__') and prop.__doc__ is not None:
        description = prop.__doc__.strip()

    return description


def _as_schema_ref(type: APIClassType) -> dict:
    return {'$ref': f'#/components/schemas/{API_OBJ_TYPE_NAMES[type]}'}


_PK_SCHEMA = {
    'type': 'integer',
    'format': 'id',
    'read_only': True,
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

    assert not isinstance(type_, ForwardRef), f'ForwardRef detected: {ForwardRef}'

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
