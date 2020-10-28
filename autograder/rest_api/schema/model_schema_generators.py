from __future__ import annotations

import copy
from decimal import Decimal
from enum import Enum
from functools import singledispatch
from typing import (
    Any, Dict, List, Mapping, Optional, Sequence, Type, TypeVar, Union, cast, get_args, get_origin,
    get_type_hints
)

import django.contrib.postgres.fields as pg_fields
from django.contrib.auth.models import User
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Field, Model, fields
from django.db.models.fields.related import RelatedField
from django.db.models.fields.reverse_related import ForeignObjectRel
from django.utils.functional import cached_property
from timezone_field.fields import TimeZoneField  # type: ignore

import autograder.core.fields as ag_fields
import autograder.core.models as ag_models
import autograder.handgrading.models as hg_models
from autograder.core.models.ag_model_base import AutograderModel, DictSerializable, ToDictMixin
from autograder.core.submission_feedback import (
    AGTestCaseResultFeedback, AGTestCommandResultFeedback, AGTestSuiteResultFeedback,
    SubmissionResultFeedback
)
from autograder.rest_api.schema.openapi_types import (
    OrRef, ParameterObject, ReferenceObject, SchemaObject
)


def generate_model_schemas() -> Dict[str, OrRef[SchemaObject]]:
    result: Dict[str, OrRef[SchemaObject]] = {
        name: APIClassSchemaGenerator.factory(class_).generate()
        for class_, name in API_OBJ_TYPE_NAMES.items()
    }

    result['UserRoles'] = {
        'type': 'object',
        'properties': {
            'is_admin': {'type': 'boolean'},
            'is_staff': {'type': 'boolean'},
            'is_student': {'type': 'boolean'},
            'is_handgrader': {'type': 'boolean'},
        }
    }

    result['SubmissionWithResults'] = {
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


def generate_parameter_schemas() -> Dict[str, OrRef[ParameterObject]]:
    fdbk_category: ParameterObject = {
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

    required_fdbk_category: ParameterObject = copy.copy(fdbk_category)
    required_fdbk_category['required'] = True

    include_staff: ParameterObject = {
        'name': 'include_staff',
        'in': 'query',
        'description': ('When "false", excludes staff and admin users '
                        'from the results. Defaults to "true".'),
        'schema': {
            'type': 'string',
            'enum': ['true', 'false'],
            'default': 'true',
        }
    }

    page: ParameterObject = {
        'name': 'page',
        'in': 'query',
        'schema': {'type': 'integer'}
    }

    return {
        'feedbackCategory': fdbk_category,
        'requiredFeedbackCategory': fdbk_category,
        'includeStaff': include_staff,
        'page': page
    }


API_OBJ_TYPE_NAMES: Dict[APIClassType, str] = {
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
    ag_models.AGTestSuiteFeedbackConfig: 'AGTestSuiteFeedbackConfig',
    ag_models.AGTestCase: ag_models.AGTestCase.__name__,
    ag_models.AGTestCaseFeedbackConfig: 'AGTestCaseFeedbackConfig',
    ag_models.AGTestCommand: ag_models.AGTestCommand.__name__,
    ag_models.AGTestCommandFeedbackConfig: 'AGTestCommandFeedbackConfig',

    ag_models.StdinSource: ag_models.StdinSource.__name__,
    ag_models.ExpectedOutputSource: ag_models.ExpectedOutputSource.__name__,
    ag_models.ExpectedReturnCode: ag_models.ExpectedReturnCode.__name__,
    ag_models.ValueFeedbackLevel: ag_models.ValueFeedbackLevel.__name__,

    SubmissionResultFeedback: SubmissionResultFeedback.__name__,
    AGTestSuiteResultFeedback: AGTestSuiteResultFeedback.__name__,
    AGTestCaseResultFeedback: AGTestCaseResultFeedback.__name__,
    AGTestCommandResultFeedback: AGTestCommandResultFeedback.__name__,
    ag_models.FeedbackCategory: ag_models.FeedbackCategory.__name__,

    ag_models.MutationTestSuite: ag_models.MutationTestSuite.__name__,
    ag_models.MutationTestSuiteFeedbackConfig: ag_models.MutationTestSuiteFeedbackConfig.__name__,
    ag_models.BugsExposedFeedbackLevel: ag_models.BugsExposedFeedbackLevel.__name__,
    ag_models.MutationTestSuiteResult.FeedbackCalculator: 'MutationTestSuiteResultFeedback',

    ag_models.RerunSubmissionsTask: ag_models.RerunSubmissionsTask.__name__,

    hg_models.HandgradingRubric: hg_models.HandgradingRubric.__name__,
    hg_models.PointsStyle: hg_models.PointsStyle.__name__,
    hg_models.Criterion: hg_models.Criterion.__name__,
    hg_models.Annotation: hg_models.Annotation.__name__,
    hg_models.HandgradingResult: hg_models.HandgradingResult.__name__,
    hg_models.CriterionResult: hg_models.CriterionResult.__name__,
    hg_models.AppliedAnnotation: hg_models.AppliedAnnotation.__name__,
    hg_models.Comment: hg_models.Comment.__name__,
    hg_models.Location: hg_models.Location.__name__,
}

APIClassType = Union[
    Type[AutograderModel],
    Type[ToDictMixin],
    Type[DictSerializable],
    Type[Model],
    Type[Enum]
]
FieldType = Union[Field, ForeignObjectRel, property, cached_property]


class APIClassSchemaGenerator:
    _class: APIClassType

    def __init__(self, class_: APIClassType):
        self._class: APIClassType = class_

    @staticmethod
    def factory(class_: APIClassType) -> APIClassSchemaGenerator:
        if issubclass(class_, AutograderModel):
            return AGModelSchemaGenerator(class_)

        if issubclass(class_, DictSerializable):
            return DictSerializableSchemaGenerator(class_)

        if issubclass(class_, ToDictMixin):
            return HasToDictMixinSchemaGenerator(class_)

        if issubclass(class_, User):
            return UserSchemaGenerator(class_)

        if issubclass(class_, Enum):
            return EnumSchemaGenerator(class_)

        assert False

    def generate(self) -> SchemaObject:
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
    def generate_request_body_schema(
        self, *, include_required: bool
    ) -> Optional[SchemaObject]:
        return None

    def _field_names(self) -> Sequence[str]:
        return []


HasToDictMixinType = TypeVar('HasToDictMixinType', bound=Type[ToDictMixin])


class HasToDictMixinSchemaGenerator(APIClassSchemaGenerator):
    _class: Type[ToDictMixin]

    def __init__(self, class_: Type[ToDictMixin]):
        self._class = class_

    def _field_names(self) -> Sequence[str]:
        return self._class.get_serializable_fields()


class AGModelSchemaGenerator(HasToDictMixinSchemaGenerator):
    _class: Type[AutograderModel]

    def __init__(self, class_: Type[AutograderModel]):
        self._class = class_

    def generate_request_body_schema(
        self, *, include_required: bool
    ) -> Optional[SchemaObject]:
        result: SchemaObject = {
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

    def _get_required_fields(self) -> List[str]:
        return [
            field_name for field_name in self._class.get_serializable_fields()
            if self._field_is_required(field_name)
        ]

    def _field_is_required(self, field_name: str) -> bool:
        override = _PROP_FIELD_IS_REQUIRED_OVERRIDES.get(self._class, {}).get(field_name, None)
        if override is not None:
            return override

        try:
            field = self._class._meta.get_field(field_name)
            return (
                # Remove this cast once django-stubs fixes:
                # https://github.com/typeddjango/django-stubs/issues/447
                not cast('RelatedField[object, object]', field).many_to_many
                and not field.blank
                and field.default == fields.NOT_PROVIDED
            )
        except (FieldDoesNotExist, AttributeError):
            return False


class DictSerializableSchemaGenerator(HasToDictMixinSchemaGenerator):
    _class: Type[DictSerializable]

    def __init__(self, class_: Type[DictSerializable]):
        self._class = class_

    def generate(self) -> SchemaObject:
        return {
            'type': 'object',
            'properties': {

                name: {
                    'description': self._class.get_field_descriptions().get(name, ''),
                    # See if type checking works with dict union in Python 3.9
                    **_get_py_type_schema(self._class.get_field_type(name))
                }
                for name in self._field_names()
            }
        }


class UserSchemaGenerator(APIClassSchemaGenerator):
    _class: Type[User]

    def __init__(self, class_: Type[User]):
        self._class = class_

    _fields = (
        'pk',
        'username',
        'first_name',
        'last_name',
        'is_superuser'
    )

    def generate(self) -> SchemaObject:
        result = super().generate()
        for name, prop in result['properties'].items():
            if name == 'username':
                # We know this wont be a ReferenceObject. Since this
                # is a "faux recursive" SchemaObject context, we'll
                # just cast to SchemaObject.
                assert '$ref' not in prop
                cast(SchemaObject, prop)['format'] = 'email'

        return result

    def _field_names(self) -> Sequence[str]:
        return self._fields


class EnumSchemaGenerator(APIClassSchemaGenerator):
    _class: Type[Enum]

    def __init__(self, class_: Type[Enum]):
        self._class = class_

    def generate(self) -> SchemaObject:
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
        return cast(property, getattr(api_class, field_name))


@singledispatch
def _get_field_schema(
    field: FieldType,
    api_class: APIClassType,
    name: str,
    include_readonly: bool = False
) -> SchemaObject:
    return {'type': 'unknown'}


@_get_field_schema.register(ForeignObjectRel)
@_get_field_schema.register(Field)
def _django_field(
    field: Field[object, object],
    api_class: Type[AutograderModel],
    name: str,
    include_readonly: bool = False
) -> SchemaObject:
    read_only = False
    if issubclass(api_class, AutograderModel) and name not in api_class.get_editable_fields():
        read_only = True

    result: SchemaObject = {
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
        related_field = cast('RelatedField[object, object]', field)
        if related_field.many_to_many or related_field.one_to_many:
            if isinstance(field, ForeignObjectRel):
                result['nullable'] = False
            if field.name in api_class.get_serialize_related_fields():
                result.update({
                    'type': 'array',
                    'items': as_schema_ref(related_field.related_model),
                })
                return result
            else:
                result.update({
                    'type': 'array',
                    'items': _PK_SCHEMA,
                })
                return result

        if field.name in api_class.get_serialize_related_fields():
            result.update({
                'allOf': [as_schema_ref(related_field.related_model)]
            })
            return result
        else:
            result.update(_PK_SCHEMA)
            return result

    return {'type': 'unknown'}


_FIELD_TYPES: Dict[Type[Field[object, object]], SchemaObject] = {
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
) -> SchemaObject:
    if name == 'pk':
        return _PK_SCHEMA_READ_ONLY if include_readonly else _PK_SCHEMA

    result: SchemaObject = {
        'description': _get_prop_description(prop),
    }
    if include_readonly:
        result['readOnly'] = True
    result.update(
        assert_not_ref(
            _get_py_type_schema(get_type_hints(prop.fget).get('return', Any))
        )
    )
    result.update(_PROP_FIELD_OVERRIDES.get(api_class, {}).get(name, {}))
    return result


@_get_field_schema.register(cached_property)
def _cached_property(
    prop: 'cached_property[object]',
    api_class: APIClassType,
    name: str,
    include_readonly: bool = False
) -> SchemaObject:
    if name == 'pk':
        return _PK_SCHEMA_READ_ONLY if include_readonly else _PK_SCHEMA

    result: SchemaObject = {
        'description': _get_prop_description(prop),
    }
    if include_readonly:
        result['readOnly'] = True
    result.update(
        assert_not_ref(
            _get_py_type_schema(get_type_hints(prop.func).get('return', Any))
        )
    )
    result.update(_PROP_FIELD_OVERRIDES.get(api_class, {}).get(name, {}))
    return result


def _get_prop_description(prop: Union[property, cached_property[object]]) -> str:
    description = ''
    if hasattr(prop, '__doc__') and prop.__doc__ is not None:
        description = prop.__doc__.strip()

    return description


_PROP_FIELD_OVERRIDES: Dict[APIClassType, Dict[str, SchemaObject]] = {
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


_PK_SCHEMA: SchemaObject = {
    'type': 'integer',
    'format': 'id',
}


_PK_SCHEMA_READ_ONLY: SchemaObject = {
    'type': 'integer',
    'format': 'id',
    'readOnly': True,
}


def _get_py_type_schema(type_: type) -> OrRef[SchemaObject]:
    origin = get_origin(type_)
    if origin is Union:
        result: SchemaObject = {}
        union_args = list(get_args(type_))
        if type(None) in union_args:
            result['nullable'] = True
            union_args.remove(type(None))

        if len(union_args) == 1:
            py_type_schema = _get_py_type_schema(union_args[0])
            if '$ref' not in py_type_schema:
                result.update(cast(SchemaObject, py_type_schema))
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


_PY_ATTR_TYPES: Dict[type, SchemaObject] = {
    int: {'type': 'integer'},
    float: {'type': 'number'},
    str: {'type': 'string'},
    bool: {'type': 'boolean'},
    Decimal: {'type': 'string', 'format': 'float'},
    dict: {'type': 'object'},
}


def as_schema_ref(type_: APIClassType) -> ReferenceObject:
    return {'$ref': f'#/components/schemas/{API_OBJ_TYPE_NAMES[type_]}'}


_NonRefType = TypeVar('_NonRefType', bound=Mapping[str, object])


def assert_not_ref(obj: OrRef[_NonRefType]) -> _NonRefType:
    assert '$ref' not in obj, obj
    return cast(_NonRefType, obj)
