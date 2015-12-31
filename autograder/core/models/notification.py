from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.CharField(max_length=500)
    recipient = models.ForeignKey(User, related_name='notifications')
