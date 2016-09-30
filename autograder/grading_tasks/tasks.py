import random
import time
import traceback

from django.conf import settings
from django.db import transaction

import celery

import autograder.core.models as ag_models
from autograder_sandbox import AutograderSandbox


@celery.shared_task
def grade_submission(submission_id):
    try:
        submission = _mark_as_being_graded(submission_id)
        _run_non_deferred_tests(submission)

        project = submission.submission_group.project
        deferred_queryset = project.autograder_test_cases.filter(deferred=True)
        for ag_test in deferred_queryset:
            grade_ag_test.apply_async([ag_test.pk, submission_id], queue='deferred')
        # signatures = (grade_ag_test.s(ag_test.pk, submission_id)
        #               for ag_test in deferred_queryset)
        # callback = mark_as_finished.s(submission_id)
        # print(list(signatures))
        # celery.chord(signatures, callback).apply_async(queue='deferred')
    except Exception:
        traceback.print_exc()
        with transaction.atomic():
            submission = ag_models.Submission.objects.select_for_update().get(
                pk=submission_id)
            submission.status = ag_models.Submission.GradingStatus.error
            submission.save()
        raise


def _mark_as_being_graded(submission_id):
    with transaction.atomic():
        submission = ag_models.Submission.objects.select_for_update().get(
            pk=submission_id)
        if (submission.status ==
                ag_models.Submission.GradingStatus.removed_from_queue):
            print('submission {} has been removed '
                  'from the queue'.format(submission.pk))
            return
        submission.status = ag_models.Submission.GradingStatus.being_graded
        submission.save()
        return submission


def _run_non_deferred_tests(submission):
        project = submission.submission_group.project
        for ag_test in project.autograder_test_cases.filter(deferred=False):
            print('running test: {}'.format(ag_test.pk))
            num_retries = 0
            while True:
                try:
                    grade_ag_test_impl(ag_test, submission)
                    break
                except Exception:
                    if num_retries == settings.AG_TEST_MAX_RETRIES:
                        print('max retries exceeded for '
                              'non-deferred test {}'.format(ag_test.pk))
                        raise
                    num_retries += 1
                    print('retrying: {}'.format(num_retries))
                    time.sleep(
                        random.randint(settings.AG_TEST_MIN_RETRY_DELAY,
                                       settings.AG_TEST_MAX_RETRY_DELAY))

        mark_as_waiting_for_deferred(submission.pk)


@celery.shared_task
def mark_as_finished(chord_results, submission_id):
    print(chord_results, submission_id)
    print(ag_models.Submission.objects.all())
    with transaction.atomic():
        submission = ag_models.Submission.objects.select_for_update().get(
            pk=submission_id)

        mark_as_finished.mocking_hook()

        submission.status = ag_models.Submission.GradingStatus.finished_grading
        submission.save()
mark_as_finished.mocking_hook = lambda: None


def mark_as_waiting_for_deferred(submission_id):
    with transaction.atomic():
        submission = ag_models.Submission.objects.select_for_update().get(
            pk=submission_id)
        if (submission.status !=
                ag_models.Submission.GradingStatus.finished_grading):
            submission.status = (
                ag_models.Submission.GradingStatus.waiting_for_deferred)
            submission.save()


@celery.shared_task(bind=True, max_retries=settings.AG_TEST_MAX_RETRIES)
def grade_ag_test(self, ag_test_id, submission_id):
    try:
        ag_test = ag_models.AutograderTestCaseBase.objects.get(pk=ag_test_id)
        submission = ag_models.Submission.objects.get(pk=submission_id)

        grade_ag_test_impl(ag_test, submission)
    except Exception as e:
        self.retry(exc=e,
                   countdown=random.randint(settings.AG_TEST_MIN_RETRY_DELAY,
                                            settings.AG_TEST_MAX_RETRY_DELAY))


def grade_ag_test_impl(ag_test, submission):
    group = submission.submission_group

    grade_ag_test_impl.mocking_hook()

    sandbox = AutograderSandbox(
        name='submission{}-test{}'.format(submission.pk, ag_test.pk),
        environment_variables={
            'usernames': ' '.join(sorted(group.member_names))},
        allow_network_access=ag_test.allow_network_connections)

    with sandbox:
        result = ag_test.run(submission, sandbox)
        result.save()
grade_ag_test_impl.mocking_hook = lambda: None


@celery.shared_task
def queue_submissions():
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
            grade_submission.apply_async([submission.pk], queue='submissions')

        print('queued {} submissions'.format(to_queue))


@celery.shared_task
def check_for_finished_deferreds():
    waiting_for_deferred = ag_models.Submission.objects.filter(
        status=ag_models.Submission.GradingStatus.waiting_for_deferred)
    for submission in waiting_for_deferred:
        if (submission.results.count() ==
                submission.submission_group.project.autograder_test_cases.count()):
            print('submission {} is finished'.format(submission.pk))
            with transaction.atomic():
                locked = ag_models.Submission.objects.select_for_update().get(pk=submission.pk)
                locked.status = ag_models.Submission.GradingStatus.finished_grading
                locked.save()
