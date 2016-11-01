import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autograder.settings.production')

from django.conf import settings  # noqa
from django.db import transaction  # noqa

app = Celery('autograder')
app.config_from_object('django.conf:settings')

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
