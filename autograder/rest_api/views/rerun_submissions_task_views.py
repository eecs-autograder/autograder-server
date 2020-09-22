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
            print(f'{rerun_task.total_num_subtasks=}')

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
