from django.db import models
from django.core.files.storage import FileSystemStorage


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


# -----------------------------------------------------------------------------

class ModelValidatableOnSave(models.Model):
    """
    This base class provides shortcut for validating and saving
    model objects.
    <Model object>.validate_and_save() is a shortcut for calling
        <Model object>.full_clean() followed by <Model object>.save()

    Methods:
        validate_and_save()
    """
    def validate_and_save(self):
        self.full_clean()
        self.save()


# -----------------------------------------------------------------------------

class UploadedFileStorage(FileSystemStorage):
    """
    Provides the following customized storage behaviors:
        - If a file already exists, ValidationError is raised rather
          than renaming the file.
        - If a filename contains illegal characters, ValidationError is
          raised rather than stripping out the illegal characters.
    """
