import enum
import typing

from django.db import models, transaction
from django.core import exceptions


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

            # If this isn't a Django Model (or if it's None), skip the field logic
            if not hasattr(self, '_meta'):
                continue

            try:
                # noinspection PyUnresolvedReferences
                field = self._meta.get_field(field_name)

                if field.many_to_one or field.one_to_one:
                    field_val = getattr(self, field_name)
                    if field_val is None:
                        continue

                    if (field_name in self.get_serialize_related_fields()
                            or field_name in self.get_transparent_to_one_fields()):
                        result[field_name] = field_val.to_dict()
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
