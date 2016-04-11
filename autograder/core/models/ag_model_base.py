from django.db import models


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


class _AutograderModelMixin:
    # This set can include model fields, properties, member variables,
    # "-to-one" relationships, etc.
    # In order to include "-to-many" relationships, you must override
    # the default behavior of this function to handle them correctly.
    DEFAULT_INCLUDE_FIELDS = frozenset()

    def validate_and_update(self, **kwargs):
        """
        Updates the values of the fields specified as
        keyword arguments, runs model validation, and saves the
        model.
        Prefer using this method over setting values manually
        and calling full_clean() because this method can perform
        extra validation that depends on the old and new values of
        fields.
        Raises AttributeError if any specified field doesn't exist.
        """
        for field_name, val in kwargs.items():
            if not hasattr(self, field_name):
                raise AttributeError('Field not found: {}'.format(field_name))
            setattr(self, field_name, val)

        self.full_clean()
        self.save()

    def to_dict(self, include_fields=None, exclude_fields=None):
        """
        Returns a dictionary representation of this model instance.

        :param include_fields: The names of fields that should
            be included in the dictionary. If this value is None,
            then all fields listed in DEFAULT_INCLUDE_FIELDS
            will be included.
            Names specified here must be present in
            DEFAULT_INCLUDE_FIELDS, otherwise AttributeError will
            be raised.
        :type include_fields: list or None

        :param exclude_fields: The names of fields that should NOT be
            included in the dictionary. Field names specified here
            will override field names specified in include_fields.
            Fields specified here that are not in DEFAULT_INCLUDE_FIELDS
            or include_fields will be ignored.
        :type exclude_fields: list or None
        """
        default_fields = frozenset(self.DEFAULT_INCLUDE_FIELDS)
        if include_fields is None:
            include_fields = default_fields

        if exclude_fields is None:
            exclude_fields = set()

        include_fields = set(include_fields)
        illegal_fields = include_fields - default_fields
        if illegal_fields:
            raise AttributeError(
                'Cannot serialize the fields: ' + ','.join(illegal_fields))

        to_include = (include_fields if include_fields is not None
                      else self.DEFAULT_INCLUDE_FIELDS)
        to_include -= set(exclude_fields)
        result = {}

        for field_name in to_include:
            result[field_name] = getattr(self, field_name)

        return result


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
