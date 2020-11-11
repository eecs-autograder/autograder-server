from enum import Enum
from typing import (
    TYPE_CHECKING, Any, Callable, Dict, Generic, List, Optional, Tuple, Type, TypeVar, Union
)

from django.contrib.postgres import fields as pg_fields
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.base import Model

from . import constants as const

if TYPE_CHECKING:
    from .models.ag_model_base import DictSerializable


# DEPRECATED: DO NOT USE
# TODO: Remove in 5.0.0
class ValidatedArrayField(pg_fields.ArrayField):  # type: ignore
    """
    This field provides the same functionality as the postgres
    ArrayField but with a more convenient validation process. When
    evaluating the individual elements of the array, a list of error
    messages is constructed that has a one-to-one correspondence with
    the elements of the array. For example, if we're storing an array of
    positive numbers, but the user provides [1, 2, -5, 4], the
    corresponding list of error messages would contain ['', '', 'Error:
    negative number', '']. The empty strings indicate no error for the
    elements 1, 2, and 4, and the non-empty string indicates the error
    caused by the -5 element. This list is then thrown as part of a
    ValidationError.
    """

    def clean(self, value: Any, model_instance: Optional[models.Model]) -> Any:
        value = super().clean(value, model_instance)

        cleaned_value = []
        errors: List[Union[str, List[str]]] = []
        error_found = False
        for item in value:
            try:
                item = self.base_field.clean(item, model_instance)
                errors.append('')
            except ValidationError as e:
                errors.append(e.messages)
                error_found = True
            finally:
                cleaned_value.append(item)

        if error_found:
            raise ValidationError(errors)

        return value

    def validate(self, value: Any, model_instance: models.Model) -> None:
        # The validate() function defined in ArrayField has the
        # behavior we want to get rid of, so we instead call
        # validate() on ArrayField's base class.
        super(pg_fields.ArrayField, self).validate(value, model_instance)

    def run_validators(self, value: Any) -> None:
        # The run_validators() function defined in ArrayField has the
        # behavior we want to get rid of, so we instead call
        # run_validators() on ArrayField's base class.
        super(pg_fields.ArrayField, self).run_validators(value)


_ValidatorCallable = Callable[..., None]


# DEPRECATED: DO NOT USE
class StringArrayField(ValidatedArrayField):
    """
    A convenience wrapper around ValidatedArrayField that always
    stores a list of strings.

    Additional options:
        strip_strings -- When true, leading and trailing whitespace is
            stripped from the items in the array.
            Default value: False
        allow_empty_strings -- Whether the underlying CharField should
            allow empty strings.
            Default value: False
        string_validators -- A list of Validators to be run on
            each element in the array.
        max_string_length -- The maximum length of strings stored
            in the array.
            Default value: (autograder.shared.
                                global_constants.MAX_CHAR_FIELD_LEN)
    """

    def __init__(
        self,
        strip_strings: bool = False,
        allow_empty_strings: bool = False,
        string_validators: Optional[List[_ValidatorCallable]] = None,
        max_string_length: int = const.MAX_CHAR_FIELD_LEN,
        **kwargs: Any
    ):
        if string_validators is None:
            string_validators = []

        self.strip_strings = strip_strings
        self.allow_empty_strings = allow_empty_strings
        self.max_string_length = max_string_length
        self.string_validators = string_validators

        super().__init__(
            models.CharField(
                max_length=max_string_length, blank=allow_empty_strings,
                validators=string_validators
            ),
            **kwargs
        )

    def deconstruct(self) -> Any:
        name, path, args, kwargs = super().deconstruct()
        del kwargs['base_field']
        kwargs.update({
            'strip_strings': self.strip_strings,
            'allow_empty_strings': self.allow_empty_strings,
            'max_string_length': self.max_string_length,
            'string_validators': self.string_validators
        })
        return name, path, args, kwargs

    def to_python(self, value: Any) -> Any:
        value = super().to_python(value)
        if value is None:
            return value

        if not self.strip_strings:
            return value

        stripped = [item.strip() if item is not None else item
                    for item in value]

        return stripped

    def from_db_value(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        return self.to_python(value)


# DEPRECATED: DO NOT USE
class ShortStringField(models.CharField):  # type: ignore
    def __init__(
        self,
        max_length: int = const.MAX_CHAR_FIELD_LEN,
        strip: bool = False,
        **kwargs: Any
    ):
        self.strip = strip
        super().__init__(max_length=max_length, **kwargs)

    def deconstruct(self) -> Any:
        name, path, args, kwargs = super().deconstruct()
        kwargs['strip'] = self.strip
        return name, path, args, kwargs

    def to_python(self, value: Any) -> Any:
        if value is not None:
            value = value.strip()

        return super().to_python(value)

    def from_db_value(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        return self.to_python(value)


_EnumType = TypeVar('_EnumType', bound=Enum)


# Use Django 3.1 TextChoices and TextField instead of this field.
# DEPRECATED: DO NOT USE
class EnumField(
    Generic[_EnumType],
    models.TextField  # type: ignore # see https://github.com/typeddjango/django-stubs/issues/285
):
    def __init__(self, enum_type: Type[_EnumType], **kwargs: Any):
        self.enum_type = enum_type
        super().__init__(**kwargs)

    def deconstruct(self) -> Tuple[Any, Any, Any, Any]:
        name, path, args, kwargs = super().deconstruct()
        kwargs['enum_type'] = self.enum_type
        return name, path, args, kwargs

    def to_python(self, value: Any) -> Optional[_EnumType]:
        if value is None:
            return None

        try:
            return self.enum_type(value)
        except ValueError:
            raise ValidationError(
                '"{}" is not a valid {}'.format(value, self.enum_type.__name__))

    def from_db_value(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        return self.to_python(value)

    def get_prep_value(self, value: Any) -> Any:
        if value is None:
            return None

        return value.value


_JSONObjType = TypeVar('_JSONObjType', bound='DictSerializable')


# django-stubs type stubs for JSONField are incomplete.
# Once they are fully-implemented, try to remove the type: ignore
# comments.
class ValidatedJSONField(Generic[_JSONObjType], pg_fields.JSONField):
    """
    This field uses the Postgres JSON field, ToDictMixin, and
    FromDictMixin to validate and store serializable Python objects
    in the database.
    """

    def __init__(self, serializable_class: Type[_JSONObjType], **kwargs: Any):
        self.serializable_class = serializable_class
        super().__init__(**kwargs)

    def deconstruct(self) -> Tuple[Any, Any, Any, Any]:
        name, path, args, kwargs = super().deconstruct()
        kwargs['serializable_class'] = self.serializable_class
        return name, path, args, kwargs

    def to_python(self, value: Any) -> Optional[_JSONObjType]:
        if value is None:
            return None

        if isinstance(value, self.serializable_class):
            return self.serializable_class.from_dict(value.to_dict())

        return self.serializable_class.from_dict(value)

    def validate(self, value: Optional[_JSONObjType], model_instance: Model) -> None:
        if value is None:
            super().validate(value, model_instance)
        else:
            super().validate(value.to_dict(), model_instance)

    def from_db_value(self, value: Any, *args: Any, **kwargs: Any) -> Optional[_JSONObjType]:
        return self.to_python(
            super().from_db_value(value, *args, **kwargs)  # type: ignore
        )

    def get_prep_value(
        self,
        value: Union[Dict[str, object], _JSONObjType, None]
    ) -> Any:
        if value is None:
            return None

        if isinstance(value, dict):
            return super().get_prep_value(value)

        return super().get_prep_value(value.to_dict())
