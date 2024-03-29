from pathlib import Path
from typing import Optional

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_composable_permissions.p import P
from rest_framework import response, status
from rest_framework.request import Request
from rest_framework.response import Response

import autograder.core.models as ag_models
import autograder.handgrading.models as hg_models
import autograder.rest_api.permissions as ag_permissions
from autograder.core.caching import clear_submission_results_cache
from autograder.core.models.copy_project_and_course import copy_project
from autograder.handgrading.import_handgrading_rubric import import_handgrading_rubric
from autograder.rest_api import tasks as api_tasks
from autograder.rest_api.schema import (
    AGDetailViewSchemaGenerator, AGListCreateViewSchemaGenerator, APITags, CustomViewSchema,
    as_content_obj
)
from autograder.rest_api.serve_file import serve_file
from autograder.rest_api.views.ag_model_views import (
    AGModelAPIView, AGModelDetailView, NestedModelView, convert_django_validation_error,
    handle_object_does_not_exist_404
)

can_list_projects = (
    P(ag_permissions.IsReadOnly)
    & (P(ag_permissions.is_staff())
       | P(ag_permissions.is_student())
       | P(ag_permissions.is_handgrader()))
)
list_create_project_permissions = P(ag_permissions.is_admin()) | can_list_projects


class SerializeProjectMixin:
    def serialize_object(self, obj: ag_models.Project) -> dict:
        result = super().serialize_object(obj)
        if not obj.course.is_admin(self.request.user):
            result.pop('closing_time', None)

        if not obj.course.is_staff(self.request.user):
            result.pop('instructor_files', None)

        return result


class ListCreateProjectView(SerializeProjectMixin, NestedModelView):
    schema = AGListCreateViewSchemaGenerator([APITags.projects], ag_models.Project)

    permission_classes = [list_create_project_permissions]

    model_manager = ag_models.Course.objects
    nested_field_name = 'projects'
    parent_obj_field_name = 'course'

    def get(self, *args, **kwargs):
        course = self.get_object()
        projects = course.projects.all()

        if not (course.is_admin(self.request.user)
                or course.is_staff(self.request.user)
                or course.is_handgrader(self.request.user)):
            projects = projects.filter(visible_to_students=True)

        return Response([self.serialize_object(project) for project in projects])

    def post(self, *args, **kwargs):
        return self.do_create()


project_detail_permissions = (
    P(ag_permissions.is_admin())
    | (P(ag_permissions.IsReadOnly) & P(ag_permissions.can_view_project()))
)


class ProjectDetailView(SerializeProjectMixin, AGModelDetailView):
    schema = AGDetailViewSchemaGenerator([APITags.projects], ag_models.Project)

    model_manager = ag_models.Project.objects.select_related('course')
    permission_classes = [project_detail_permissions]

    def get(self, *args, **kwargs):
        return self.do_get()

    def patch(self, *args, **kwargs):
        return self.do_patch()

    @transaction.atomic
    def delete(self, *args, **kwargs):
        project = self.get_object()
        if project.ag_test_suites.count() != 0 or project.mutation_test_suites.count() != 0:
            return response.Response(
                "You cannot delete a project that still has test cases. "
                "Please delete all of this project's test cases and try again",
                status=status.HTTP_400_BAD_REQUEST
            )

        project.delete()
        return response.Response(status=status.HTTP_204_NO_CONTENT)


class CopyProjectView(AGModelAPIView):
    schema = CustomViewSchema([APITags.projects], {
        'POST': {
            'operation_id': 'copyProject',
            'request': {
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'new_project_name': {
                                    'type': 'string',
                                    'description': '''The name for the new project.
                                        Only required if the target course is the same as the
                                        one the project belongs to.
                                    '''
                                }
                            }
                        }
                    }
                }
            },
            'responses': {
                '201': {
                    'content': as_content_obj(ag_models.Project),
                    'description': ''
                }
            }
        }
    })

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects

    permission_classes = [ag_permissions.is_admin()]

    @convert_django_validation_error
    @transaction.atomic()
    def post(self, request: Request, *args, **kwargs):
        """
        Makes a copy of the specified project and
        all of its instructor file, expected student file, test case,
        and handgrading data.
        Note that groups, submissions, and results (test case, handgrading,
        etc.) are NOT copied.
        """
        project: ag_models.Project = self.get_object()

        target_course = get_object_or_404(ag_models.Course.objects, pk=kwargs['target_course_pk'])
        if not target_course.is_admin(request.user):
            return response.Response(status=status.HTTP_403_FORBIDDEN)

        new_project_name = request.data.get('new_project_name', None)
        new_project = copy_project(
            project=project, target_course=target_course, new_project_name=new_project_name)

        return response.Response(status=status.HTTP_201_CREATED, data=new_project.to_dict())


class ImportHandgradingRubricView(AGModelAPIView):
    schema = CustomViewSchema([APITags.projects, APITags.handgrading_rubrics], {
        'POST': {
            'operation_id': 'importHandgradingRubric',
            'responses': {
                '201': {
                    'content': as_content_obj(hg_models.HandgradingRubric),
                    'description': ''
                }
            }
        }
    })

    pk_key = 'project_pk'
    model_manager = ag_models.Project.objects

    permission_classes = [ag_permissions.is_admin()]

    @handle_object_does_not_exist_404
    @transaction.atomic()
    def post(self, *args, **kwargs):
        project: ag_models.Project = self.get_object()

        import_from_project = get_object_or_404(
            ag_models.Project.objects, pk=kwargs['import_from_project_pk'])

        if not import_from_project.course.is_admin(self.request.user):
            return response.Response(status=status.HTTP_403_FORBIDDEN)

        if not hasattr(import_from_project, 'handgrading_rubric'):
            return response.Response(
                status=status.HTTP_400_BAD_REQUEST,
                data=f'The project "{import_from_project.name}" has no handgrading rubric')

        import_handgrading_rubric(import_to=project, import_from=import_from_project)
        imported = hg_models.HandgradingRubric.objects.get(project=project)
        return response.Response(status=status.HTTP_201_CREATED, data=imported.to_dict())


