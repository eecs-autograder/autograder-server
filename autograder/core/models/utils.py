# import uuid
import fnmatch

from django.db import models
from django.core.exceptions import ValidationError

from polymorphic.models import PolymorphicManager, PolymorphicModel

import autograder.core.shared.utilities as ut


def find_matching_pattern(filename, pattern_objects):
    return ut.find_if(
        pattern_objects,
        lambda pattern_obj: fnmatch.fnmatch(filename, pattern_obj.pattern))


class ManagerWithValidateOnCreate(models.Manager):
    """
    This manager provides a shortcut for creating and validating
    model objects.

    <Model class>.objects.validate_and_create is a shortcut for
        constructing a model object, calling full_clean(), and
        then calling save.

    """
    def validate_and_create(self, **kwargs):
        model = self.model(**kwargs)
        model.full_clean()
        model.save()
        return model

    def create(self, **kwargs):
        raise NotImplementedError(
            'create() is unsupported for this model. '
            'Please use validate_and_create() instead.')


# class PolymorphicManagerWithValidateOnCreate(PolymorphicManager):
#     """
#     Same as ManagerWithValidateOnCreate, but to be used with
#     PolymorphicModels.
#     """
#     def validate_and_create(self, **kwargs):
#         model = self.model(**kwargs)
#         model.full_clean()
#         model.save()
#         return model

#     def create(self, **kwargs):
#         raise NotImplementedError(
#             'create() is unsupported for this model. '
#             'Please use validate_and_create() instead.')


class ModelValidatableOnSave(models.Model):
    """
    This base class provides shortcut for validating and saving
    model objects.
    <Model object>.validate_and_save() is a shortcut for calling
        <Model object>.full_clean() followed by <Model object>.save()

    Methods:
        validate_and_save()
    """
    class Meta:
        abstract = True

    def validate_and_save(self):
        self.full_clean()
        self.save()


# class PolymorphicModelValidatableOnSave(PolymorphicModel):
#     """
#     Same as ModelValidatableOnSave, but to be used with polymorphic models.
#     """
#     def validate_and_save(self):
#         self.full_clean()
#         self.save()
