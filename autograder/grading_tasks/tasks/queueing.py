import celery
from django.conf import settings
from django.db import transaction

import autograder.core.models as ag_models
from .grade_submission import grade_submission


@celery.shared_task
def queue_submissions():
    with transaction.atomic():
        to_queue = list(ag_models.Submission.objects.select_for_update().filter(
            status=ag_models.Submission.GradingStatus.received).reverse())
        print(to_queue)

        for submission in to_queue:
            print('adding submission{} to queue for grading'.format(submission.pk))
            submission.status = ag_models.Submission.GradingStatus.queued
            submission.save()
            grade_submission.apply_async([submission.pk],
                                         queue=_get_submission_queue_name(submission))

        print('queued {} submissions'.format(to_queue))


@celery.shared_task(acks_late=True, autoretry_for=(Exception,))
def register_project_queues(worker_names=None, project_pks=None):
    from autograder.celery import app

    if not worker_names:
        worker_names = [worker_name for worker_name in app.control.inspect().active()
                        if worker_name.startswith(settings.SUBMISSION_WORKER_PREFIX)]

    print('worker names', worker_names)
    if not worker_names:
        return

    if not project_pks:
        project_pks = [project.pk for project in ag_models.Project.objects.all()]

    print('project pks:', project_pks)
    for pk in project_pks:
        res = app.control.add_consumer('project{}'.format(pk), destination=worker_names)
        print(res)


def _get_submission_queue_name(submission: ag_models.Submission):
    return 'project{}'.format(submission.submission_group.project_id)
