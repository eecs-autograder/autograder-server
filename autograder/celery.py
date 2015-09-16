# import os
# import sys

# from celery import Celery
# # from autograder import settings

# # set the default Django settings module for the 'celery' program.
# sys.path.append('..')
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

# from django.conf import settings

# CELERY_ACCEPT_CONTENT = ['json']

# app = Celery('autograder', broker='amqp://')

# # Using a string here means the worker will not have to
# # pickle the object when using Windows.
# app.config_from_object('django.conf:settings')
# app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# app.conf.CELERY_ACCEPT_CONTENT = ['json']
# app.conf.CELERY_TASK_SERIALIZER = 'json'
# app.conf.CELERY_RESULT_SERIALIZER = 'json'
