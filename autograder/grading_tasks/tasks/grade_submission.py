from autograder.core.models.submission import Submission
import traceback

import celery

from django.conf import settings
from django.db import transaction
from django.db.models.expressions import F
from django.utils import timezone

import autograder.core.models as ag_models
from autograder.core.caching import delete_cached_submission_result
from autograder.utils.retry import retry_should_recover

from .grade_mutation_test_suite import (
    grade_mutation_test_suite_impl, grade_deferred_mutation_test_suite)
from .grade_ag_test import (
    grade_ag_test_suite_impl,
    grade_deferred_ag_test_suite
)
from .utils import mark_submission_as_error, load_queryset_with_retry
from autograder.core.submission_email_receipts import send_submission_score_summary_email

from .exceptions import SubmissionRejected, SubmissionRemovedFromQueue


class SubmissionGrader:
    def __init__(self, submission_pk: int):
        self.submission_pk = submission_pk
        # Note: Avoid aliasing the object this refers to, as the object
        # is replaced at certain points in the grading process.
        self._submission = None
        self._project = None

        self._reraise_fatal_error = True

    @property
    def submission(self) -> ag_models.Submission:
        assert self._submission is not None
        return self._submission

    @property
    def project(self) -> ag_models.Project:
        assert self._project is not None
        return self._project

    def grade_submission(self) -> None:
        try:
            self.grade_submission_impl()
        except Exception as e:
            print('Error grading submission')
            traceback.print_exc()
            self.record_submission_grading_error(traceback.format_exc())
            if self._reraise_fatal_error:
                raise

    def grade_submission_impl(self) -> None:
        try:
            self.load_submission()
        except SubmissionRemovedFromQueue:
            return

        try:
            self.grade_non_deferred_suites()
        except SubmissionRejected:
            self.mark_submission_as_rejected()
            return

        self.send_non_deferred_tests_finished_email()
        self.grade_deferred_suites()

    @retry_should_recover
    def load_submission(self):
        """
        Loads the submission, marks it as being_graded, and sets
        self.submission to the loaded submission and self.project to
        the project it belongs to.
        """
        with transaction.atomic():
            self._submission = ag_models.Submission.objects.select_for_update().select_related(
                'project'
            ).get(pk=self.submission_pk)
            self._project = self.submission.project
            if self.submission.status == ag_models.Submission.GradingStatus.removed_from_queue:
                print('submission {} has been removed '
                      'from the queue'.format(self.submission.pk))
                raise SubmissionRemovedFromQueue

            self.submission.status = ag_models.Submission.GradingStatus.being_graded
            self.submission.grading_start_time = timezone.now()
            self.submission.save()

    def grade_non_deferred_suites(self):
        non_deferred_ag_test_suites = load_queryset_with_retry(
            self.project.ag_test_suites.filter(deferred=False))
        for suite in non_deferred_ag_test_suites:
            self.grade_ag_test_suite(suite)

        non_deferred_mutation_suites = load_queryset_with_retry(
            self.project.mutation_test_suites.filter(deferred=False))
        for suite in non_deferred_mutation_suites:
            self.grade_mutation_test_suite(suite)

    # In rerun override:
    # - check if rerun is cancelled before running suite
    #   and then raise RerunCancelled
    # - if suite is not one of the suites to rerun (and not rerun all), do nothing
    def grade_ag_test_suite(self, suite: ag_models.AGTestSuite) -> None:
        grade_ag_test_suite_impl(
            suite,
            self.submission,
            on_suite_setup_finished=self.save_denormalized_ag_test_suite_result,
            on_test_case_finished=self.save_denormalized_ag_test_case_result,
        )

    @retry_should_recover
    def mark_submission_as_rejected(self):
        with transaction.atomic():
            if self.submission.is_bonus_submission:
                ag_models.Group.objects.select_for_update().filter(
                    pk=self.submission.group_id
                ).update(bonus_submissions_used=F('bonus_submissions_used') - 1)

            self.submission.is_bonus_submission = False
            self.submission.status = ag_models.Submission.GradingStatus.rejected
            self.submission.save()

    # In rerun override:
    # - check if rerun is cancelled before running suite
    #   and then raise RerunCancelled
    # - if suite is not one of the suites to rerun (and not rerun all), do nothing
    def grade_mutation_test_suite(self, suite: ag_models.MutationTestSuite) -> None:
        grade_mutation_test_suite_impl(suite, self.submission)

    @retry_should_recover
    def save_denormalized_ag_test_suite_result(
        self,
        ag_test_suite_result: ag_models.AGTestSuiteResult
    ) -> None:
        with transaction.atomic():
            submission = Submission.objects.select_for_update().get(pk=self.submission.pk)
            key = str(ag_test_suite_result.ag_test_suite_id)
            submission.denormalized_ag_test_results[key] = ag_test_suite_result.to_dict()
            submission.save()
            self._submission = submission

    @retry_should_recover
    def save_denormalized_ag_test_case_result(
        self,
        ag_test_case_result: ag_models.AGTestCaseResult
    ) -> None:
        with transaction.atomic():
            submission = Submission.objects.select_for_update().get(pk=self.submission.pk)
            print(submission.denormalized_ag_test_results)
            ag_test_case = ag_test_case_result.ag_test_case
            submission.denormalized_ag_test_results[
                str(ag_test_case.ag_test_suite_id)
            ]['ag_test_case_results'][str(ag_test_case.pk)] = ag_test_case_result.to_dict()

            submission.save()
            self._submission = submission

    def send_non_deferred_tests_finished_email(self) -> None:
        if self.project.send_email_on_non_deferred_tests_finished:
            try:
                # # Refresh the submission to load the denormalized
                # # test case results
                # submission.refresh_from_db()
                send_submission_score_summary_email(self.submission)
            except Exception:
                print('Error sending email receipt:')
                traceback.print_exc()

    # Full override for rerun (can still call get_deferred_suite_task_signatures)
    # - DON'T mark as waiting for deferred
    # - only mark as finished if full submission rerun
    def grade_deferred_suites(self) -> None:
        self.mark_as_waiting_for_deferred()
        deferred_task_signatures = self.get_deferred_suite_task_signatures()
        if not deferred_task_signatures:
            _mark_submission_as_finished_impl(self.submission.pk)
            return

        callback = mark_submission_as_finished.s(self.submission.pk).on_error(on_chord_error.s())
        celery.chord(deferred_task_signatures)(callback)

    @retry_should_recover
    def mark_as_waiting_for_deferred(self):
        ag_models.Submission.objects.filter(
            pk=self.submission.pk
        ).update(
            status=ag_models.Submission.GradingStatus.waiting_for_deferred,
            non_deferred_grading_end_time=timezone.now()
        )

    def get_deferred_suite_task_signatures(self):
        deferred_ag_test_suites = load_queryset_with_retry(
            self.project.ag_test_suites.filter(deferred=True))
        ag_suite_signatures = [
            self.get_deferred_ag_test_suite_task_signature(ag_test_suite)
            for ag_test_suite in deferred_ag_test_suites
        ]

        deferred_mutation_test_suites = load_queryset_with_retry(
            self.project.mutation_test_suites.filter(deferred=True))
        mutation_suite_signatures = [
            self.get_deferred_mutation_suite_task_signature(suite)
            for suite in deferred_mutation_test_suites
        ]

        return ag_suite_signatures + mutation_suite_signatures

    # Override for rerun, use only specified suites/tests, and use the rerun queue
    def get_deferred_ag_test_suite_task_signature(self, suite: ag_models.AGTestSuite):
        return grade_deferred_ag_test_suite.s(
            suite.pk, self.submission_pk
        ).set(queue=settings.DEFERRED_QUEUE_TMPL.format(suite.project_id))

    # Override for rerun, use only specified suites/tests, and use the rerun queue
    def get_deferred_mutation_suite_task_signature(self, suite: ag_models.MutationTestSuite):
        return grade_deferred_mutation_test_suite.s(
            suite.pk, self.submission.pk
        ).set(queue=settings.DEFERRED_QUEUE_TMPL.format(suite.project_id))

    # @property
    # def deferred_suite_queue_name_template(self):  # Override me for rerun
    #     return settings.DEFERRED_QUEUE_TMPL

    # @property
    # def deferred_ag_test_suite_task(self):   # Override me for rerun
    #     return grade_deferred_ag_test_suite

    def record_submission_grading_error(self, error_msg: str) -> None:
        mark_submission_as_error(self.submission_pk, traceback.format_exc())


