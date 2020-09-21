from autograder.core.caching import clear_submission_results_cache
import traceback

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import F, Value
from django.db.models.functions import Concat

import celery

from autograder.grading_tasks.tasks.grade_mutation_test_suite import grade_mutation_test_suite_impl
import autograder.core.models as ag_models
from autograder.utils.retry import retry_should_recover

from .exceptions import RerunCancelled
from .grade_ag_test import grade_ag_test_suite_impl
from .grade_submission import SubmissionGrader


# See autograder/rest_api/tests/test_views/test_rerun_submissions_task_views.py
# for tests that cover this module.


@celery.shared_task(acks_late=True)
def rerun_submission(submission_pk: int, rerun_task_pk: int) -> None:
    rerunner = SubmissionRerunner(submission_pk, rerun_task_pk)
    return rerunner.grade_submission()


class SubmissionRerunner(SubmissionGrader):
    def __init__(self, submission_pk: int, rerun_task_pk: int):
        super().__init__(submission_pk)
        self._rerun_task_pk = rerun_task_pk
        self._rerun_task = ag_models.RerunSubmissionsTask.objects.get(pk=rerun_task_pk)

        self._reraise_fatal_error = False

    def grade_submission_impl(self) -> None:
        try:
            super().grade_submission_impl()
        except RerunCancelled:
            pass

    @retry_should_recover
    def load_submission(self):
        """
        Loads the submission self.submission to the loaded submission
        and self.project to the project it belongs to.
        This override does NOT modify the submission in the database.
        """
        with transaction.atomic():
            self._submission = ag_models.Submission.objects.select_for_update().select_related(
                'project'
            ).get(pk=self.submission_pk)
            self._project = self.submission.project

    @retry_should_recover
    def grade_ag_test_suite(self, suite: ag_models.AGTestSuite) -> None:
        if _rerun_is_cancelled(self._rerun_task_pk):
            raise RerunCancelled

        if (suite.pk in self._rerun_task.ag_test_suite_data
                or self._rerun_task.rerun_all_ag_test_suites):
            grade_ag_test_suite_impl(
                suite,
                self.submission,
                *self._rerun_task.ag_test_suite_data.get(str(suite.pk), []),
                on_suite_setup_finished=self.save_denormalized_ag_test_suite_result,
                on_test_case_finished=self.save_denormalized_ag_test_case_result,
            )

            _update_rerun_progress(self._rerun_task_pk)

    def mark_submission_as_rejected(self) -> None:
        # When rerunning, we do NOT want to reject submissions or
        # refund bonus submissions.
        pass

    @retry_should_recover
    def grade_mutation_test_suite(self, suite: ag_models.MutationTestSuite) -> None:
        if _rerun_is_cancelled(self._rerun_task_pk):
            raise RerunCancelled

        if (suite.pk in self._rerun_task.mutation_suite_pks
                or self._rerun_task.rerun_all_mutation_test_suites):
            grade_mutation_test_suite_impl(suite, self.submission)
            _update_rerun_progress(self._rerun_task_pk)

    def send_non_deferred_tests_finished_email(self) -> None:
        # Do NOT send emails during reruns.
        pass

    def grade_deferred_suites(self) -> None:
        deferred_task_signatures = self.get_deferred_suite_task_signatures()
        from autograder.celery import app
        on_finished_sig = on_submission_rerun_finished.s(
            project_pk=self.project.pk,
            mark_submission_as_finished=(
                self._rerun_task.rerun_all_ag_test_suites
                and self._rerun_task.rerun_all_mutation_test_suites),
            submission_pk=self.submission_pk
        )
        celery.chord(deferred_task_signatures, body=on_finished_sig, app=app).apply_async()

    def mark_as_waiting_for_deferred(self):
        # Do nothing
        pass

    def get_deferred_ag_test_suite_task_signature(self, suite: ag_models.AGTestSuite):
        return rerun_deferred_ag_test_suite.s(
            self._rerun_task_pk, self.submission_pk, suite.pk,
            *self._rerun_task.ag_test_suite_data.get(str(suite.pk), [])
        ).set(queue=settings.RERUN_QUEUE_TMPL.format(self.project.pk))

    def get_deferred_mutation_suite_task_signature(self, suite: ag_models.MutationTestSuite):
        return rerun_deferred_mutation_test_suite.s(
            self._rerun_task_pk, self.submission_pk, suite.pk,
        ).set(queue=settings.RERUN_QUEUE_TMPL.format(self.project.pk))

    def record_submission_grading_error(self, error_msg: str) -> None:
        _update_rerun_error_msg(
            self._rerun_task_pk,
            f'Error rerunning submission {self.submission_pk}\n' + error_msg
        )


