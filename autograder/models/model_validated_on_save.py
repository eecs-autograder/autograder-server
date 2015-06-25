from django.db import models


class ModelValidatedOnSave(models.Model):
    """
    Derived from django's Model class, provides an interface
    for writing Models that are automatically validated
    when Model.save() is called.

    Overridden member functions:
        save()

    Abstract methods:
        validate_fields()
    """
    def save(self, *args, **kwargs):
        self.validate_fields()
        super().save(*args, **kwargs)

    def validate_fields(self):
        """
        Checks the state of this Model object and raises
        ValueError if any fields are invalid.
        """
        raise NotImplementedError("Derived classes must override this method.")
