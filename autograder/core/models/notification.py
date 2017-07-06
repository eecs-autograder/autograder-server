from django.db import models
from django.contrib.auth.models import User

from .ag_model_base import AutograderModel


class Notification(AutograderModel):
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.CharField(max_length=500)
    recipient = models.ForeignKey(User, related_name='notifications')

    SERIALIZABLE_FIELDS = (
        'pk',
        'timestamp',
        'message',
        'recipient',
    )
