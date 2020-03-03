import traceback

import celery
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import F
from django.db.models import Value
from django.db.models.functions import Concat

from rest_framework import mixins, response, status
from rest_framework.decorators import detail_route
from rest_framework.request import Request

from autograder.core.caching import clear_submission_results_cache
from autograder.grading_tasks import tasks
from autograder.grading_tasks.tasks.utils import retry_should_recover
from autograder.rest_api.views.ag_model_views import (
    ListCreateNestedModelViewSet, AGModelGenericViewSet)
import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
import autograder.rest_api.permissions as ag_permissions


class RerunSubmissionsTaskListCreateView(ListCreateNestedModelViewSet):
    serializer_class = ag_serializers.RerunSubmissionTaskSerializer
    permission_classes = [ag_permissions.is_admin(lambda project: project.course)]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')
    to_one_field_name = 'project'
    reverse_to_one_field_name = 'rerun_submission_tasks'

    @transaction.atomic()
    def create(self, request: Request, *args, **kwargs):
        project = self.get_object()  # type: ag_models.Project

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid()
        rerun_task = serializer.save(
            project=project, creator=request.user
        )  # type: ag_models.RerunSubmissionsTask

        submissions = ag_models.Submission.objects.filter(group__project=project)
        if not request.data.get('rerun_all_submissions', True):
            submissions = submissions.filter(pk__in=request.data.get('submission_pks', []))

        ag_test_suites = project.ag_test_suites.all()
        ag_suites_data = request.data.get('ag_test_suite_data', {})
        if not request.data.get('rerun_all_ag_test_suites', True):
            ag_test_suites = ag_test_suites.filter(pk__in=ag_suites_data.keys())

        student_suites = project.student_test_suites.all()
        if not request.data.get('rerun_all_student_test_suites', True):
            student_suites = student_suites.filter(
                pk__in=request.data.get('student_suite_pks', []))

        signatures = []
        for submission in submissions:
            ag_suite_sigs = [
                rerun_ag_test_suite.s(rerun_task.pk, submission.pk, ag_suite.pk,
                                      *ag_suites_data.get(str(ag_suite.pk), []))
                for ag_suite in ag_test_suites]

            student_suite_sigs = [
                rerun_student_test_suite.s(rerun_task.pk, submission.pk, student_suite.pk)
                for student_suite in student_suites]

            signatures += ag_suite_sigs
            signatures += student_suite_sigs

        from autograder.celery import app
        if signatures:
            clear_cache_sig = clear_cached_submission_results.s(project.pk)

            chord_result = celery.chord(signatures, body=clear_cache_sig, app=app).apply_async()

            # In case any of the subtasks finish before we reach this line
            # (definitely happens in testing), make sure we don't
            # accidentally overwrite the task's progress or error messages.
            ag_models.RerunSubmissionsTask.objects.filter(
                pk=rerun_task.pk
            ).update(celery_group_result_id=chord_result.id)

        return response.Response(self.get_serializer(rerun_task).data,
                                 status=status.HTTP_201_CREATED)


class RerunSubmissionsTaskDetailVewSet(mixins.RetrieveModelMixin,
                                       AGModelGenericViewSet):
    permission_classes = [ag_permissions.is_admin(lambda rerun_task: rerun_task.project.course)]
    serializer_class = ag_serializers.RerunSubmissionTaskSerializer

    model_manager = ag_models.RerunSubmissionsTask.objects

    @transaction.atomic
    @detail_route(methods=['POST'])
    def cancel(self, *args, **kwargs):
        task = self.get_object()
        task.is_cancelled = True
        task.save()

        return response.Response(self.get_serializer(task).data, status=status.HTTP_200_OK)


@celery.shared_task(queue='rerun', max_retries=1, acks_late=True)
def rerun_ag_test_suite(rerun_task_pk, submission_pk, ag_test_suite_pk, *ag_test_case_pks):
    if _rerun_is_cancelled(rerun_task_pk):
        return

    @retry_should_recover
    def _rerun_ag_test_suite_impl():
        try:
            ag_test_suite = ag_models.AGTestSuite.objects.get(pk=ag_test_suite_pk)
            ag_test_cases = ag_test_suite.ag_test_cases.filter(pk__in=ag_test_case_pks)
            submission = ag_models.Submission.objects.get(pk=submission_pk)

            # - ag_test_case_pks being empty means we want to rerun all tests.
            # - ag_test_case_pks being non-empty and ag_test_cases being empty
            # implies that none of the requested tests exist.
            if not ag_test_case_pks or ag_test_cases:
                tasks.grade_ag_test_suite_impl(ag_test_suite, submission, *ag_test_cases)
        except ObjectDoesNotExist:
            # This means that the suite was deleted, so we skip it.
            pass

        _update_rerun_progress(rerun_task_pk)

    try:
        _rerun_ag_test_suite_impl()
    except Exception as e:
        error_msg = (
            f'\nError rerunning ag test suite {ag_test_suite_pk} for submission {submission_pk}\n'
            f'{str(e)} {traceback.format_exc()}\n')
        _update_rerun_error_msg(rerun_task_pk, error_msg)


@celery.shared_task(queue='rerun', max_retries=1, acks_late=True)
def rerun_student_test_suite(rerun_task_pk, submission_pk, student_test_suite_pk):
    if _rerun_is_cancelled(rerun_task_pk):
        return

    @retry_should_recover
    def _rerun_student_test_suite_impl():
        try:
            student_suite = ag_models.StudentTestSuite.objects.get(pk=student_test_suite_pk)
            submission = ag_models.Submission.objects.get(pk=submission_pk)

            tasks.grade_student_test_suite_impl(student_suite, submission)
        except ObjectDoesNotExist:
            pass

        _update_rerun_progress(rerun_task_pk)

    try:
        _rerun_student_test_suite_impl()
    except Exception as e:
        error_msg = (
            f'\nError rerunning student test suite {student_test_suite_pk} for submission '
            f'{submission_pk}\n'
            f'{str(e)} {traceback.format_exc()}\n'
        )
        _update_rerun_error_msg(rerun_task_pk, error_msg)


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


@celery.shared_task(queue='small_tasks', max_retries=1, acks_late=True)
def clear_cached_submission_results(result, project_pk: int):
    @retry_should_recover
    def _clear_cached_submission_results_impl():
        clear_submission_results_cache(project_pk)

    _clear_cached_submission_results_impl()
