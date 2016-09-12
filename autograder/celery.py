import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autograder.settings')

from django.conf import settings  # noqa
from django.db import transaction

app = Celery('autograder', backend='amqp')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
if not os.environ.get('IS_CELERYBEAT', False):
    app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.task
def queue_submissions():
    import autograder.core.models as ag_models
    # TODO: integration test
    # TODO: update this to support multiple courses in one system
    newly_queued = ag_models.Submission.objects.filter(
        status=ag_models.Submission.GradingStatus.received
    ).update(status=ag_models.Submission.GradingStatus.queued)

    for submission in newly_queued:
        grade_submission.apply_async(submission.pk)

    print('queued {} submissions'.format(len(newly_queued)))

