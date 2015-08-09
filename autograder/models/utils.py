# import uuid

from django.db import models

from polymorphic import PolymorphicManager, PolymorphicModel


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


class PolymorphicManagerWithValidateOnCreate(PolymorphicManager):
    """
    Same as ManagerWithValidateOnCreate, but to be used with
    PolymorphicModels.
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


class PolymorphicModelValidatableOnSave(PolymorphicModel):
    """
    Same as ModelValidatableOnSave, but to be used with polymorphic models.
    """
    def validate_and_save(self):
        self.full_clean()
        self.save()


# class UUIDModelMixin(object):
#     """
#     Mixin class that adds a UUID field called "unique_id" to models.
#     """
#     unique_id = models.UUIDField(
#         primary_key=True, default=uuid.uuid4, editable=False)
