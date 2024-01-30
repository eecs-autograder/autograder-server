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
from django.db import models
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
    result: Dict[str, OrRef[SchemaObject]] = {}
    for class_, name in _API_OBJ_TYPE_NAMES.items():
        generator = APIClassSchemaGenerator.factory(class_)
        result[name] = generator.generate()

        if class_ in _API_CREATE_OBJ_TYPE_NAMES:
            create_name = _API_CREATE_OBJ_TYPE_NAMES[class_]
            if class_ in _CREATE_BODY_OVERRIDES:
                if _CREATE_BODY_OVERRIDES[class_] is not None:
                    result[create_name] = _CREATE_BODY_OVERRIDES[class_]
            else:
                result[create_name] = (
                    generator.generate_create_model_schema()
                )

        if class_ in _API_UPDATE_OBJ_TYPE_NAMES:
            update_name = _API_UPDATE_OBJ_TYPE_NAMES[class_]
            if class_ in _UPDATE_BODY_OVERRIDES:
                if _UPDATE_BODY_OVERRIDES[class_] is not None:
                    result[update_name] = _UPDATE_BODY_OVERRIDES[class_]
            else:
                result[update_name] = (
                    generator.generate_request_body_schema(include_required=False)
                )

    result['UserRoles'] = {
        'type': 'object',
        'properties': {
            'is_admin': {'type': 'boolean'},
            'is_staff': {'type': 'boolean'},
            'is_student': {'type': 'boolean'},
            'is_handgrader': {'type': 'boolean'},
        },
        'required': [
            'is_admin',
            'is_staff',
            'is_student',
            'is_handgrader',
        ],
    }

    result['SubmissionWithResults'] = {
        'allOf': [
            as_schema_ref(ag_models.Submission),
            {
                'type': 'object',
                'properties': {
                    'results': as_schema_ref(SubmissionResultFeedback)
                },
                'required': ['results']
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


def register_api_object_type_name(api_class: APIClassType, name: str | None = None) -> None:
    global _API_OBJ_TYPE_NAMES
    if name is None:
        name = api_class.__name__

    _API_OBJ_TYPE_NAMES[api_class] = name


def get_api_object_type_name(api_class: APIClassType) -> str:
    return _API_OBJ_TYPE_NAMES[api_class]


def api_object_type_name_is_registered(api_class: APIClassType) -> bool:
    return api_class in _API_OBJ_TYPE_NAMES


_API_OBJ_TYPE_NAMES: Dict[APIClassType, str] = {
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

_API_CREATE_OBJ_TYPE_NAMES: Dict[APIClassType, str] = {
    # User: 'User',
    ag_models.Course: 'Create' + ag_models.Course.__name__,
    # ag_models.Semester: ag_models.Semester.__name__,
    ag_models.Project: 'Create' + ag_models.Project.__name__,
    # ag_models.UltimateSubmissionPolicy: ag_models.UltimateSubmissionPolicy.__name__,
    ag_models.ExpectedStudentFile: 'Create' + ag_models.ExpectedStudentFile.__name__,
    ag_models.InstructorFile: 'Create' + ag_models.InstructorFile.__name__,
    ag_models.DownloadTask: 'Create' + ag_models.DownloadTask.__name__,
    # ag_models.DownloadType: ag_models.DownloadType.__name__,
    ag_models.Group: 'Create' + ag_models.Group.__name__,
    ag_models.GroupInvitation: 'Create' + ag_models.GroupInvitation.__name__,
    ag_models.Submission: 'Create' + ag_models.Submission.__name__,

    # ag_models.Command: ag_models.Command.__name__,

    # ag_models.SandboxDockerImage: ag_models.SandboxDockerImage.__name__,
    ag_models.BuildSandboxDockerImageTask: 'BuildSandboxDockerImage',
    # ag_models.BuildImageStatus: ag_models.BuildImageStatus.__name__,
    ag_models.AGTestSuite: 'Create' + ag_models.AGTestSuite.__name__,
    # ag_models.AGTestSuiteFeedbackConfig: 'AGTestSuiteFeedbackConfig',
    ag_models.AGTestCase: 'Create' + ag_models.AGTestCase.__name__,
    # ag_models.AGTestCaseFeedbackConfig: 'AGTestCaseFeedbackConfig',
    ag_models.AGTestCommand: 'Create' + ag_models.AGTestCommand.__name__,
    # ag_models.AGTestCommandFeedbackConfig: 'AGTestCommandFeedbackConfig',

    # ag_models.StdinSource: ag_models.StdinSource.__name__,
    # ag_models.ExpectedOutputSource: ag_models.ExpectedOutputSource.__name__,
    # ag_models.ExpectedReturnCode: ag_models.ExpectedReturnCode.__name__,
    # ag_models.ValueFeedbackLevel: ag_models.ValueFeedbackLevel.__name__,

    # SubmissionResultFeedback: SubmissionResultFeedback.__name__,
    # AGTestSuiteResultFeedback: AGTestSuiteResultFeedback.__name__,
    # AGTestCaseResultFeedback: AGTestCaseResultFeedback.__name__,
    # AGTestCommandResultFeedback: AGTestCommandResultFeedback.__name__,
    # ag_models.FeedbackCategory: ag_models.FeedbackCategory.__name__,

    ag_models.MutationTestSuite: 'Create' + ag_models.MutationTestSuite.__name__,
    # ag_models.MutationTestSuiteFeedbackConfig: ag_models.MutationTestSuiteFeedbackConfig.__name__,
    # ag_models.BugsExposedFeedbackLevel: ag_models.BugsExposedFeedbackLevel.__name__,
    # ag_models.MutationTestSuiteResult.FeedbackCalculator: 'MutationTestSuiteResultFeedback',

    ag_models.RerunSubmissionsTask: 'Create' + ag_models.RerunSubmissionsTask.__name__,

    hg_models.HandgradingRubric: 'Create' + hg_models.HandgradingRubric.__name__,
    # hg_models.PointsStyle: hg_models.PointsStyle.__name__,
    hg_models.Criterion: 'Create' + hg_models.Criterion.__name__,
    hg_models.Annotation: 'Create' + hg_models.Annotation.__name__,
    hg_models.HandgradingResult: 'Create' + hg_models.HandgradingResult.__name__,
    # hg_models.CriterionResult: 'Create' + hg_models.CriterionResult.__name__,
    hg_models.AppliedAnnotation: 'Create' + hg_models.AppliedAnnotation.__name__,
    hg_models.Comment: 'Create' + hg_models.Comment.__name__,
    # hg_models.Location: hg_models.Location.__name__,
}

_API_UPDATE_OBJ_TYPE_NAMES: Dict[APIClassType, str] = {
    # User: 'User',
    ag_models.Course: 'Update' + ag_models.Course.__name__,
    # ag_models.Semester: ag_models.Semester.__name__,
    ag_models.Project: 'Update' + ag_models.Project.__name__,
    # ag_models.UltimateSubmissionPolicy: ag_models.UltimateSubmissionPolicy.__name__,
    ag_models.ExpectedStudentFile: 'Update' + ag_models.ExpectedStudentFile.__name__,
    # ag_models.InstructorFile: 'Update' + ag_models.InstructorFile.__name__,
    ag_models.DownloadTask: 'Update' + ag_models.DownloadTask.__name__,
    # ag_models.DownloadType: ag_models.DownloadType.__name__,
    # ag_models.Group: 'Update' + ag_models.Group.__name__,
    # ag_models.GroupInvitation: 'Update' + ag_models.GroupInvitation.__name__,
    # ag_models.Submission: 'Update' + ag_models.Submission.__name__,

    # ag_models.Command: ag_models.Command.__name__,

    ag_models.SandboxDockerImage: 'Update' + ag_models.SandboxDockerImage.__name__,
    # ag_models.BuildSandboxDockerImageTask: 'Update' + ag_models.BuildSandboxDockerImageTask.__name__,
    # ag_models.BuildImageStatus: ag_models.BuildImageStatus.__name__,
    ag_models.AGTestSuite: 'Update' + ag_models.AGTestSuite.__name__,
    # ag_models.AGTestSuiteFeedbackConfig: 'AGTestSuiteFeedbackConfig',
    ag_models.AGTestCase: 'Update' + ag_models.AGTestCase.__name__,
    # ag_models.AGTestCaseFeedbackConfig: 'AGTestCaseFeedbackConfig',
    ag_models.AGTestCommand: 'Update' + ag_models.AGTestCommand.__name__,
    # ag_models.AGTestCommandFeedbackConfig: 'AGTestCommandFeedbackConfig',

    # ag_models.StdinSource: ag_models.StdinSource.__name__,
    # ag_models.ExpectedOutputSource: ag_models.ExpectedOutputSource.__name__,
    # ag_models.ExpectedReturnCode: ag_models.ExpectedReturnCode.__name__,
    # ag_models.ValueFeedbackLevel: ag_models.ValueFeedbackLevel.__name__,

    # SubmissionResultFeedback: SubmissionResultFeedback.__name__,
    # AGTestSuiteResultFeedback: AGTestSuiteResultFeedback.__name__,
    # AGTestCaseResultFeedback: AGTestCaseResultFeedback.__name__,
    # AGTestCommandResultFeedback: AGTestCommandResultFeedback.__name__,
    # ag_models.FeedbackCategory: ag_models.FeedbackCategory.__name__,

    ag_models.MutationTestSuite: 'Update' + ag_models.MutationTestSuite.__name__,
    # ag_models.MutationTestSuiteFeedbackConfig: ag_models.MutationTestSuiteFeedbackConfig.__name__,
    # ag_models.BugsExposedFeedbackLevel: ag_models.BugsExposedFeedbackLevel.__name__,
    # ag_models.MutationTestSuiteResult.FeedbackCalculator: 'MutationTestSuiteResultFeedback',

    # ag_models.RerunSubmissionsTask: 'Update' + ag_models.RerunSubmissionsTask.__name__,

    hg_models.HandgradingRubric: 'Update' + hg_models.HandgradingRubric.__name__,
    # hg_models.PointsStyle: hg_models.PointsStyle.__name__,
    hg_models.Criterion: 'Update' + hg_models.Criterion.__name__,
    hg_models.Annotation: 'Update' + hg_models.Annotation.__name__,
    hg_models.HandgradingResult: 'Update' + hg_models.HandgradingResult.__name__,
    hg_models.CriterionResult: 'Update' + hg_models.CriterionResult.__name__,
    # hg_models.AppliedAnnotation: 'Update' + hg_models.AppliedAnnotation.__name__,
    # hg_models.Comment: 'Update' + hg_models.Comment.__name__,
    # hg_models.Location: hg_models.Location.__name__,
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

    def generate_create_model_schema(self) -> SchemaObject | None:
        return None

    def generate_update_model_schema(self) -> SchemaObject | None:
        return None

    # Generate a version of the schema for this class that includes
    # only the fields that are allowed in create (POST) and update (PATCH)
    # requests.
    def generate_request_body_schema(
        self, *, include_required: bool
    ) -> Optional[SchemaObject]:
        return None

    def _field_names(self) -> Sequence[str]:
        return []

    def _editable_field_names(self) -> Sequence[str]:
        return []


HasToDictMixinType = TypeVar('HasToDictMixinType', bound=Type[ToDictMixin])


class HasToDictMixinSchemaGenerator(APIClassSchemaGenerator):
    _class: Type[ToDictMixin]

    def generate(self) -> SchemaObject:
        result = super().generate()
        return (
            super().generate()
            | {
                'required': self._get_required_field_names()
            }
        )

    def __init__(self, class_: Type[ToDictMixin]):
        self._class = class_

    def _field_names(self) -> Sequence[str]:
        return self._class.get_serializable_fields()

    def _get_required_field_names(self) -> list[str]:
        if self._class in self._required_field_names_override:
            return self._required_field_names_override[self._class]

        return list(self._field_names())

    _required_field_names_override: Dict[Type[ToDictMixin], list[str]] = {
        SubmissionResultFeedback: [
            'pk',
            'total_points',
            'total_points_possible',
        ]
    }

class AGModelSchemaGenerator(HasToDictMixinSchemaGenerator):
    _class: Type[AutograderModel]

    def __init__(self, class_: Type[AutograderModel]):
        self._class = class_

    def _get_required_field_names(self) -> list[str]:
        return [
            field for field in self._field_names()
            if self._field_is_required_on_get(field)
        ]

    def generate_create_model_schema(self) -> SchemaObject | None:
        result: SchemaObject = {
            'type': 'object',
            'properties': {
                name: _get_field_schema(
                    _extract_field(name, self._class),
                    self._class,
                    name,
                )
                for name in self._settable_on_create_fields_names()
            },
            'required': self._get_required_on_create_fields()
        }
        return result


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
                )
                for name in self._editable_field_names()
            }
        }
        if include_required:
            result['required'] = self._get_required_on_create_fields()
        return result

    def _editable_field_names(self) -> Sequence[str]:
        return self._class.get_editable_fields()

    def _settable_on_create_fields_names(self) -> list[str]:
        if self._class in self._settable_on_create_field_names_override:
            return self._settable_on_create_field_names_override[self._class]

        return self._editable_field_names()

    _settable_on_create_field_names_override: Dict[APIClassType, list[str]] = {
        ag_models.RerunSubmissionsTask: [
            'rerun_all_submissions',
            'submission_pks',
            'rerun_all_ag_test_suites',
            'ag_test_suite_data',
            'rerun_all_mutation_test_suites',
            'mutation_suite_pks',
        ],
        hg_models.AppliedAnnotation: [
            'annotation',
            'location',
        ]
    }

    def _get_required_on_create_fields(self) -> List[str]:
        if self._class in self._required_on_create_field_names_override:
            return self._required_on_create_field_names_override[self._class]

        return [
            field_name for field_name in self._class.get_serializable_fields()
            if self._field_is_required_on_create(field_name)
        ]

    _required_on_create_field_names_override: Dict[APIClassType, list[str]] = {
        ag_models.AGTestCase: [
            'name',
        ],
        hg_models.AppliedAnnotation: [
            'annotation',
            'location',
        ],
    }

    # Returns true if the specified field will always be present in
    # a GET request context.
    def _field_is_required_on_get(self, field_name: str) -> bool:
        override = _PROP_FIELD_IS_REQUIRED_OVERRIDES.get(self._class, {}).get(field_name, None)
        if override is not None:
            return override

        return True

    def _field_is_required_on_create(self, field_name: str) -> bool:
        override = _PROP_FIELD_IS_REQUIRED_OVERRIDES.get(self._class, {}).get(field_name, None)
        if override is not None:
            return override

        try:
            field = self._class._meta.get_field(field_name)
            return (
                # Remove this cast once django-stubs fixes:
                # https://github.com/typeddjango/django-stubs/issues/447
                not cast('RelatedField[object, object]', field).many_to_many
                and not cast('RelatedField[object, object]', field).is_relation
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
            },
            'required': self._get_required_field_names()
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

        result['required'] = list(self._fields)
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
) -> SchemaObject:
    return {'type': 'unknown'}


@_get_field_schema.register(ForeignObjectRel)
@_get_field_schema.register(Field)
def _django_field(
    field: Field[object, object],
    api_class: Type[AutograderModel],
    name: str,
) -> SchemaObject:
    result: SchemaObject = {
        # str() is used to force processing of django lazy eval
        'description': str(field.help_text).strip() if hasattr(field, 'help_text') else '',
        'nullable': field.null,
    }

    # In Django 2, choices is an empty list by default. In Django 3,
    # choices is None by default.
    if hasattr(field, 'choices') and field.choices:
        result['enum'] = [str(choice[0]) for choice in field.choices]

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

    models.JSONField: {'type': 'object'},
    pg_fields.JSONField: {'type': 'object'},
}


