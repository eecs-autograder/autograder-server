import celery
from django.db import transaction
from rest_framework import generics
from rest_framework import mixins
from rest_framework import response
from rest_framework import status
from rest_framework.request import Request

from autograder.grading_tasks import tasks
from autograder.grading_tasks.tasks.utils import retry_should_recover
from autograder.rest_api.views.ag_model_views import (
    ListCreateNestedModelView, AGModelGenericViewSet)
import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
import autograder.rest_api.permissions as ag_permissions


class RerunSubmissionsTaskListCreateView(ListCreateNestedModelView):
    serializer_class = ag_serializers.RerunSubmissionTaskSerializer
    permission_classes = [ag_permissions.is_admin(lambda project: project.course)]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')
    foreign_key_field_name = 'project'
    reverse_foreign_key_field_name = 'rerun_submission_tasks'

    @transaction.atomic()
    def create(self, request: Request, *args, **kwargs):
        project = self.get_object()  # type: ag_models.Project

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid()
        rerun_task = serializer.save(
            project=project, creator=request.user
        )  # type: ag_models.RerunSubmissionsTask

        submissions = ag_models.Submission.objects.filter(submission_group__project=project)
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
                rerun_ag_test_suite.s(submission.pk, ag_suite.pk,
                                      *ag_suites_data.get(str(ag_suite.pk), []))
                for ag_suite in ag_test_suites]

            student_suite_sigs = [
                rerun_student_test_suite.s(submission.pk, student_suite.pk)
                for student_suite in student_suites]

            signatures += ag_suite_sigs
            signatures += student_suite_sigs

        if not signatures:
            rerun_task.is_finished = True
            rerun_task.save()
            return response.Response(self.get_serializer(rerun_task).data,
                                     status=status.HTTP_201_CREATED)

        callback = mark_rerun_submissions_as_finished.s(
            rerun_task.pk
        ).on_error(mark_rerun_submissions_as_error.s(rerun_task.pk))

        task = celery.chord(signatures)(callback)
        rerun_task.celery_result_id = task.id
        rerun_task.save()

        return response.Response(self.get_serializer(rerun_task).data,
                                 status=status.HTTP_201_CREATED)


class RerunSubmissionsTaskDetailVewSet(mixins.RetrieveModelMixin,
                                       AGModelGenericViewSet):
    permission_classes = [ag_permissions.is_admin(lambda rerun_task: rerun_task.project.course)]
    serializer_class = ag_serializers.RerunSubmissionTaskSerializer

    model_manager = ag_models.RerunSubmissionsTask.objects


@celery.shared_task(queue='rerun', max_retries=1, acks_late=True)
def rerun_ag_test_suite(submission_pk, ag_test_suite_pk, *ag_test_case_pks):
    @retry_should_recover
    def _rerun_ag_test_suite_impl():
        ag_test_suite = ag_models.AGTestSuite.objects.get(pk=ag_test_suite_pk)
        ag_test_cases = ag_test_suite.ag_test_cases.filter(pk__in=ag_test_case_pks)
        submission = ag_models.Submission.objects.get(pk=submission_pk)

        tasks.grade_ag_test_suite_impl(ag_test_suite, submission, *ag_test_cases)

    _rerun_ag_test_suite_impl()


@celery.shared_task(queue='rerun', max_retries=1, acks_late=True)
def rerun_student_test_suite(submission_pk, student_test_suite_pk):
    @retry_should_recover
    def _rerun_student_test_suite_impl():
        student_suite = ag_models.StudentTestSuite.objects.get(pk=student_test_suite_pk)
        submission = ag_models.Submission.objects.get(pk=submission_pk)
        tasks.grade_student_test_suite_impl(student_suite, submission)

    _rerun_student_test_suite_impl()


@celery.shared_task(queue='small_tasks', acks_late=True)
def mark_rerun_submissions_as_finished(chord_results, rerun_submissions_task_pk):
    with transaction.atomic():
        ag_models.RerunSubmissionsTask.objects.select_for_update().filter(
            pk=rerun_submissions_task_pk
        ).update(is_finished=True)


@celery.shared_task(queue='small_tasks', acks_late=True)
def mark_rerun_submissions_as_error(rerun_submissions_task_pk, request, exc, traceback):
    with transaction.atomic():
        ag_models.RerunSubmissionsTask.objects.select_for_update().filter(
            pk=rerun_submissions_task_pk
        ).update(is_finished=True, error_msg=str(exc) + '\n' + str(traceback))
