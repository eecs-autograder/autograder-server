from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_composable_permissions.p import P
from drf_yasg.openapi import Parameter
from drf_yasg.utils import swagger_auto_schema
from rest_framework import decorators, mixins, response
from rest_framework import permissions
from rest_framework import status
from rest_framework.request import Request

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.core.models.copy_project_and_course import copy_project
from autograder.rest_api import tasks as api_tasks, transaction_mixins
from autograder.rest_api.views.ag_model_views import (
    AGModelGenericViewSet, convert_django_validation_error)
from autograder.rest_api.views.ag_model_views import ListCreateNestedModelViewSet
from autograder.rest_api.views.schema_generation import APITags

can_list_projects = (
    P(ag_permissions.IsReadOnly)
    & (P(ag_permissions.is_staff())
       | P(ag_permissions.is_student())
       | P(ag_permissions.is_handgrader()))
)
list_create_project_permissions = P(ag_permissions.is_admin()) | can_list_projects


class ListCreateProjectView(ListCreateNestedModelViewSet):
    serializer_class = ag_serializers.ProjectSerializer
    permission_classes = (list_create_project_permissions,)

    model_manager = ag_models.Course.objects
    to_one_field_name = 'course'
    reverse_to_one_field_name = 'projects'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.method not in permissions.SAFE_METHODS:
            return queryset

        course = self.get_object()
        if course.is_student(self.request.user):
            return queryset.filter(visible_to_students=True)

        return queryset


class CopyProjectView(AGModelGenericViewSet):
    api_tags = [APITags.projects]

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects

    serializer_class = ag_serializers.ProjectSerializer
    permission_classes = (ag_permissions.is_admin(),)

    @swagger_auto_schema(
        operation_description="""Makes a copy of the specified project and
            all of its instructor file, expected student file, test case,
            and handgrading data.
            Note that groups, submissions, and results (test case, handgrading,
            etc.) are NOT copied.
        """,
        request_body_parameters=[
            Parameter('new_project_name', in_='query', type='string', required=False),
        ]
    )
    @convert_django_validation_error
    @transaction.atomic()
    def copy_project(self, request: Request, *args, **kwargs):
        project: ag_models.Project = self.get_object()

        target_course = get_object_or_404(ag_models.Course.objects, pk=kwargs['target_course_pk'])
        if not target_course.is_admin(request.user):
            return response.Response(status=status.HTTP_403_FORBIDDEN)

        new_project_name = request.query_params.get('new_project_name', None)
        new_project = copy_project(
            project=project, target_course=target_course, new_project_name=new_project_name)

        return response.Response(status=status.HTTP_201_CREATED, data=new_project.to_dict())

    @classmethod
    def as_view(cls, actions=None, **initkwargs):
        return super().as_view(actions={'post': 'copy_project'}, **initkwargs)


@receiver(post_save, sender=ag_models.Project)
def on_project_created(sender, instance, created, **kwargs):
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        return

    if not created:
        return

    from autograder.grading_tasks.tasks import register_project_queues

    from autograder.celery import app
    register_project_queues.apply_async(
        kwargs={'project_pks': [instance.pk]}, queue='small_tasks',
        connection=app.connection())


project_detail_permissions = (
    P(ag_permissions.is_admin())
    | (P(ag_permissions.IsReadOnly) & P(ag_permissions.can_view_project()))
)


