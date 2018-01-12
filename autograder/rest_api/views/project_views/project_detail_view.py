from django.db import transaction
from django.http import FileResponse

from rest_framework import decorators, exceptions, mixins, permissions, response, viewsets
from rest_framework import status

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins
from autograder.rest_api.views.ag_model_views import AGModelGenericViewSet
from autograder.rest_api import tasks as api_tasks
from .permissions import ProjectPermissions
from ..load_object_mixin import build_load_object_mixin


class ProjectDetailViewSet(build_load_object_mixin(ag_models.Project),
                           mixins.RetrieveModelMixin,
                           transaction_mixins.TransactionUpdateMixin,
                           viewsets.GenericViewSet):
    serializer_class = ag_serializers.ProjectSerializer
    permission_classes = (permissions.IsAuthenticated, ProjectPermissions)

    @decorators.detail_route()
    def num_queued_submissions(self, *args, **kwargs):
        project = self.get_object()
        num_queued_submissions = ag_models.Submission.objects.filter(
            status=ag_models.Submission.GradingStatus.queued,
            submission_group__project=project).count()

        return response.Response(data=num_queued_submissions)

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

    @decorators.detail_route(permission_classes=[
        permissions.IsAuthenticated, ag_permissions.is_admin(lambda project: project.course)])
    def download_tasks(self, *args, **kwargs):
        project = self.get_object()
        queryset = project.download_tasks.all()
        serializer = ag_serializers.DownloadTaskSerializer(queryset, many=True)
        return response.Response(data=serializer.data)


class UserCreatedTask(permissions.BasePermission):
    def has_object_permission(self, request, view, obj: ag_models.DownloadTask):
        return request.user == obj.creator


class DownloadTaskDetailViewSet(mixins.RetrieveModelMixin, AGModelGenericViewSet):
    permission_classes = (ag_permissions.is_admin(lambda task: task.project.course),
                          UserCreatedTask)
    serializer_class = ag_serializers.DownloadTaskSerializer

    model_manager = ag_models.DownloadTask.objects

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
        if (download_type == ag_models.DownloadType.all_scores or
                download_type == ag_models.DownloadType.final_graded_submission_scores):
            return 'text/csv'

        if (download_type == ag_models.DownloadType.all_submission_files or
                download_type == ag_models.DownloadType.final_graded_submission_files):
            return 'application/zip'