@celery.shared_task(acks_late=True)
def grade_submission(submission_pk):
    grader = SubmissionGrader(submission_pk)
    return grader.grade_submission()

    try:
        submission = _mark_submission_as_being_graded(submission_pk)
        if submission is None:
            return

        # _mark_submission_as_being_graded pre-selects group and
        # project, so this doesn't need retry logic.
        project = submission.group.project  # type: ag_models.Project

        for suite in load_queryset_with_retry(project.ag_test_suites.filter(deferred=False)):
            try:
                grade_ag_test_suite_impl(suite, submission)
            except SubmissionRejected:
                _mark_submission_as_rejected(submission)

        for suite in load_queryset_with_retry(project.mutation_test_suites.filter(deferred=False)):
            grade_mutation_test_suite_impl(suite, submission)

        @retry_should_recover
        def mark_as_waiting_for_deferred():
            # Make sure to not overwrite denormalized ag test results
            ag_models.Submission.objects.filter(
                pk=submission.pk
            ).update(status=ag_models.Submission.GradingStatus.waiting_for_deferred)

        mark_as_waiting_for_deferred()

        if project.send_email_on_non_deferred_tests_finished:
            try:
                # Refresh the submission to load the denormalized
                # test case results
                submission.refresh_from_db()
                send_submission_score_summary_email(submission)
            except Exception:
                print('Error sending email receipt:')
                traceback.print_exc()

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


# @retry_should_recover
# def _mark_submission_as_rejected(submission: ag_models.Submission):
#     with transaction.atomic():
#         if submission.is_bonus_submission:
#             ag_models.Group.objects.select_for_update().filter(
#                 pk=submission.group_id
#             ).update(bonus_submissions_used=F('bonus_submissions_used') - 1)

#         submission.is_bonus_submission = False
#         submission.status = ag_models.Submission.GradingStatus.rejected
#         submission.save()


# @retry_should_recover
# def _mark_submission_as_being_graded(submission_pk):
#     with transaction.atomic():
#         submission = ag_models.Submission.objects.select_for_update().select_related(
#             'group__project').get(pk=submission_pk)
#         if submission.status == ag_models.Submission.GradingStatus.removed_from_queue:
#             print('submission {} has been removed '
#                   'from the queue'.format(submission.pk))
#             return None

#         submission.status = ag_models.Submission.GradingStatus.being_graded
#         submission.save()
#         return submission


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
