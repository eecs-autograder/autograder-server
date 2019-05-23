import copy
import decimal
import enum
import inspect
import typing
from collections import OrderedDict

from django.db import models, transaction
from django.core import exceptions
from drf_yasg.openapi import Schema, Parameter

from autograder.core.fields import ValidatedJSONField


class AutograderModelManager(models.Manager):
    """
    The default manager for autograder model classes.
    Its main purpose is to provide the validate_and_create method.
    """
    def validate_and_create(self, **kwargs) -> 'AutograderModel':
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
            if not instance._meta.get_field(field_name).many_to_many:
                continue

            objs = kwargs.pop(field_name)
            if not objs:
                continue

            related_model = instance._meta.get_field(field_name).related_model
            many_to_many_to_set[field_name] = _load_related_to_many_objs(related_model, objs)

        with transaction.atomic():
            for field_name, value in kwargs.items():
                if field_name in instance.get_transparent_to_one_fields():
                    related_model = instance._meta.get_field(field_name).related_model
                    setattr(instance, field_name,
                            related_model.objects.validate_and_create(**value))
                elif _field_is_to_one(instance, field_name):
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


def _field_is_to_one(instance: 'AutograderModel', field_name: str):
    field = instance._meta.get_field(field_name)
    return field.many_to_one or field.one_to_one


def _load_related_to_many_objs(related_model, objs: typing.Sequence):
    if not objs:
        return []

    if isinstance(objs[0], related_model):
        return objs
    elif isinstance(objs[0], int):
        return list(related_model.objects.filter(pk__in=objs))
    elif isinstance(objs[0], dict):
        return list(related_model.objects.filter(pk__in=[obj['pk'] for obj in objs]))
    else:
        raise ValueError(
            'Invalid type for related objects. '
            'Expected {}, dict, or int, but was {}'.format(str(related_model),
                                                           type(objs[0])))


class ToDictMixin:
    @classmethod
    def get_serializable_fields(cls) -> typing.Tuple[str]:
        """
        Returns a tuple of the names of member variables to include
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
        cls.SERIALIZABLE_FIELDS, which defaults to an empty tuple.
        """
        return cls.SERIALIZABLE_FIELDS

    SERIALIZABLE_FIELDS = tuple()

    @classmethod
    def get_serialize_related_fields(cls) -> typing.Tuple[str]:
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

    SERIALIZE_RELATED = tuple()

    @classmethod
    def get_transparent_to_one_fields(cls) -> typing.Tuple[str]:
        """
        Returns a tuple of the names of database -to-one fields
        that should be treated as "transparent" when serializing and
        updating instances of this class.
        This introduces the following default behaviors for affected fields:
        - The related object will be serialized using its to_dict() method.
        - When the field is being set, either in validate_and_create or
          validate_and_update, the parameter value for the field MUST
          be a dictionary. In the case of validate_and_create, a new
          related object will be created using the dictionary contents
          as keyword arguments. In the case of validate_and_update,
          the dictionary contents will be unpacked and passed to the
          related object's validate_and_update method. If the related
          object is None, then a new related object will be created
          similarly to in validate_and_create.
          If the related object is being set to None in validate_and_update,
          the current related object will be deleted. Keep this in mind
          especially if those objects have children that could be
          cascade-deleted because of this.

        Marking a -to-one relationship as transparent effectively makes it
        behave like a normal member of the class rather than a database relationship.

        The base class version of this function returns the value of
        cls.TRANSPARENT_TO_ONE_FIELDS, which defaults to an empty tuple.
        """
        return cls.TRANSPARENT_TO_ONE_FIELDS

    TRANSPARENT_TO_ONE_FIELDS = tuple()

    def to_dict(self) -> dict:
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
                field = self._meta.get_field(field_name)

                if isinstance(field, ValidatedJSONField):
                    value = getattr(self, field_name)

                    result[field_name] = value.to_dict() if value is not None else None
                    continue

                if field.many_to_one or field.one_to_one:
                    field_val = getattr(self, field_name)
                    if field_val is None:
                        continue

                    if (field_name in self.get_serialize_related_fields()
                            or field_name in self.get_transparent_to_one_fields()):
                        result[field_name] = field_val.to_dict()
                    else:
                        if isinstance(field_val, int):  # serializing an '_id' field
                            result[field_name] = field_val
                        else:
                            result[field_name] = field_val.pk
                elif field.many_to_many or field.one_to_many:
                    if field_name in self.get_serialize_related_fields():
                        result[field_name] = [
                            obj.to_dict() for obj in getattr(self, field_name).all()]
                    else:
                        result[field_name] = [obj.pk for obj in getattr(self, field_name).all()]
            except exceptions.FieldDoesNotExist:
                pass

        return result


