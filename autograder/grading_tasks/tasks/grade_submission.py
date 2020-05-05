import traceback

import celery

from django.conf import settings
from django.db import transaction

import autograder.core.models as ag_models
from autograder.core.caching import delete_cached_submission_result
from autograder.utils.retry import retry_should_recover

from .grade_mutation_test_suite import (
    grade_mutation_test_suite_impl, grade_deferred_mutation_test_suite)
from .grade_ag_test import grade_ag_test_suite_impl, grade_deferred_ag_test_suite
from .utils import mark_submission_as_error, load_queryset_with_retry


@celery.shared_task(acks_late=True)
def grade_submission(submission_pk):
    try:
        submission = _mark_submission_as_being_graded(submission_pk)
        if submission is None:
            return

        # _mark_submission_as_being_graded pre-selects group and
        # project, so this doesn't need retry logic.
        project = submission.group.project  # type: ag_models.Project

        for suite in load_queryset_with_retry(project.ag_test_suites.filter(deferred=False)):
            grade_ag_test_suite_impl(suite, submission)

        for suite in load_queryset_with_retry(project.mutation_test_suites.filter(deferred=False)):
            grade_mutation_test_suite_impl(suite, submission)

        @retry_should_recover
        def mark_as_waiting_for_deferred():
            # Make sure to not overwrite denormalized ag test results
            ag_models.Submission.objects.filter(
                pk=submission.pk
            ).update(status=ag_models.Submission.GradingStatus.waiting_for_deferred)

        mark_as_waiting_for_deferred()

        deferred_ag_test_suites = load_queryset_with_retry(
            project.ag_test_suites.filter(deferred=True))

        ag_suite_signatures = [
            grade_deferred_ag_test_suite.s(
                ag_test_suite.pk, submission_pk
            ).set(queue=settings.DEFERRED_QUEUE_TMPL.format(ag_test_suite.project_id))
            for ag_test_suite in deferred_ag_test_suites
        ]

        deferred_mutation_test_suites = load_queryset_with_retry(
            project.mutation_test_suites.filter(deferred=True))

        mutation_suite_signatures = [
            grade_deferred_mutation_test_suite.s(
                suite.pk, submission.pk
            ).set(queue=settings.DEFERRED_QUEUE_TMPL.format(suite.project_id))
            for suite in deferred_mutation_test_suites
        ]

        signatures = ag_suite_signatures + mutation_suite_signatures
        if not signatures:
            _mark_submission_as_finished_impl(submission_pk)
            return

        callback = mark_submission_as_finished.s(submission_pk).on_error(on_chord_error.s())
        celery.chord(signatures)(callback)
    except Exception:
        print('Error grading submission')
        traceback.print_exc()
        mark_submission_as_error(submission_pk, traceback.format_exc())
        raise


@retry_should_recover
def _mark_submission_as_being_graded(submission_pk):
    with transaction.atomic():
        submission = ag_models.Submission.objects.select_for_update().select_related(
            'group__project').get(pk=submission_pk)
        if submission.status == ag_models.Submission.GradingStatus.removed_from_queue:
            print('submission {} has been removed '
                  'from the queue'.format(submission.pk))
            return None

        submission.status = ag_models.Submission.GradingStatus.being_graded
        submission.save()
        return submission


@celery.shared_task(queue='small_tasks', acks_late=True)
def mark_submission_as_finished(chord_results, submission_pk):
    _mark_submission_as_finished_impl(submission_pk)


@celery.shared_task(queue='small_tasks', acks_late=True)
def on_chord_error(request, exc, traceback):
    print('Error in deferred test case chord. '
          'This most likely means that a deferred test '
          'case exceeded the retry limit.')
    print(traceback)
    print(exc)


@retry_should_recover
def _mark_submission_as_finished_impl(submission_pk):
    ag_models.Submission.objects.filter(
        pk=submission_pk
    ).update(status=ag_models.Submission.GradingStatus.finished_grading)

    submission = ag_models.Submission.objects.select_related(
        'group__project').get(pk=submission_pk)
    delete_cached_submission_result(submission)
