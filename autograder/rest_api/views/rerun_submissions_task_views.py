from autograder.grading_tasks.tasks.rerun_submission import rerun_submission
from autograder.core.models import submission

import celery
from django.conf import settings
from django.db import transaction
from rest_framework import mixins, response, status
from rest_framework.request import Request

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
from autograder.grading_tasks import tasks
from autograder.rest_api.schema import (AGDetailViewSchemaGenerator,
                                        AGListCreateViewSchemaGenerator, APITags, CustomViewSchema,
                                        as_content_obj)
from autograder.rest_api.views.ag_model_views import (AGModelAPIView, AGModelDetailView,
                                                      NestedModelView,
                                                      convert_django_validation_error)


class RerunSubmissionsTaskListCreateView(NestedModelView):
    schema = AGListCreateViewSchemaGenerator(
        [APITags.rerun_submissions_tasks], ag_models.RerunSubmissionsTask)

    permission_classes = [ag_permissions.is_admin()]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects.select_related('course')
    nested_field_name = 'rerun_submission_tasks'
    parent_obj_field_name = 'project'

    def get(self, *args, **kwargs):
        return self.do_list()

    @convert_django_validation_error
    def post(self, request: Request, *args, **kwargs):
        with transaction.atomic():
            project: ag_models.Project = self.get_object()

            task_args = dict(request.data)
            task_args.update({'project': project, 'creator': request.user})
            rerun_task = ag_models.RerunSubmissionsTask.objects.validate_and_create(**task_args)

            submissions = ag_models.Submission.objects.filter(group__project=project)
            if not request.data.get('rerun_all_submissions', True):
                submissions = submissions.filter(pk__in=request.data.get('submission_pks', []))
            else:
                # Only rerun for "finished" or "waiting for deferred"
                # submissions if rerun_all_submissions is True
                submissions = submissions.filter(
                    status__in=[
                        ag_models.Submission.GradingStatus.waiting_for_deferred,
                        ag_models.Submission.GradingStatus.finished_grading
                    ]
                )

            signatures = [
                rerun_submission.s(
                    submission.pk, rerun_task.pk
                ).set(queue=settings.RERUN_QUEUE_TMPL.format(project.pk))
                for submission in submissions
            ]
            from autograder.celery import app
            celery.group(signatures, app=app).apply_async()

            # ag_test_suites = project.ag_test_suites.all()
            # ag_suites_data = request.data.get('ag_test_suite_data', {})
            # rerun_all_ag_test_suites = request.data.get('rerun_all_ag_test_suites', True)
            # if not rerun_all_ag_test_suites:
            #     ag_test_suites = ag_test_suites.filter(pk__in=ag_suites_data.keys())

            # mutation_suites = project.mutation_test_suites.all()
            # rerun_all_mutation_test_suites = (
            #     request.data.get('rerun_all_mutation_test_suites', True))
            # if not rerun_all_mutation_test_suites:
            #     mutation_suites = mutation_suites.filter(
            #         pk__in=request.data.get('mutation_suite_pks', []))

            # signatures = []
            # for submission in submissions:
            #     ag_suite_sigs = [
            #         rerun_ag_test_suite.s(
            #             rerun_task.pk, submission.pk, ag_suite.pk,
            #             *ag_suites_data.get(str(ag_suite.pk), [])
            #         ).set(queue=settings.RERUN_QUEUE_TMPL.format(ag_suite.project_id))
            #         for ag_suite in ag_test_suites
            #     ]

            #     mutation_suite_sigs = [
            #         rerun_mutation_test_suite.s(
            #             rerun_task.pk, submission.pk, mutation_suite.pk
            #         ).set(queue=settings.RERUN_QUEUE_TMPL.format(mutation_suite.project_id))
            #         for mutation_suite in mutation_suites
            #     ]

            #     signatures += ag_suite_sigs
            #     signatures += mutation_suite_sigs

        # from autograder.celery import app
        # if signatures:
        #     on_finished_sig = on_submission_rerun_finished.s(
        #         project_pk=project.pk,
        #         mark_submissions_as_finished=(rerun_all_ag_test_suites
        #                                       and rerun_all_mutation_test_suites),
        #         submission_pks=[submission.pk for submission in submissions]
        #     )
        #     celery.chord(signatures, body=on_finished_sig, app=app).apply_async()

        return response.Response(rerun_task.to_dict(), status=status.HTTP_201_CREATED)


class RerunSubmissionsTaskDetailView(AGModelDetailView):
    schema = AGDetailViewSchemaGenerator([APITags.rerun_submissions_tasks])

    permission_classes = [ag_permissions.is_admin(lambda rerun_task: rerun_task.project.course)]
    model_manager = ag_models.RerunSubmissionsTask.objects

    def get(self, *args, **kwargs):
        return self.do_get()