class DictSerializableMixin(ToDictMixin):
    """
    In addition to the functionality provided by ToDictMixin,
    provides a way to validate data and construct or update
    objects from the validated data.

    Also provides a way of generating a Schema for the class.

    Note: This mixin should NOT be used with Django model classes.
    """

    @classmethod
    def from_dict(cls, input_: dict):
        """
        Validates input_ and constructs an object from it.
        To add custom validation, override the validate() method.
        """
        cls._check_for_missing_fields(input_)
        return cls(**cls.prepare_input(input_))

    def update(self, input_):
        """
        Validates input_ and updates the current object from it.
        To add custom validation, override the validate() method.
        """
        prepared_input = self.prepare_input(input_)
        for field_name, value in prepared_input.items():
            setattr(self, field_name, value)

    @classmethod
    def prepare_input(cls, input_: dict) -> dict:
        """
        Prepares input_ for constructing an instance of cls. If a string
        is given where an enum is expected, an object of the enum type
        will be created and used instead.

        Raises django.core.exceptions.ValidationError if input
        contains any fields not in cls.get_field_types(), or if any
        input values have the wrong type.
        """
        processed_input = copy.deepcopy(input_)

        extra_fields = set(input_.keys()) - cls._allowed_fields()
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
    def _check_for_missing_fields(cls, input_: dict):
        # Skip "self"
        ctor_fields = list(inspect.signature(cls.__init__).parameters.keys())[1:]
        for field_name in ctor_fields:
            if cls.field_is_required(field_name) and field_name not in input_:
                raise exceptions.ValidationError(
                    f'Missing required field: "{field_name}"'
                )

    @classmethod
    def _allowed_fields(cls) -> typing.Set[str]:
        return set(inspect.signature(cls.__init__).parameters.keys())

    @classmethod
    def get_field_type(cls, field_name: str) -> typing.Type:
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

        return param.annotation

    @classmethod
    def field_is_required(cls, field_name: str) -> bool:
        """
        Returns True if the parameter to the __init__ method called
        field_name has no default value (if it's a required parameter).
        """
        return cls.get_field_default(field_name) is inspect.Parameter.empty

    @classmethod
    def get_field_default(cls, field_name):
        """
        Returns the default value for the field with the given name.
        The default value is introspected from the parameter of the
        same name in the __init__ method.
        """
        default = inspect.signature(cls.__init__).parameters[field_name].default
        return default.value if isinstance(default, enum.Enum) else default

    @classmethod
    def get_field_descriptions(cls):
        return cls.FIELD_DESCRIPTIONS

    # A dictionary of field names to field descriptions.
    FIELD_DESCRIPTIONS: typing.Dict[str, str] = {}

    @classmethod
    def run_field_validators(cls, input_: dict):
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
    FIELD_VALIDATORS: typing.Dict[str, typing.List[typing.Callable[[object], None]]] = {}

    @classmethod
    def get_schema(cls, title) -> Schema:
        """
        Returns a schema for this class to be used in generating API
        documentation.
        """
        properties = OrderedDict()
        for field_name in cls.get_serializable_fields():
            properties[field_name] = Parameter(
                field_name, 'body',
                description=cls.get_field_descriptions().get(field_name, ''),
                type=cls.get_field_type(field_name).__name__,
                required=cls.field_is_required(field_name),
                default=cls.get_field_default(field_name)
            )
        return Schema(
            title=title,
            type='object',
            properties=properties
        )


class AutograderModel(ToDictMixin, models.Model):
    """
    The base class for non-polymorphic autograder model classes. This
    class sets an AutograderModelManager as the default manager and
    provides a last_modified field and a validate_and_update method.
    """
    class Meta:
        abstract = True

    objects = AutograderModelManager()

    INVALID_FIELD_NAMES_KEY = 'invalid_field_names'

    last_modified = models.DateTimeField(auto_now=True)

    @classmethod
    def get_editable_fields(cls):
        """
        Returns a collection of the names of database fields that can be
        edited on this model type using model.validate_and_update()

        The base class version of this function returns the value of
        cls.EDITABLE_FIELDS, which defaults to an empty
        tuple. Thus, you can either set EDITABLE_FIELDS in
        derived classes or override this method.
        """
        return cls.EDITABLE_FIELDS

    EDITABLE_FIELDS = tuple()

    @transaction.atomic
    def validate_and_update(self, **kwargs):
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

            field = self._meta.get_field(field_name)

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
                loaded_vals = _load_related_to_many_objs(field.related_model, val)
                getattr(self, field_name).set(loaded_vals, clear=True)
            elif field_name in self.get_transparent_to_one_fields():
                if val is not None and not isinstance(val, dict):
                    raise ValueError(
                        'Expected a dictionary or None when updating the transparent '
                        '-to-one field {} on model object of type {}, but got {} instead.'.format(
                            field_name, self.__class__, type(val)))

                if getattr(self, field_name) is None:
                    if val is None:
                        pass
                    else:
                        setattr(self, field_name,
                                field.related_model.objects.validate_and_create(**val))
                else:
                    if val is None:
                        getattr(self, field_name).delete()
                        setattr(self, field_name, None)
                    else:
                        update_vals = {key: value for key, value in val.items()
                                       if key in field.related_model.get_editable_fields()}
                        getattr(self, field_name).validate_and_update(**update_vals)
            elif _field_is_to_one(self, field_name):
                _set_to_one_relationship(self, field_name, val)
            else:
                setattr(self, field_name, val)

        self.full_clean()
        self.save()

    def __str__(self):
        return '<{}: {}>'.format(self.__class__.__name__, self.pk)


def _set_to_one_relationship(model_obj, field_name, value):
    related_model = model_obj._meta.get_field(field_name).related_model

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