@_get_field_schema.register
def _property(
    prop: property,
    api_class: APIClassType,
    name: str,
) -> SchemaObject:
    if name == 'pk':
        return _PK_SCHEMA

    result: SchemaObject = {
        'description': _get_prop_description(prop),
    }
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
) -> SchemaObject:
    if name == 'pk':
        return _PK_SCHEMA

    result: SchemaObject = {
        'description': _get_prop_description(prop),
    }
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
}

_PROP_FIELD_IS_REQUIRED_OVERRIDES: Dict[APIClassType, Dict[str, bool]] = {
    ag_models.Group: {
        'member_names': True
    },
    ag_models.Project: {
        'closing_time': False
    }
}

_CREATE_BODY_OVERRIDES: Dict[APIClassType, SchemaObject] = {
    ag_models.InstructorFile: {
        'type': 'object',
        'properties': {
            'file_obj': {
                'type': 'string',
                'format': 'binary',
                'description': 'The form-encoded file.'
            }
        }
    },

    ag_models.Group: {
        'type': 'object',
        'properties': {
            'member_names': {
                'type': 'array',
                'items': {
                    'type': 'string',
                    'format': 'username',
                }
            }
        },
        'required': [
            'member_names',
        ]
    },

    ag_models.GroupInvitation: {
        'type': 'object',
        'properties': {
            'recipients': {
                'type': 'array',
                'items': {
                    'type': 'string',
                    'format': 'username',
                }
            }
        },
        'required': [
            'recipients',
        ]
    },

    ag_models.Submission: {
        'type': 'object',
        'properties': {
            'submitted_files': {
                'type': 'array',
                'items': {
                    'type': 'string',
                    'format': 'binary',
                },
                'description': 'A list of form-encoded files to submit.'
            }
        },
        'required': [
            'submitted_files',
        ]
    },

    ag_models.BuildSandboxDockerImageTask: {
        'type': 'object',
        'properties': {
            'files': {
                'description': (
                    'The form-encoded files. One file must be named "Dockerfile"'),
                'type': 'array',
                'items': {
                    'type': 'string',
                    'format': 'binary',
                },
            }
        }
    },

    # FIXME: applied annotation (request body and create model)
    ag_models.DownloadTask: None,
}

# FIXME: required fields on result fdbk objects

_UPDATE_BODY_OVERRIDES: Dict[APIClassType, SchemaObject] = {
    # FIXME: instructor file
    ag_models.DownloadTask: None,
}


_PK_SCHEMA: SchemaObject = {
    'type': 'integer',
}


_PK_SCHEMA_READ_ONLY: SchemaObject = {
    'type': 'integer',
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

    if origin is dict:
        return {'type': 'object'}

    if type_ in _API_OBJ_TYPE_NAMES:
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
    return {'$ref': f'#/components/schemas/{_API_OBJ_TYPE_NAMES[type_]}'}


def as_create_schema_ref(type_: APIClassType) -> ReferenceObject:
    return {'$ref': f'#/components/schemas/{_API_CREATE_OBJ_TYPE_NAMES[type_]}'}


_NonRefType = TypeVar('_NonRefType', bound=Mapping[str, object])


def assert_not_ref(obj: OrRef[_NonRefType]) -> _NonRefType:
    assert '$ref' not in obj, obj
    return obj
