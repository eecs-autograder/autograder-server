import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autograder.settings')
os.environ.setdefault('CELERY_CONFIG_MODULE', 'autograder.settings.celery')

from django.conf import settings  # noqa
from django.db import transaction  # noqa

app = Celery('autograder')
app.config_from_envvar('CELERY_CONFIG_MODULE')

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task
def queue_submissions():
    import autograder.core.models as ag_models
    from autograder.grading_tasks.tasks import grade_submission
    # TODO: integration test
    # TODO: update this to support multiple courses in one system
    with transaction.atomic():
        to_queue = list(ag_models.Submission.objects.select_for_update().filter(
            status=ag_models.Submission.GradingStatus.received))
        print(to_queue)

        for submission in to_queue:
            print('adding submission{} to queue for grading'.format(submission.pk))
            submission.status = 'queued'
            submission.save()
            grade_submission.apply_async([submission.pk])

        print('queued {} submissions'.format(to_queue))
