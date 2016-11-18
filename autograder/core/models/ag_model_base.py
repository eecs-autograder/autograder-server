from django.db import models, transaction
from django.core import exceptions

import polymorphic.models as poly_models


class _AutograderModelManagerMixin:
    def validate_and_create(self, **kwargs):
        """
        This method is a shortcut for constructing a model object,
        calling full_clean(), and then calling save().
        Prefer using this method over <Model class>.objects.create().
        """
        instance = self.model()
        many_to_many_to_set = {}
        for field_name in list(kwargs.keys()):
            if instance._meta.get_field(field_name).many_to_many:
                many_to_many_to_set[field_name] = kwargs.pop(field_name)

        with transaction.atomic():
            for field_name, value in kwargs.items():
                setattr(instance, field_name, value)
            instance.full_clean()
            instance.save()

            for field_name, value in many_to_many_to_set.items():
                getattr(instance, field_name).set(value, clear=True)

            return instance


class ToDictMixin:
    @classmethod
    def get_serializable_fields(class_):
        """
        Returns a collection of the names of member variables to include
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

        The base class version of this function returns the value of
        class_.SERIALIZABLE_FIELDS, which defaults to an empty tuple,
        plus the tuple ('pk',).
        """
        return class_.SERIALIZABLE_FIELDS + ('pk',)

    SERIALIZABLE_FIELDS = tuple()

    def to_dict(self, include_fields=None, exclude_fields=None):
        """
        Returns a dictionary representation of this model instance.

        Keyword arguments:
            include_fields -- The names of fields that should be
                included in the dictionary. If this value is None, then
                all fields listed in get_serializable_fields() will
                be included. Names specified here must be present in
                get_serializable_fields(), otherwise ValidationError
                will be raised.

            exclude_fields -- The names of fields that should NOT
                be included in the dictionary. Fields specified both
                here and in include_fields will be excluded. Any fields
                names specified here that are not listed in
                get_serializable_fields() will be ignored.
        """
        default_fields = frozenset(self.get_serializable_fields())
        if include_fields is None:
            include_fields = default_fields

        if exclude_fields is None:
            exclude_fields = set()

        include_fields = set(include_fields)
        illegal_fields = include_fields - default_fields
        if illegal_fields:
            raise exceptions.ValidationError(
                {AutograderModel.INVALID_FIELD_NAMES_KEY: list(illegal_fields)})

        to_include = (include_fields if include_fields is not None
                      else default_fields)
        to_include -= set(exclude_fields)
        result = {}

        for field_name in to_include:
            result[field_name] = getattr(self, field_name)

            # If this isn't a Django Model, skip the field logic
            if not hasattr(self, '_meta'):
                continue

            try:
                field = self._meta.get_field(field_name)
                if field.many_to_one or field.one_to_one:
                    field_val = getattr(self, field_name)
                    if field_val is None:
                        continue
                    result[field_name] = field_val.pk
                elif field.many_to_many:
                    try:
                        result[field_name] = [
                            obj.to_dict() for obj in getattr(self, field_name).all()]
                    except AttributeError:
                        result[field_name] = list(getattr(self, field_name).all())
            except exceptions.FieldDoesNotExist:
                pass

        return result


class _AutograderModelMixin(ToDictMixin):
    @classmethod
    def get_editable_fields(class_):
        """
        Returns a collection of the names of database fields that can be
        edited on this model type using model.validate_and_update()

        The base class version of this function returns the value of
        class_.EDITABLE_FIELDS, which defaults to an empty
        tuple. Thus, you can either set EDITABLE_FIELDS in
        derived classes or override this method.
        """
        return class_.EDITABLE_FIELDS

    EDITABLE_FIELDS = tuple()

    @transaction.atomic
    def validate_and_update(self, **kwargs):
        """
        Updates the values of the fields specified as
        keyword arguments, runs model validation, and saves the
        model.
        Prefer using this method over setting values manually
        and calling full_clean() because this method can perform
        extra validation that depends on the old and new values of
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
            if self._meta.get_field(field_name).many_to_many:
                getattr(self, field_name).set(val, clear=True)
            else:
                setattr(self, field_name, val)

        self.full_clean()
        self.save()


class AutograderModelManager(_AutograderModelManagerMixin, models.Manager):
    """
    The default manager for autograder model classes. This manager
    provides some convenience methods.
    """
    pass


class AutograderModel(_AutograderModelMixin, models.Model):
    """
    The base class for non-polymorphic autograder model classes. This
    class sets a default manager and provides some convenience methods.
    """
    class Meta:
        abstract = True

    objects = AutograderModelManager()

    INVALID_FIELD_NAMES_KEY = 'invalid_field_names'


class PolymorphicAutograderModelManager(_AutograderModelManagerMixin,
                                        poly_models.PolymorphicManager):
    """
    Similar to AutograderModelManager, but is to be used for polymorphic
    models instead.
    """
    pass


class PolymorphicAutograderModel(_AutograderModelMixin,
                                 poly_models.PolymorphicModel):
    """
    Similar to AutograderModel, but is to be used for polymorphic
    models instead.
    """
    class Meta:
        abstract = True

    # NOTE: Currently, the polymorphic manager needs to be set in
    # the first concrete class.
    # objects = PolymorphicAutograderModelManager()
