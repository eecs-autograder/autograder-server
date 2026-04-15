from django.contrib.auth.models import User
from django.core import validators
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from .ag_model_base import AutograderModel, AutograderModelManager
from . import Course


class LateDaysRemaining(AutograderModel):
    objects = AutograderModelManager['LateDaysRemaining']()

    class Meta:
        unique_together = ('course', 'user')

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Remove in version 5.0.0
    old_late_days_remaining = models.IntegerField(
        validators=[validators.MinValueValidator(0)], blank=True, default=0)

    @property
    def late_days_remaining(self) -> int:
        return max(0, self._true_late_days_remaining)

    @late_days_remaining.setter
    def late_days_remaining(self, value: int) -> None:
        if value < 0:
            raise ValidationError({
                'late_days_remaining': 'This value cannot be negative.'
            })

        self._extra_late_days_granted += value - self._true_late_days_remaining

    @property
    def _true_late_days_remaining(self) -> int:
        return (
            self.course.num_late_days + self._extra_late_days_granted
            - self.late_days_used
        )

    _extra_late_days_granted = models.IntegerField(blank=True, default=0)
    late_days_used = models.IntegerField(
        blank=True, default=0, validators=[MinValueValidator(0)])


class LateDayUsageRecord(AutograderModel):
    """
    Represents a record of a student's use of a late day, and all subsequent
    associated submissions.
    """
    objects = AutograderModelManager['LateDayUsageRecord']()

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='late_day_usage_records'
    )

    user_pk = models.IntegerField()
    group_pk = models.IntegerField()
    project_pk = models.IntegerField()
    submission_pk = models.IntegerField()

    timestamp = models.DateTimeField()
    num_late_days_used = models.IntegerField()

    SERIALIZABLE_FIELDS = [
        'course',
        'user_pk',
        'group_pk',
        'project_pk',
        'submission_pk',
        'timestamp',
        'num_late_days_used',
    ]
