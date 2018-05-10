from celery import Celery
from celery.signals import worker_ready

# Make sure that DJANGO_SETTINGS_MODULE is set in your environment.
from django.conf import settings

app = Celery('autograder')
app.config_from_object('django.conf:settings')

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)()


@worker_ready.connect()
def detect_queues(sender, **kwargs):
    if not sender.hostname.startswith(settings.SUBMISSION_WORKER_PREFIX):
        return

    import autograder.core.models as ag_models
    for project in ag_models.Project.objects.all():
        _register_project_queue(project.pk, sender.hostname)


def _register_project_queue(project_pk, worker_name):
    print('project {}'.format(project_pk))
    res = app.control.add_consumer('project{}'.format(project_pk),
                                   destination=[worker_name])
    print(res)