class ProjectDetailViewSet(mixins.RetrieveModelMixin,
                           transaction_mixins.TransactionPartialUpdateMixin,
                           AGModelGenericViewSet):
    model_manager = ag_models.Project.objects.select_related('course')

    serializer_class = ag_serializers.ProjectSerializer
    permission_classes = (project_detail_permissions,)

    @decorators.detail_route()
    def num_queued_submissions(self, *args, **kwargs):
        project = self.get_object()
        num_queued_submissions = ag_models.Submission.objects.filter(
            status=ag_models.Submission.GradingStatus.queued,
            group__project=project).count()

        return response.Response(data=num_queued_submissions)

    @swagger_auto_schema(auto_schema=None)
    @decorators.detail_route(
        methods=['POST'],
        permission_classes=[
            permissions.IsAuthenticated, ag_permissions.is_admin(lambda project: project.course)])
    def all_submission_files(self, *args, **kwargs):
        # IMPORTANT: Do NOT add the task to the queue before completing this transaction!
        with transaction.atomic():
            project = self.get_object()  # type: ag_models.Project
            include_staff = self.request.query_params.get('include_staff', None) == 'true'
            task = ag_models.DownloadTask.objects.validate_and_create(
                project=project, creator=self.request.user,
                download_type=ag_models.DownloadType.all_submission_files)

        from autograder.celery import app
        api_tasks.all_submission_files_task.apply_async(
            (project.pk, task.pk, include_staff), connection=app.connection())

        return response.Response(status=status.HTTP_202_ACCEPTED, data=task.to_dict())

    @swagger_auto_schema(auto_schema=None)
    @decorators.detail_route(
        methods=['POST'],
        permission_classes=[
            permissions.IsAuthenticated, ag_permissions.is_admin(lambda project: project.course)])
    def ultimate_submission_files(self, *args, **kwargs):
        # IMPORTANT: Do NOT add the task to the queue before completing this transaction!
        with transaction.atomic():
            project = self.get_object()
            include_staff = self.request.query_params.get('include_staff', None) == 'true'
            task = ag_models.DownloadTask.objects.validate_and_create(
                project=project, creator=self.request.user,
                download_type=ag_models.DownloadType.final_graded_submission_files)

        from autograder.celery import app
        api_tasks.ultimate_submission_files_task.apply_async(
            (project.pk, task.pk, include_staff), connection=app.connection())

        return response.Response(status=status.HTTP_202_ACCEPTED, data=task.to_dict())

    @swagger_auto_schema(auto_schema=None)
    @decorators.detail_route(
        methods=['POST'],
        permission_classes=[
            permissions.IsAuthenticated, ag_permissions.is_admin(lambda project: project.course)])
    def all_submission_scores(self, *args, **kwargs):
        # IMPORTANT: Do NOT add the task to the queue before completing this transaction!
        with transaction.atomic():
            project = self.get_object()  # type: ag_models.Project
            include_staff = self.request.query_params.get('include_staff', None) == 'true'
            task = ag_models.DownloadTask.objects.validate_and_create(
                project=project, creator=self.request.user,
                download_type=ag_models.DownloadType.all_scores)

        from autograder.celery import app
        api_tasks.all_submission_scores_task.apply_async(
            (project.pk, task.pk, include_staff), connection=app.connection())

        return response.Response(status=status.HTTP_202_ACCEPTED, data=task.to_dict())

    @swagger_auto_schema(auto_schema=None)
    @decorators.detail_route(
        methods=['POST'],
        permission_classes=[
            permissions.IsAuthenticated, ag_permissions.is_admin(lambda project: project.course)])
    def ultimate_submission_scores(self, *args, **kwargs):
        # IMPORTANT: Do NOT add the task to the queue before completing this transaction!
        with transaction.atomic():
            project = self.get_object()  # type: ag_models.Project
            include_staff = self.request.query_params.get('include_staff', None) == 'true'
            task = ag_models.DownloadTask.objects.validate_and_create(
                project=project, creator=self.request.user,
                download_type=ag_models.DownloadType.final_graded_submission_scores)

        from autograder.celery import app
        api_tasks.ultimate_submission_scores_task.apply_async(
            (project.pk, task.pk, include_staff), connection=app.connection())

        return response.Response(status=status.HTTP_202_ACCEPTED, data=task.to_dict())

    @swagger_auto_schema(auto_schema=None)
    @decorators.detail_route(permission_classes=[
        permissions.IsAuthenticated, ag_permissions.is_admin(lambda project: project.course)])
    def download_tasks(self, *args, **kwargs):
        project = self.get_object()
        queryset = project.download_tasks.all()
        serializer = ag_serializers.DownloadTaskSerializer(queryset, many=True)
        return response.Response(data=serializer.data)

    @decorators.detail_route(
        methods=['DELETE'],
        permission_classes=[
            permissions.IsAuthenticated,
            ag_permissions.is_admin(lambda project: project.course)]
    )
    def results_cache(self, *args, **kwargs):
        with transaction.atomic():
            project = self.get_object()

        cache.delete_pattern('project_{}_submission_normal_results_*'.format(project.pk))
        return response.Response(status=status.HTTP_204_NO_CONTENT)


