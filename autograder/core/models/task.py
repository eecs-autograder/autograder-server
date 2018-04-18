from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from autograder.core.models import AutograderModel


class Task(AutograderModel):
    class Meta:
        abstract = True

    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="A percentage indicating how close the task is to completion.")
    error_msg = models.TextField(blank=True)
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def has_error(self) -> bool:
        return self.error_msg != ''
