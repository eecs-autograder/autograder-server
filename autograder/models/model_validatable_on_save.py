from django.db import models


class ModelValidatableOnSave(models.Model):
    """
    Derived from django's Model class, provides a validate_and_save()
    function that calls full_clean() (django function in charge of
    validation) before saving.

    Methods:
        validate_and_save()
    """
    def validate_and_save(self, *args, **kwargs):
        self.full_clean()
        self.save(*args, **kwargs)
