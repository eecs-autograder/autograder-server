from __future__ import annotations

import copy
import decimal
import enum
import inspect
from typing import Callable, Dict, List, Mapping, Sequence, Type, TypedDict, TypeVar, Union, cast

from django.contrib.auth.models import User
from django.core import exceptions
from django.core.exceptions import FieldDoesNotExist
from django.db import models, transaction
from django.db.models import Model

from autograder.core.fields import ValidatedJSONField
from autograder.rest_api.serialize_user import serialize_user

_AutograderModelType = TypeVar('_AutograderModelType', bound='AutograderModel')


class AutograderModelManager(models.Manager[_AutograderModelType]):
    """
    The default manager for autograder model classes.
    Its main purpose is to provide the validate_and_create method.
    """
    def validate_and_create(self, **kwargs: object) -> _AutograderModelType:
        """
        This method is a shortcut for constructing a model object,
        calling full_clean(), and then calling save().
        Prefer using this method over <Model class>.objects.create().

        One-to-one relationships and foreign key relationships:
        If you wish to specify a value for a one-to-one or foreign key
        relationship, you may pass one of the following:
            - The related object itself
            - The related object's primary key
            - A dictonary with the related object's primary key stored
              under the 'pk' key.

        Many-to-many relationships:
        Similarly to -to-one relationships, you may pass a sequence of
        objects as the value for a many-to-many relationship. The
        objects of the sequence must be one of the following:
            - The related objects themselves
            - The related objects' primary keys
            - Dictonaries with the related objects' primary keys stored
              under the 'pk' key.
        The sequence must be homogenous (you cannot mix and match the types
        listed above.
        """
        instance = self.model()
        many_to_many_to_set = {}
        for field_name in list(kwargs.keys()):
            field = instance._meta.get_field(field_name)
            if not field.many_to_many:
                continue

            objs = cast(Sequence[object], kwargs.pop(field_name))
            if not objs:
                continue

            related_model = instance._meta.get_field(field_name).related_model
            assert related_model is not None
            many_to_many_to_set[field_name] = _load_related_to_many_objs(related_model, objs)

        with transaction.atomic():
            for field_name, value in kwargs.items():
                if _field_is_to_one(instance, field_name):
                    _set_to_one_relationship(instance, field_name, value)
                else:
                    field = instance._meta.get_field(field_name)
                    if (value is not None and isinstance(field, ValidatedJSONField)
                            and isinstance(value, dict)):
                        try:
                            setattr(instance, field_name,
                                    field.serializable_class.from_dict(value))
                        except exceptions.ValidationError as e:
                            raise exceptions.ValidationError({field_name: str(e)})
                    else:
                        setattr(instance, field_name, value)

            instance.full_clean()
            instance.save()

            for field_name, value in many_to_many_to_set.items():
                getattr(instance, field_name).set(value, clear=True)

            # This needs to be here in case the model's clean()
            # method does any validation on many-to-many relationships.
            instance.clean()

            return instance


def _field_is_to_one(instance: AutograderModel, field_name: str) -> bool:
    field = instance._meta.get_field(field_name)
    return bool(field.many_to_one) or bool(field.one_to_one)


class _HasPK(TypedDict):
    pk: int


def _load_related_to_many_objs(
    related_model: Type[Model],
    objs: Sequence[object]
) -> Sequence[Model]:
    if not objs:
        return []

    if isinstance(objs[0], related_model):
        return cast(Sequence[Model], objs)
    elif isinstance(objs[0], int):
        return list(related_model.objects.filter(pk__in=objs))
    elif isinstance(objs[0], dict):
        return list(
            related_model.objects.filter(
                pk__in=[obj['pk'] for obj in cast(Sequence[_HasPK], objs)]
            )
        )
    else:
        raise ValueError(
            'Invalid type for related objects. '
            'Expected {}, dict, or int, but was {}'.format(str(related_model),
                                                           type(objs[0])))