class DownloadTaskDetailViewSet(mixins.RetrieveModelMixin, AGModelGenericViewSet):
    permission_classes = (ag_permissions.is_admin(lambda task: task.project.course),)
    serializer_class = ag_serializers.DownloadTaskSerializer

    model_manager = ag_models.DownloadTask.objects

    swagger_schema = None

    @decorators.detail_route()
    def result(self, *args, **kwargs):
        task = self.get_object()
        if task.progress != 100:
            return response.Response(data={'in_progress': task.progress},
                                     status=status.HTTP_400_BAD_REQUEST)
        if task.error_msg:
            return response.Response(data={'task_error': task.error_msg},
                                     status=status.HTTP_400_BAD_REQUEST)

        content_type = self._get_content_type(task.download_type)
        return FileResponse(open(task.result_filename, 'rb'), content_type=content_type)

    def _get_content_type(self, download_type: ag_models.DownloadType):
        if (download_type == ag_models.DownloadType.all_scores
                or download_type == ag_models.DownloadType.final_graded_submission_scores):
            return 'text/csv'

        if (download_type == ag_models.DownloadType.all_submission_files
                or download_type == ag_models.DownloadType.final_graded_submission_files):
            return 'application/zip'


class EditBonusSubmissionsView(AGModelGenericViewSet):
    serializer_class = ag_serializers.ProjectSerializer
    permission_classes = (ag_permissions.is_admin(),)

    model_manager = ag_models.Project.objects.select_related('course')
    pk_key = 'project_pk'

    @swagger_auto_schema(
        responses={'204': ''},
        request_body_parameters=[
            Parameter(
                'add',
                'body',
                type='integer',
                description="""How many bonus submissions to add to each group's total.
                               Mutually exclusive with "subtract"."""
            ),
            Parameter(
                'subtract',
                'body',
                type='integer',
                description="""How many bonus submissions to subtract from each group's total.
                       Mutually exclusive with "add"."""
            )
        ],
        manual_parameters=[
            Parameter(
                'group_pk',
                'query',
                type='integer',
                description="""Instead of modifying the bonus submission totals for every group,
                               only modify the group with the specified primary key."""
            )
        ]
    )
    @transaction.atomic()
    def partial_update(self, *args, **kwargs):
        project: ag_models.Project = self.get_object()

        if len(self.request.data) > 1 or len(self.request.data) == 0:
            return response.Response(
                status=status.HTTP_400_BAD_REQUEST,
                data='Please provide exactly one of: "add", "subtract".')

        queryset = project.groups
        if 'group_pk' in self.request.query_params:
            queryset = queryset.filter(pk=self.request.query_params.get('group_pk'))

        if 'add' in self.request.data:
            queryset.update(
                bonus_submissions_remaining=(
                    F('bonus_submissions_remaining') + self.request.data.get('add')))
        if 'subtract' in self.request.data:
            queryset.update(
                bonus_submissions_remaining=(
                    F('bonus_submissions_remaining') - self.request.data.get('subtract')))

        return response.Response(status=status.HTTP_204_NO_CONTENT)

    @classmethod
    def as_view(cls, actions=None, **initkwargs):
        return super().as_view(actions={'patch': 'partial_update'}, **initkwargs)
