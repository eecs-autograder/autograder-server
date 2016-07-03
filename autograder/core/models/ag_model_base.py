from django.db import models
from django.core import exceptions

import polymorphic.models as poly_models


class _AutograderModelManagerMixin:
    def validate_and_create(self, **kwargs):
        """
        This method is a shortcut for constructing a model object,
        calling full_clean(), and then calling save().
        Prefer using this method over <Model class>.objects.create().
        """
        instance = self.model(**kwargs)
        instance.full_clean()
        instance.save()
        return instance

_INVALID_FIELD_NAMES_KEY = 'invalid_field_names'


class _AutograderModelMixin:
    @classmethod
    def get_default_to_dict_fields(class_):
        """
        Returns a collection of the names of member variables to include
        by default in the dictionary returned by to_dict()

        This collection can include model fields, properties, member
        variables, "-to-one" relationships, and anything else for which
        getattr() returns the desired value.
        By default, "-to-one" relationships will be represented as the
        primary key of the related object.
        In order to include "-to-many" relationships, you must override
        to_dict() to handle them correctly.
        """
        raise NotImplementedError('Subclasses should override this method')

    @classmethod
    def is_read_only(class_):
        """
        If this method returns True, then model objects of that type
        should be considered read-only. Effectively, this makes
        Model.get_editable_fields() return an empty list.
        """
        return False

    @classmethod
    def get_editable_fields(class_):
        """
        Returns a collection of the names of database fields that can be
        edited on this model type using model.validate_and_update()
        """
        if class_.is_read_only():
            return []

        raise NotImplementedError(
            "Subclasses that aren't read-only should override this method")

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
                    {_INVALID_FIELD_NAMES_KEY: [field_name]})
            if field_name not in self.get_editable_fields():
                raise exceptions.ValidationError(
                    {'non_editable_fields': [field_name]})
            setattr(self, field_name, val)

        self.full_clean()
        self.save()

    def to_dict(self, include_fields=None, exclude_fields=None):
        """
        Returns a dictionary representation of this model instance.
        Note: The primary key of this model instance is included in the
        representation by default under the key 'pk'. 'pk' should not be
        listed in include_fields or exclude_fields, and will be ignored
        if it is. If a derived class wishes to exclude the primary key
        from its dictionary representation, the derived class should
        override the _include_pk property

        Keyword arguments:
            include_fields -- The names of fields that should be
                included in the dictionary. If this value is None, then
                all fields listed in get_default_to_dict_fields() will
                be included. Names specified here must be present in
                get_default_to_dict_fields(), otherwise ValidationError
                will be raised.

            param exclude_fields -- The names of fields that should NOT
                be included in the dictionary. Fields specified both
                here and in include_fields will be excluded. Any fields
                names specified here that are not listed in
                get_default_to_dict_fields() will be ignored.
        """
        default_fields = frozenset(self.get_default_to_dict_fields())
        if include_fields is None:
            include_fields = default_fields

        if exclude_fields is None:
            exclude_fields = set()

        include_fields = set(include_fields)
        illegal_fields = include_fields - default_fields
        if illegal_fields:
            raise exceptions.ValidationError(
                {_INVALID_FIELD_NAMES_KEY: list(illegal_fields)})

        to_include = (include_fields if include_fields is not None
                      else default_fields)
        to_include -= set(exclude_fields)
        result = {}

        for field_name in to_include:
            result[field_name] = getattr(self, field_name)
            try:
                field = self._meta.get_field(field_name)
                if field.many_to_one or field.one_to_one:
                    field_val = getattr(self, field_name)
                    if field_val is None:
                        continue
                    result[field_name] = field_val.pk
            except exceptions.FieldDoesNotExist:
                pass

        if self._include_pk:
            result['pk'] = self.pk

        return result

    @property
    def _include_pk(self):
        '''
        Derived classes can override this property if they wish to
        exclude the primary key attribute from their dictionary
        representation.
        '''
        return True


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
