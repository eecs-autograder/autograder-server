from django.db import models
from django.contrib.auth.models import User

from .ag_model_base import AutograderModel


class Notification(AutograderModel):
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.CharField(max_length=500)
    recipient = models.ForeignKey(User, related_name='notifications')

    _DEFAULT_TO_DICT_FIELDS = frozenset([
        'timestamp',
        'message',
        'recipient',
    ])

    @classmethod
    def get_default_to_dict_fields(class_):
        return class_._DEFAULT_TO_DICT_FIELDS

    @classmethod
    def is_read_only(class_):
        return True
