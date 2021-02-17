from celery import Celery
from celery.signals import worker_ready

# Make sure that DJANGO_SETTINGS_MODULE is set in your environment.
from django.conf import settings
from django.dispatch.dispatcher import receiver

app = Celery('autograder')
app.config_from_object('django.conf:settings')

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@receiver(worker_ready)
def detect_queues(sender, **kwargs):
    import autograder.core.models as ag_models
    from autograder.grading_tasks.tasks.queueing import get_worker_prefix, register_project_queues

    if get_worker_prefix(sender.hostname) not in settings.WORKER_PREFIX_TO_QUEUE_TMPLS:
        return

    project_pks = [project.pk for project in ag_models.Project.objects.all()]

    page_size = 50
    for i in range(0, len(project_pks), page_size):
        register_project_queues.s(
            worker_names=[sender.hostname],
            project_pks=project_pks[i:i + page_size]
        ).apply_async(
            queue='small_tasks'
        )
