import celery
from django.conf import settings
from django.db import transaction
from django.db.models import Sum, F

import autograder.core.models as ag_models
from .grade_submission import grade_submission


def _estimated_grading_time(project_pk: int):
    ag_test_time_max = sum(
        command.time_limit for command in
        ag_models.AGTestCommand.objects.filter(
            ag_test_case__ag_test_suite__project=project_pk
        ).exclude(ag_test_case__ag_test_suite__deferred=True)
    )

    student_test_suite_time_max = sum(
        suite.student_test_validity_check_command.time_limit * suite.max_num_student_tests
        for suite in
        ag_models.MutationTestSuite.objects.filter(project=project_pk).exclude(deferred=True)
    )

    return ag_test_time_max + student_test_suite_time_max


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

            if _estimated_grading_time(submission.project_id) / 60 > 10:
                queue_name_tmpl = settings.SUBMISSION_QUEUE_TMPL.format(submission.project_id)
            else:
                queue_name_tmpl = settings.FAST_QUEUE_TMPL.format(submission.project_id)

            grade_submission.apply_async(
                [submission.pk], queue=queue_name_tmpl.format(submission.project_id))

        print('queued {} submissions'.format(to_queue))


@celery.shared_task(acks_late=True, autoretry_for=(Exception,), default_retry_delay=5)
def register_project_queues(worker_names=None, project_pks=None):
    from autograder.celery import app

    if not worker_names:
        worker_names = [
            worker_name for worker_name in app.control.inspect().active() if
            get_worker_prefix(worker_name) in settings.WORKER_PREFIX_TO_QUEUE_TMPLS
        ]

    print('worker names', worker_names, flush=True)
    if not worker_names:
        return

    if not project_pks:
        project_pks = [project.pk for project in ag_models.Project.objects.all()]

    for worker_name in worker_names:
        prefix = get_worker_prefix(worker_name)
        for pk in project_pks:
            queue_tmpls = settings.WORKER_PREFIX_TO_QUEUE_TMPLS[prefix]
            for tmpl in queue_tmpls:
                res = app.control.add_consumer(tmpl.format(pk), destination=[worker_name])
            print(res)


def get_worker_prefix(worker_hostname: str):
    return worker_hostname.split('@')[0]