class CancelRerunSubmissionsTaskView(AGModelAPIView):
    schema = CustomViewSchema([APITags.rerun_submissions_tasks], {
        'POST': {
            'operation_id': 'cancelRerunSubmissionsTask',
            'responses': {
                '200': {
                    'content': as_content_obj(ag_models.RerunSubmissionsTask)
                }
            }
        }
    })

    permission_classes = [ag_permissions.is_admin(lambda rerun_task: rerun_task.project.course)]
    model_manager = ag_models.RerunSubmissionsTask.objects

    @transaction.atomic
    def post(self, *args, **kwargs):
        task = self.get_object()
        task.is_cancelled = True
        task.save()

        return response.Response(task.to_dict(), status=status.HTTP_200_OK)


# @celery.shared_task(max_retries=1, acks_late=True)
# def rerun_ag_test_suite(rerun_task_pk, submission_pk, ag_test_suite_pk, *ag_test_case_pks):
#     if _rerun_is_cancelled(rerun_task_pk):
#         return

#     @retry_should_recover
#     def _rerun_ag_test_suite_impl():
#         try:
#             ag_test_suite = ag_models.AGTestSuite.objects.get(pk=ag_test_suite_pk)
#             ag_test_cases = ag_test_suite.ag_test_cases.filter(pk__in=ag_test_case_pks)
#             submission = ag_models.Submission.objects.get(pk=submission_pk)

#             # - ag_test_case_pks being empty means we want to rerun all tests.
#             # - ag_test_case_pks being non-empty and ag_test_cases being empty
#             # implies that none of the requested tests exist.
#             if not ag_test_case_pks or ag_test_cases:
#                 tasks.grade_ag_test_suite_impl(ag_test_suite, submission, *ag_test_cases)
#         except ObjectDoesNotExist:
#             # This means that the suite was deleted, so we skip it.
#             pass

#         _update_rerun_progress(rerun_task_pk)

#     try:
#         _rerun_ag_test_suite_impl()
#     except Exception as e:
#         error_msg = (
#             f'\nError rerunning ag test suite {ag_test_suite_pk} for submission {submission_pk}\n'
#             f'{str(e)} {traceback.format_exc()}\n')
#         _update_rerun_error_msg(rerun_task_pk, error_msg)


# @celery.shared_task(max_retries=1, acks_late=True)
# def rerun_mutation_test_suite(rerun_task_pk, submission_pk, mutation_test_suite_pk):
#     if _rerun_is_cancelled(rerun_task_pk):
#         return

#     @retry_should_recover
#     def _rerun_mutation_test_suite_impl():
#         try:
#             mutation_suite = ag_models.MutationTestSuite.objects.get(pk=mutation_test_suite_pk)
#             submission = ag_models.Submission.objects.get(pk=submission_pk)

#             tasks.grade_mutation_test_suite_impl(mutation_suite, submission)
#         except ObjectDoesNotExist:
#             pass

#         _update_rerun_progress(rerun_task_pk)

#     try:
#         _rerun_mutation_test_suite_impl()
#     except Exception as e:
#         error_msg = (
#             f'\nError rerunning mutation test suite {mutation_test_suite_pk} for submission '
#             f'{submission_pk}\n'
#             f'{str(e)} {traceback.format_exc()}\n'
#         )
#         _update_rerun_error_msg(rerun_task_pk, error_msg)


# @retry_should_recover
# def _rerun_is_cancelled(rerun_task_pk: int):
#     task = ag_models.RerunSubmissionsTask.objects.get(pk=rerun_task_pk)
#     return task.is_cancelled


# @retry_should_recover
# def _update_rerun_progress(rerun_task_pk: int):
#     with transaction.atomic():
#         ag_models.RerunSubmissionsTask.objects.select_for_update().filter(
#             pk=rerun_task_pk
#         ).update(num_completed_subtasks=F('num_completed_subtasks') + 1)


# @retry_should_recover
# def _update_rerun_error_msg(rerun_task_pk: int, error_msg: str):
#     with transaction.atomic():
#         ag_models.RerunSubmissionsTask.objects.select_for_update().filter(
#             pk=rerun_task_pk
#         ).update(error_msg=Concat('error_msg', Value(error_msg)))


# @celery.shared_task(queue='small_tasks', max_retries=1, acks_late=True)
# def on_submission_rerun_finished(
#     *args, project_pk: int, mark_submissions_as_finished: bool, submission_pks: List[int]
# ):
#     if mark_submissions_as_finished:
#         _mark_submissions_as_finished_after_rerun(submission_pks)

#     _clear_cached_submission_results_impl(project_pk)


# @retry_should_recover
# def _mark_submissions_as_finished_after_rerun(submission_pks: List[int]):
#     print(submission_pks)
#     with transaction.atomic():
#         ag_models.Submission.objects.select_for_update().exclude(
#             status=ag_models.Submission.GradingStatus.finished_grading
#         ).filter(
#             pk__in=submission_pks
#         ).update(status=ag_models.Submission.GradingStatus.finished_grading)


# @retry_should_recover
# def _clear_cached_submission_results_impl(project_pk: int):
#     clear_submission_results_cache(project_pk)