class ToDictMixin:
    @classmethod
    def get_serializable_fields(cls) -> Sequence[str]:
        """
        Returns a Sequence of the names of member variables to include
        by default in the dictionary returned by to_dict()

        This collection can include model fields, properties, member
        variables, "-to-one" relationships, and anything else for which
        getattr() returns the desired value.
        By default, "-to-one" relationships will be represented as the
        primary key of the related object.
        By default, "-to-many" relationships are represented as a list
        of model objects. These objects are serialized if they also have
        a "to_dict()" method.
        "-to-many" fields can only be serialized in instances of the
        model class they are defined in, not reverse-lookup
        relationships.

        By default, attributes that are subtypes of enum.Enum
        are serialized by accessing the .value attribute of the enum.

        The base class version of this function returns the value of
        cls.SERIALIZABLE_FIELDS, which defaults to an empty Sequence.
        """
        return cls.SERIALIZABLE_FIELDS

    SERIALIZABLE_FIELDS: Sequence[str] = tuple()

    @classmethod
    def get_serialize_related_fields(cls) -> Sequence[str]:
        """
        Returns a tuple of the names of database related fields
        (-to-one or -to-many) that should be serialized
        (by calling <related_obj>.to_dict()) when
        an instance of this class is serialized with <obj>.to_dict().
        This overrides the default behavior of representing related
        objects as only a primary key.

        IMPORTANT: Do not register a relationship and its reverse
        lookup in SERIALIZE_RELATED for their respective models,
        or you will get infinite recursion!

        The base class version of this function returns the value of
        cls.SERIALIZE_RELATED, which defaults to an empty tuple.
        """
        return cls.SERIALIZE_RELATED

    SERIALIZE_RELATED: Sequence[str] = tuple()

    def to_dict(self) -> Dict[str, object]:
        """
        Returns a dictionary representation of this model instance.
        """
        result = {}

        for field_name in self.get_serializable_fields():
            result[field_name] = getattr(self, field_name)

            if isinstance(result[field_name], enum.Enum):
                result[field_name] = result[field_name].value
                continue

            if isinstance(result[field_name], decimal.Decimal):
                # Note: We may want to make the precision customizable
                # in the future.
                quantized = result[field_name].quantize(decimal.Decimal('.01'))
                result[field_name] = str(quantized)
                continue

            # If this isn't a Django Model (or if it's None), skip the field logic
            if not hasattr(self, '_meta'):
                continue

            try:
                field = cast(Model, self)._meta.get_field(field_name)

                if isinstance(field, ValidatedJSONField):
                    value = getattr(self, field_name)

                    result[field_name] = value.to_dict() if value is not None else None
                    continue

                if field.many_to_one or field.one_to_one:
                    field_val = getattr(self, field_name)
                    if field_val is None:
                        continue

                    if field_name in self.get_serialize_related_fields():
                        result[field_name] = _serialize_model_obj(field_val)
                    else:
                        if isinstance(field_val, int):  # serializing an '_id' field
                            result[field_name] = field_val
                        else:
                            result[field_name] = field_val.pk
                elif field.many_to_many or field.one_to_many:
                    if field_name in self.get_serialize_related_fields():
                        result[field_name] = [
                            _serialize_model_obj(obj) for obj in getattr(self, field_name).all()
                        ]
                    else:
                        result[field_name] = [obj.pk for obj in getattr(self, field_name).all()]
            except exceptions.FieldDoesNotExist:
                pass

        return result


def _serialize_model_obj(obj: Union[ToDictMixin, User]) -> Dict[str, object]:
    if isinstance(obj, User):
        return serialize_user(obj)

    return obj.to_dict()


