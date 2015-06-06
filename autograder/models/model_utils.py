from django.db import models


class ModelValidatedOnSave(models.Model):
    def save(self, *args, **kwargs):
        self.validate_fields()
        super().save(*args, **kwargs)

    def validate_fields(self):
        """
        Checks the state of this Model object and raises
        django.core.exceptions.ValidationError if any fields
        are invalid.
        """
        raise NotImplementedError("Derived classes must override this method.")
