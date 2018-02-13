import traceback

import celery

from django.core.cache import cache
from django.db import transaction

import autograder.core.models as ag_models
from .grade_student_test_suite import (
    grade_student_test_suite_impl, grade_deferred_student_test_suite)
from .grade_ag_test import grade_ag_test_suite_impl, grade_deferred_ag_test_suite
from .utils import retry_should_recover, mark_submission_as_error


@celery.shared_task(acks_late=True)
def grade_submission(submission_pk):
    try:
        submission = _mark_submission_as_being_graded(submission_pk)
        if submission is None:
            return

        project = submission.submission_group.project  # type: ag_models.Project

        @retry_should_recover
        def load_non_deferred_ag_suites():
            return list(project.ag_test_suites.filter(deferred=False))

        for suite in load_non_deferred_ag_suites():
            grade_ag_test_suite_impl(suite, submission)

        @retry_should_recover
        def load_non_deferred_student_suites():
            return list(project.student_test_suites.filter(deferred=False))

        for suite in load_non_deferred_student_suites():
            grade_student_test_suite_impl(suite, submission)

        @retry_should_recover
        def mark_as_waiting_for_deferred():
            submission.status = (
                ag_models.Submission.GradingStatus.waiting_for_deferred)
            submission.save()

        mark_as_waiting_for_deferred()

        @retry_should_recover
        def load_deferred_ag_suites():
            return list(project.ag_test_suites.filter(deferred=True))

        ag_suite_signatures = [grade_deferred_ag_test_suite.s(ag_test_suite.pk, submission_pk)
                               for ag_test_suite in load_deferred_ag_suites()]

        @retry_should_recover
        def load_deferred_student_suites():
            return list(project.student_test_suites.filter(deferred=True))

        student_suite_signatures = [grade_deferred_student_test_suite.s(suite.pk, submission.pk)
                                    for suite in load_deferred_student_suites()]

        signatures = ag_suite_signatures + student_suite_signatures
        if not signatures:
            _mark_submission_as_finished_impl(submission_pk)
            return

        if len(signatures) == 1:
            signatures[0].apply_async(
                link_error=on_chord_error.s(),
                link=mark_submission_as_finished.s(submission_pk))
        else:
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
            'submission_group__project').get(pk=submission_pk)
        if (submission.status ==
                ag_models.Submission.GradingStatus.removed_from_queue):
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
        'submission_group__project').get(pk=submission_pk)
    cache_key = 'project_{}_submission_normal_results_{}'.format(
        submission.submission_group.project.pk, submission.pk)
    cache.delete(cache_key)