class DictSerializable(ToDictMixin):
    """
    In addition to the functionality provided by ToDictMixin,
    provides a way to validate data and construct or update
    objects from the validated data.

    To use, derive from this class and provide a constructor with type
    annotations and, where applicable, default values for the arguments.
    Input data will be automatically validated to check for input type
    correctness, extra fields, and missing required fields.

    Note: This mixin should NOT be used with Django model classes.
    """
    _DerivedType = TypeVar('_DerivedType', bound='DictSerializable')

    def __init__(self, **kwargs: object) -> None:
        raise NotImplementedError('Derived classes must provide their own constructor.')

    @classmethod
    def from_dict(cls: Type[_DerivedType], input_: Dict[str, object]) -> _DerivedType:
        """
        Validates input_ and constructs an object from it.
        To add custom validation, override the validate() method.

        Note that calling DictSerializable.from_dict(obj.to_dict())
        should return an equivalent object.
        """
        cls._check_for_missing_fields(input_)
        result = cls(**cls.prepare_input(input_))
        result.validate()
        return result

    @classmethod
    def get_serializable_fields(cls) -> Sequence[str]:
        """
        This override automatically detects fields to be serialized
        by taking their names from the constructor arguments.
        Override this method if you want to manually specify
        serializable fields. When doing so, make sure that
        DictSerializable.from_dict(obj.to_dict()) still produces a
        valid result.
        """
        return tuple(cls._allowed_fields())

    def update(self, input_: Dict[str, object]) -> None:
        """
        Validates input_ and updates the current object from it.
        To add custom validation, override the validate() method.
        """
        prepared_input = self.prepare_input(input_)

        original = self.to_dict()

        for field_name, value in prepared_input.items():
            setattr(self, field_name, value)

        try:
            self.validate()
        except Exception:
            self.update(original)
            raise

    def validate(self) -> None:
        """
        Override this method to perform validation that requires more
        than one field (e.g. if one field is supposed to be greater
        that another).

        Raises django.core.exceptions.ValidationError constructed with
        a string if any invalid data is detected.

        This method is called in DictSerializable.from_dict()
        before the new object is returned and in self.update() after
        updated fields are assigned. Note that this is done in a way
        that the updates will be undone if an exception is thrown.
        """
        pass

    @classmethod
    def prepare_input(cls, input_: Dict[str, object]) -> Dict[str, object]:
        """
        Prepares input_ for constructing an instance of cls. If a string
        is given where an enum is expected, an object of the enum type
        will be created and used instead.

        Raises django.core.exceptions.ValidationError if input
        contains any fields not in cls.get_field_types(), or if any
        input values have the wrong type.
        """
        processed_input = copy.deepcopy(input_)

        extra_fields = set(input_.keys()) - set(cls._allowed_fields())
        if extra_fields:
            raise exceptions.ValidationError(f'Extra fields: {",".join(extra_fields)}')

        for field_name, value in input_.items():
            expected_type = cls.get_field_type(field_name)
            if issubclass(expected_type, enum.Enum) and isinstance(value, str):
                try:
                    processed_input[field_name] = expected_type(value)
                except ValueError as e:
                    raise exceptions.ValidationError(f'{field_name}: {str(e)}')
            elif not isinstance(value, expected_type):
                raise exceptions.ValidationError(
                    f'{field_name}: Incorrect type. Expected {expected_type.__name__}, '
                    f'but got {type(value).__name__}')
            else:
                processed_input[field_name] = value

        cls.run_field_validators(processed_input)

        return processed_input

    @classmethod
    def _check_for_missing_fields(cls, input_: Dict[str, object]) -> None:
        ctor_fields = cls._allowed_fields()
        for field_name in ctor_fields:
            if cls.field_is_required(field_name) and field_name not in input_:
                raise exceptions.ValidationError(
                    f'Missing required field: "{field_name}"'
                )

    @classmethod
    def _allowed_fields(cls) -> List[str]:
        # Skip "self"
        return list(inspect.signature(cls.__init__).parameters.keys())[1:]

    @classmethod
    def get_field_type(cls, field_name: str) -> type:
        """
        Attempts to determine the type of the field with the given
        name by inspecting the type annotation of the parameter
        with the same name in the __init__  method.

        Raises ValueError if there is no type annotation for the
        parameter.
        """
        param = inspect.signature(cls.__init__).parameters[field_name]
        if param.annotation is inspect.Parameter.empty:
            raise ValueError(f'Missing type annotation for {field_name} in {cls.__name__}')

        return cast(type, param.annotation)

    @classmethod
    def field_is_required(cls, field_name: str) -> bool:
        """
        Returns True if the parameter to the __init__ method called
        field_name has no default value (if it's a required parameter).
        """
        return cls.get_field_default(field_name) is inspect.Parameter.empty

    @classmethod
    def get_field_default(cls, field_name: str) -> object:
        """
        Returns the default value for the field with the given name.
        The default value is introspected from the parameter of the
        same name in the __init__ method.
        """
        default = inspect.signature(cls.__init__).parameters[field_name].default
        return default.value if isinstance(default, enum.Enum) else default

    @classmethod
    def get_field_descriptions(cls) -> Mapping[str, str]:
        return cls.FIELD_DESCRIPTIONS

    # A dictionary of field names to field descriptions. Used for
    # generating the API schema.
    FIELD_DESCRIPTIONS: Mapping[str, str] = {}

    @classmethod
    def run_field_validators(cls, input_: Dict[str, object]) -> None:
        """
        Runs the validators defined in cls.FIELD_VALIDATORS on input_.
        Re-raises the first caught ValidationError with the field name
        added to the error message.

        This function is run at the end of prepare_input.
        """
        for field_name, value in input_.items():
            for validator in cls.FIELD_VALIDATORS.get(field_name, []):
                try:
                    validator(input_[field_name])
                except exceptions.ValidationError as e:
                    raise exceptions.ValidationError(f'Error in "{field_name}": ' + e.message)

    # Validator functions should take in one argument and raise
    # django.core.exceptions.ValidationError constructed with a
    # string if the argument is invalid.
    FIELD_VALIDATORS: Dict[str, List[_FieldValidatorFunc]] = {}


_FieldValidatorFunc = Callable[[object], None]


def make_min_value_validator(min_value: int) -> _FieldValidatorFunc:
    def validator(value: object) -> None:
        if not isinstance(value, int):
            raise exceptions.ValidationError(f'Expected int but got type {type(value).__name__}')
        if value < min_value:
            raise exceptions.ValidationError(f'Must be >= {min_value}')

    return validator