@retry_should_recover
def _rerun_is_cancelled(rerun_task_pk: int):
    task = ag_models.RerunSubmissionsTask.objects.get(pk=rerun_task_pk)
    return task.is_cancelled


@retry_should_recover
def _update_rerun_progress(rerun_task_pk: int):
    with transaction.atomic():
        ag_models.RerunSubmissionsTask.objects.select_for_update().filter(
            pk=rerun_task_pk
        ).update(num_completed_subtasks=F('num_completed_subtasks') + 1)


@retry_should_recover
def _update_rerun_error_msg(rerun_task_pk: int, error_msg: str):
    with transaction.atomic():
        ag_models.RerunSubmissionsTask.objects.select_for_update().filter(
            pk=rerun_task_pk
        ).update(error_msg=Concat('error_msg', Value(error_msg)))


@celery.shared_task(max_retries=1, acks_late=True)
def rerun_deferred_ag_test_suite(
    rerun_task_pk: int,
    submission_pk: int,
    ag_test_suite_pk: int,
    *ag_test_case_pks: int
) -> None:
    if _rerun_is_cancelled(rerun_task_pk):
        return

    @retry_should_recover
    def _rerun_deferred_ag_test_suite_impl():
        try:
            ag_test_suite = ag_models.AGTestSuite.objects.get(pk=ag_test_suite_pk)
            ag_test_cases = ag_test_suite.ag_test_cases.filter(pk__in=ag_test_case_pks)
            submission = ag_models.Submission.objects.get(pk=submission_pk)

            # - ag_test_case_pks being empty means we want to rerun all tests.
            # - ag_test_case_pks being non-empty and ag_test_cases being empty
            # implies that none of the requested tests exist.
            if not ag_test_case_pks or ag_test_cases:
                grade_ag_test_suite_impl(ag_test_suite, submission, *ag_test_cases)
        except ObjectDoesNotExist:
            # This means that the suite was deleted, so we skip it.
            pass

        _update_rerun_progress(rerun_task_pk)

    try:
        _rerun_deferred_ag_test_suite_impl()
    except Exception as e:
        error_msg = (
            f'\nError rerunning ag test suite {ag_test_suite_pk} for submission {submission_pk}\n'
            f'{str(e)} {traceback.format_exc()}\n')
        _update_rerun_error_msg(rerun_task_pk, error_msg)


@celery.shared_task(max_retries=1, acks_late=True)
def rerun_deferred_mutation_test_suite(rerun_task_pk, submission_pk, mutation_test_suite_pk):
    if _rerun_is_cancelled(rerun_task_pk):
        return

    @retry_should_recover
    def _rerun_deferred_mutation_test_suite_impl():
        try:
            mutation_suite = ag_models.MutationTestSuite.objects.get(pk=mutation_test_suite_pk)
            submission = ag_models.Submission.objects.get(pk=submission_pk)

            grade_mutation_test_suite_impl(mutation_suite, submission)
        except ObjectDoesNotExist:
            pass

        _update_rerun_progress(rerun_task_pk)

    try:
        _rerun_deferred_mutation_test_suite_impl()
    except Exception as e:
        error_msg = (
            f'\nError rerunning mutation test suite {mutation_test_suite_pk} for submission '
            f'{submission_pk}\n'
            f'{str(e)} {traceback.format_exc()}\n'
        )
        _update_rerun_error_msg(rerun_task_pk, error_msg)


@celery.shared_task(queue='small_tasks', max_retries=1, acks_late=True)
def on_submission_rerun_finished(
    *args, project_pk: int, mark_submission_as_finished: bool, submission_pk: int
):
    if mark_submission_as_finished:
        _mark_submission_as_finished_after_rerun(submission_pk)

    _clear_cached_submission_results_impl(project_pk)


@retry_should_recover
def _mark_submission_as_finished_after_rerun(submission_pk: int):
    print(submission_pk)
    with transaction.atomic():
        ag_models.Submission.objects.select_for_update().filter(
            pk=submission_pk
        ).exclude(
            status=ag_models.Submission.GradingStatus.finished_grading
        ).update(status=ag_models.Submission.GradingStatus.finished_grading)


@retry_should_recover
def _clear_cached_submission_results_impl(project_pk: int):
    clear_submission_results_cache(project_pk)
