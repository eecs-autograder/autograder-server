from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres import fields as pg_fields

from picklefield.fields import PickledObjectField

from autograder.utilities.json_serializable_interface import JsonSerializable

import autograder.core.shared.global_constants as gc


class JsonSerializableClassField(pg_fields.JSONField):
    def __init__(self, class_, **kwargs):
        self._class = class_

        if not issubclass(class_, JsonSerializable):
            raise TypeError(
                'Error preparing the field {}. '
                'Class must implement the JsonSerializable interface.')

        super().__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.update({
            'class_': self._class
        })
        return name, path, args, kwargs

    def get_prep_value(self, value):
        if value is None:
            return super().get_prep_value(value)

        if isinstance(value, self._class):
            value = value.to_json()

        return super().get_prep_value(value)

    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            return None

        if isinstance(value, self._class):
            return value

        return self._class.from_json(value)

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def validate(self, value, model_instance):
        if not isinstance(value, self._class):
            raise TypeError(
                'Error preparing value of type {} for the field {}. '
                'Expected value of type {}'.format(
                    type(value), self.name, self._class))

        # The postgres JSONField tries to parse the JSON, but at this
        # point we have an unserialized class object. Rather
        # than wasting time converting to json and parsing just
        # for validation, we'll call the base field class's
        # validate() method to check the other properties of the field.
        super(pg_fields.JSONField, self).validate(value, model_instance)


class ClassField(PickledObjectField):
    def __init__(self, class_, **kwargs):
        self._class = class_
        super().__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.update({
            'class_': self._class
        })
        return name, path, args, kwargs

    def get_prep_value(self, value):
        if value is None or isinstance(value, self._class):
            return super().get_prep_value(value)

        raise TypeError(
            'Error preparing value of type {} to the field {}. '
            'Expected value of type {}'.format(
                type(value), self.name, self._class))


class ValidatedArrayField(pg_fields.ArrayField):
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

    def clean(self, value, model_instance):
        value = super().clean(value, model_instance)

        cleaned_value = []
        errors = []
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

    def validate(self, value, model_instance):
        # The validate() function defined in ArrayField has the
        # behavior we want to get rid of, so we instead call
        # validate() on ArrayField's base class.
        super(ArrayField, self).validate(value, model_instance)

    def run_validators(self, value):
        # The run_validators() function defined in ArrayField has the
        # behavior we want to get rid of, so we instead call
        # run_validators() on ArrayField's base class.
        super(ArrayField, self).run_validators(value)


class StringArrayField(ValidatedArrayField):
    """
    A convenience wrapper around ValidatedArrayField that always
    stores a list of strings.

    Additional options:
        strip_strings -- When true, leading and trailing whitespace is
            stripped from the items in the array.
            Default value: True
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

    def __init__(self, strip_strings=True, allow_empty_strings=False,
                 string_validators=[], max_string_length=gc.MAX_CHAR_FIELD_LEN,
                 **kwargs):
        self.base_string_field = models.CharField(
            max_length=max_string_length, blank=allow_empty_strings,
            validators=string_validators)
        self.strip_strings = strip_strings
        self.allow_empty_strings = allow_empty_strings
        self.max_string_length = max_string_length
        self.string_validators = string_validators

        super().__init__(self.base_string_field, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs['base_field']
        kwargs.update({
            'strip_strings': self.strip_strings,
            'allow_empty_strings': self.allow_empty_strings,
            'max_string_length': self.max_string_length,
            'string_validators': self.string_validators
        })
        return name, path, args, kwargs

    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            return value

        if not self.strip_strings:
            return value

        stripped = [item.strip() if item is not None else item
                    for item in value]

        return stripped

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)


class ShortStringField(models.CharField):
    def __init__(self, max_length=gc.MAX_CHAR_FIELD_LEN, strip=False,
                 **kwargs):
        self.strip = strip
        super().__init__(max_length=max_length, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # del kwargs['max_length']
        kwargs.update({
            'strip': self.strip
        })
        return name, path, args, kwargs

    def to_python(self, value):
        if value is not None:
            value = value.strip()

        return super().to_python(value)

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)


class StringChoiceField(ShortStringField):
    def __init__(self, choices=[], **kwargs):
        super().__init__(choices=zip(choices, choices), **kwargs)