def make_max_value_validator(max_value: int) -> _FieldValidatorFunc:
    def validator(value: object) -> None:
        if not isinstance(value, int):
            raise exceptions.ValidationError(f'Expected int but got type {type(value).__name__}')
        if value > max_value:
            raise exceptions.ValidationError(f'Must be <= {max_value}')

    return validator


def non_empty_str_validator(string: object) -> None:
    if not isinstance(string, str):
        raise exceptions.ValidationError(f'Expected str but got type {type(string).__name__}')
    if len(string) == 0:
        raise exceptions.ValidationError(f'Must not be empty')


class AutograderModel(ToDictMixin, models.Model):
    """
    The base class for non-polymorphic autograder model classes.
    Provides a last_modified field and a validate_and_update method.

    Derived classes should set an AutograderModelManager as the
    default manager. For example, if the model class name is Course,
    that class should include the line:
        objects = AutograderModelManager['Course']()
    This will ensure that the validate_and_create method is properly
    type-checked.
    """
    class Meta:
        abstract = True

    INVALID_FIELD_NAMES_KEY = 'invalid_field_names'

    last_modified = models.DateTimeField(auto_now=True)

    @classmethod
    def get_editable_fields(cls) -> Sequence[str]:
        """
        Returns a sequence of the names of database fields that can be
        edited on this model type using model.validate_and_update()

        The base class version of this function returns the value of
        cls.EDITABLE_FIELDS, which defaults to an empty
        tuple. Thus, you can either set EDITABLE_FIELDS in
        derived classes or override this method.
        """
        return cls.EDITABLE_FIELDS

    EDITABLE_FIELDS: Sequence[str] = tuple()

    @transaction.atomic
    def validate_and_update(self, **kwargs: object) -> None:
        """
        Updates the values of the fields specified as
        keyword arguments, runs model validation, and saves the
        model.

        One-to-one relationships and foreign key relationships:
        If you wish to specify a value for a one-to-one or foreign key
        relationship, you may pass one of the following:
            - The related object itself
            - The related object's primary key
            - A dictonary with the related object's primary key stored
              under the 'pk' key.

        Many-to-many relationships:
        Similarly to -to-one relationships, you may pass a sequence of
        objects as the value for a many-to-many relationship. The
        objects of the sequence must be one of the following:
            - The related objects themselves
            - The related objects' primary keys
            - Dictonaries with the related objects' primary keys stored
              under the 'pk' key.
        The sequence must be homogenous (you cannot mix and match the types
        listed above.

        Prefer using this method over setting values manually
        and calling full_clean() because this method can be overridden to
        perform extra validation that depends on the old and new values of
        fields.
        Raises ValidationError if any specified field doesn't exist or
        is not editable.
        """
        for field_name, val in kwargs.items():
            if not hasattr(self, field_name):
                raise exceptions.ValidationError(
                    {AutograderModel.INVALID_FIELD_NAMES_KEY: [field_name]})

            if field_name not in self.get_editable_fields():
                raise exceptions.ValidationError(
                    {'non_editable_fields': [field_name]})

            try:
                field = self._meta.get_field(field_name)
            except FieldDoesNotExist:
                # The field is most likely a property setter.
                setattr(self, field_name, val)
                continue

            if isinstance(field, ValidatedJSONField):
                if isinstance(val, dict):
                    try:
                        if getattr(self, field_name) is None:
                            setattr(self, field_name, field.serializable_class.from_dict(val))
                        else:
                            getattr(self, field_name).update(val)
                    except exceptions.ValidationError as e:
                        raise exceptions.ValidationError({field_name: str(e)})
                else:
                    setattr(self, field_name, val)

                continue

            if field.many_to_many:
                assert field.related_model is not None
                loaded_vals = _load_related_to_many_objs(
                    field.related_model, cast(Sequence[object], val))
                getattr(self, field_name).set(loaded_vals, clear=True)
            elif _field_is_to_one(self, field_name):
                _set_to_one_relationship(self, field_name, val)
            else:
                setattr(self, field_name, val)

        self.full_clean()
        self.save()

    def __str__(self) -> str:
        return '<{}: {}>'.format(self.__class__.__name__, self.pk)


def _set_to_one_relationship(
    model_obj: _AutograderModelType,
    field_name: str,
    value: object
) -> None:
    related_model = model_obj._meta.get_field(field_name).related_model
    assert related_model is not None

    if value is None:
        related_obj = None
    elif isinstance(value, related_model):
        related_obj = value
    elif isinstance(value, int):
        related_obj = related_model.objects.get(pk=value)
    elif isinstance(value, dict):
        related_obj = related_model.objects.get(pk=value['pk'])
    else:
        raise ValueError('-to-one related objects must be represented as int, '
                         'dict, or the object itself')

    setattr(model_obj, field_name, related_obj)
