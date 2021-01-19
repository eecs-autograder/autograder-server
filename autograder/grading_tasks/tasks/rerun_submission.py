from autograder.core.submission_feedback import update_denormalized_ag_test_results
import traceback

import celery
from django.db import transaction
from django.db.models import F, Value
from django.db.models.functions import Concat

import autograder.core.models as ag_models
from autograder.core.caching import clear_submission_results_cache
from autograder.grading_tasks.tasks.grade_mutation_test_suite import grade_mutation_test_suite_impl
from autograder.grading_tasks.tasks.utils import load_queryset_with_retry
from autograder.utils.retry import retry_should_recover

from .exceptions import RerunCancelled
from .grade_ag_test import grade_ag_test_suite_impl

# See autograder/rest_api/tests/test_views/test_rerun_submissions_task_views.py
# for tests that cover this module.


@celery.shared_task(acks_late=True)
def rerun_submission(submission_pk: int, rerun_task_pk: int) -> None:
    rerunner = SubmissionRerunner(submission_pk, rerun_task_pk)
    return rerunner.rerun_submission()


class SubmissionRerunner:
    def __init__(self, submission_pk: int, rerun_task_pk: int):
        self._submission_pk = submission_pk
        self._submission = None
        self._group = None
        self._project = None

        self._rerun_task_pk = rerun_task_pk
        self._rerun_task = None

    @property
    def submission(self) -> ag_models.Submission:
        assert self._submission is not None
        return self._submission

    @property
    def group(self) -> ag_models.Group:
        assert self._group is not None
        return self._group

    @property
    def project(self) -> ag_models.Project:
        assert self._project is not None
        return self._project

    @property
    def rerun_task(self) -> ag_models.RerunSubmissionsTask:
        assert self._rerun_task is not None
        return self._rerun_task

    def rerun_submission(self) -> None:
        try:
            self.load_data()
            self.rerun_suites()
            self.mark_as_finished()
        except RerunCancelled:
            pass
        except Exception as e:
            print('Error grading submission')
            traceback.print_exc()
            self.record_submission_grading_error(traceback.format_exc())

    @retry_should_recover
    def load_data(self):
        """
        Loads the rerun task, submission, group, and project requested.
        """
        with transaction.atomic():
            self._rerun_task = ag_models.RerunSubmissionsTask.objects.get(pk=self._rerun_task_pk)
            print(f'{self._rerun_task.ag_test_suite_data=}')
            self._submission = ag_models.Submission.objects.select_for_update().select_related(
                'project', 'group'
            ).get(pk=self._submission_pk)
            self._group = self._submission.group
            self._project = self.submission.project

    def rerun_suites(self) -> None:
        for suite in load_queryset_with_retry(self.project.ag_test_suites.filter()):
            self.grade_ag_test_suite(suite)

        for suite in load_queryset_with_retry(self.project.mutation_test_suites.filter()):
            self.grade_mutation_test_suite(suite)

    @retry_should_recover
    def grade_ag_test_suite(self, suite: ag_models.AGTestSuite) -> None:
        if self.rerun_is_cancelled():
            raise RerunCancelled

        if (str(suite.pk) in self.rerun_task.ag_test_suite_data
                or self.rerun_task.rerun_all_ag_test_suites):
            grade_ag_test_suite_impl(
                suite,
                self.submission,
                self.group,
                *self.rerun_task.ag_test_suite_data.get(str(suite.pk), []),
            )
            self.update_rerun_progress()
            self._update_denormalized_ag_test_results()

    @retry_should_recover
    def _update_denormalized_ag_test_results(self) -> None:
        update_denormalized_ag_test_results(self._submission_pk)

    @retry_should_recover
    def grade_mutation_test_suite(self, suite: ag_models.MutationTestSuite) -> None:
        if self.rerun_is_cancelled():
            raise RerunCancelled

        if (suite.pk in self.rerun_task.mutation_suite_pks
                or self.rerun_task.rerun_all_mutation_test_suites):
            grade_mutation_test_suite_impl(suite, self.submission)
            self.update_rerun_progress()

    @retry_should_recover
    def rerun_is_cancelled(self) -> bool:
        self.rerun_task.refresh_from_db()
        return self.rerun_task.is_cancelled

    @retry_should_recover
    def update_rerun_progress(self) -> None:
        with transaction.atomic():
            ag_models.RerunSubmissionsTask.objects.select_for_update().filter(
                pk=self._rerun_task_pk
            ).update(num_completed_subtasks=F('num_completed_subtasks') + 1)

    def mark_as_finished(self) -> None:
        if (self.rerun_task.rerun_all_ag_test_suites
                and self.rerun_task.rerun_all_mutation_test_suites):
            _mark_submission_as_finished_after_rerun(self._submission_pk)

        _clear_cached_submission_results_impl(self.project.pk)

    @retry_should_recover
    def record_submission_grading_error(self, error_msg: str) -> None:
        with transaction.atomic():
            ag_models.RerunSubmissionsTask.objects.select_for_update().filter(
                pk=self._rerun_task_pk
            ).update(
                error_msg=Concat(
                    'error_msg',
                    Value(f'Error rerunning submission {self._submission_pk}\n' + error_msg)
                )
            )


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
