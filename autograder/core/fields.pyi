from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Generic, Optional, Type, TypeVar, Union, overload

from django.contrib.postgres import fields as pg_fields
from django.db.models.base import Model
from django.db.models.fields.json import JSONField

from . import constants as const

if TYPE_CHECKING:
    from .models.ag_model_base import DictSerializable


_JSONObjType = TypeVar('_JSONObjType', bound='DictSerializable')


class ValidatedJSONField(Generic[_JSONObjType], JSONField):
    def __set__(self, instance: Model, value: Union[_JSONObjType, Dict[str, object]]) -> None:
        ...

    # class access
    @overload
    def __get__(
        self: ValidatedJSONField[_JSONObjType],
        instance: None,
        owner: Type[Model]
    ) -> ValidatedJSONField[_JSONObjType]:
        ...

    # Model instance access
    @overload
    def __get__(self, instance: Model, owner: Type[Model]) -> _JSONObjType:
        ...

    # non-Model instances
    @overload
    def __get__(
        self: ValidatedJSONField[_JSONObjType],
        instance: object,
        owner: type
    ) -> ValidatedJSONField[_JSONObjType]:
        ...

    def __init__(self, serializable_class: Type[_JSONObjType], **kwargs: Any):
        ...

    def validate(self, value: Optional[_JSONObjType], model_instance: Model) -> None:
        ...