class NumQueuedSubmissionsView(AGModelAPIView):
    schema = CustomViewSchema([APITags.projects, APITags.submissions], {
        'GET': {
            'operation_id': 'getNumQueuedSubmissions',
            'responses': {
                '200': {
                    'content': {
                        'application/json': {
                            'schema': {'type': 'integer'}
                        }
                    },
                    'description': ''
                }
            }
        }
    })

    model_manager = ag_models.Project.objects
    permission_classes = [project_detail_permissions]

    def get(self, *args, **kwargs):
        """
        The number of submissions for this project with grading status "queued".
        """
        project = self.get_object()
        num_queued_submissions = ag_models.Submission.objects.filter(
            status=ag_models.Submission.GradingStatus.queued,
            group__project=project).count()

        return response.Response(data=num_queued_submissions)


class _DownloadViewBase(AGModelAPIView):
    """
    Base class for project scores and submitted files views.
    """
    schema = None

    download_type: Optional[ag_models.DownloadType] = None
    celery_task_func = None

    model_manager = ag_models.Project.objects
    permission_classes = [ag_permissions.is_admin()]

    def post(self, *args, **kwargs):
        # IMPORTANT: Do NOT add the task to the queue before completing this transaction!
        with transaction.atomic():
            project = self.get_object()  # type: ag_models.Project
            include_staff = self.request.query_params.get('include_staff', None) == 'true'
            include_pending_extensions = (
                self.request.query_params.get('include_pending_extensions', None) == 'true')
            task = ag_models.DownloadTask.objects.validate_and_create(
                project=project,
                creator=self.request.user,
                download_type=self.download_type,
                include_pending_extensions=include_pending_extensions)

        from autograder.celery import app
        self.celery_task_func.apply_async(
            (project.pk, task.pk, include_staff), connection=app.connection())

        return response.Response(status=status.HTTP_202_ACCEPTED, data=task.to_dict())


class AllSubmittedFilesTaskView(_DownloadViewBase):
    download_type = ag_models.DownloadType.all_submission_files
    celery_task_func = api_tasks.all_submission_files_task


class UltimateSubmissionSubmittedFilesTaskView(_DownloadViewBase):
    download_type = ag_models.DownloadType.final_graded_submission_files
    celery_task_func = api_tasks.ultimate_submission_files_task


class AllScoresTaskView(_DownloadViewBase):
    download_type = ag_models.DownloadType.all_scores
    celery_task_func = api_tasks.all_submission_scores_task


class UltimateSubmissionScoresTaskView(_DownloadViewBase):
    download_type = ag_models.DownloadType.final_graded_submission_scores
    celery_task_func = api_tasks.ultimate_submission_scores_task


class ListDownloadTasksView(NestedModelView):
    schema = None

    model_manager = ag_models.Project.objects
    nested_field_name = 'download_tasks'
    permission_classes = [ag_permissions.is_admin()]

    def get(self, *args, **kwargs):
        return self.do_list()


class ClearResultsCacheView(AGModelAPIView):
    schema = CustomViewSchema([APITags.projects], {
        'DELETE': {'deprecated': True, 'operation_id': 'clearSubmissionResultsCache'}
    })

    model_manager = ag_models.Project.objects
    permission_classes = [ag_permissions.is_admin()]

    def delete(self, *args, **kwargs):
        """
        DEPRECATED. Clears cached "normal" feedback submission results.
        """
        with transaction.atomic():
            project = self.get_object()

        clear_submission_results_cache(project.pk)
        return response.Response(status=status.HTTP_204_NO_CONTENT)


class DownloadTaskDetailView(AGModelDetailView):
    schema = None

    model_manager = ag_models.DownloadTask.objects
    permission_classes = [ag_permissions.is_admin(lambda task: task.project.course)]

    def get(self, *args, **kwargs):
        return self.do_get()


class DownloadTaskResultView(AGModelAPIView):
    schema = None

    model_manager = ag_models.DownloadTask.objects
    permission_classes = [ag_permissions.is_admin(lambda task: task.project.course)]

    def get(self, *args, **kwargs):
        task = self.get_object()
        if task.progress != 100:
            return response.Response(data={'in_progress': task.progress},
                                     status=status.HTTP_400_BAD_REQUEST)
        if task.error_msg:
            return response.Response(data={'task_error': task.error_msg},
                                     status=status.HTTP_400_BAD_REQUEST)

        content_type = self._get_content_type(task.download_type)
        return serve_file(Path(task.result_filename), content_type=content_type)

    def _get_content_type(self, download_type: ag_models.DownloadType):
        if (download_type == ag_models.DownloadType.all_scores
                or download_type == ag_models.DownloadType.final_graded_submission_scores):
            return 'text/csv'

        if (download_type == ag_models.DownloadType.all_submission_files
                or download_type == ag_models.DownloadType.final_graded_submission_files):
            return 'application/zip'
