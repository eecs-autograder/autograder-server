import os
import json
from django import http
from django.core import exceptions

from .endpoint_base import EndpointBase

from autograder.core import models as ag_models
from autograder.rest_api import url_shortcuts

DEFAULT_SUBMISSION_GROUP_PAGE_SIZE = 20


class GetUpdateProjectEndpoint(EndpointBase):
    _EDITABLE_FIELDS = [
        'name',
        'visible_to_students',
        'closing_time',
        'disallow_student_submissions',
        'allow_submissions_from_non_enrolled_students',
        'min_group_size',
        'max_group_size',
        'required_student_files',
        'expected_student_file_patterns'
    ]

    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        project = ag_models.Project.objects.get(pk=pk)
        _check_can_view(request.user, project)

        response = {
            "type": "project",
            "id": pk,
            "name": project.name,
            "visible_to_students": project.visible_to_students,
            "closing_time": project.closing_time,
            "disallow_student_submissions": project.disallow_student_submissions,
            "allow_submissions_from_non_enrolled_students": project.allow_submissions_from_non_enrolled_students,
            "min_group_size": project.min_group_size,
            "max_group_size": project.max_group_size,
            "required_student_files": project.required_student_files,
            "expected_student_file_patterns": [
                {
                    "pattern": obj.pattern,
                    "min_num_matches": obj.min_num_matches,
                    "max_num_matches": obj.max_num_matches
                }
                for obj in project.expected_student_file_patterns
            ],
            "urls": {
                "self": url_shortcuts.project_url(project),
                "semester": url_shortcuts.semester_url(project.semester),
                "uploaded_files": url_shortcuts.project_files_url(project),
            }
        }

        return http.JsonResponse(response)

    def patch(self, request, pk, *args, **kwargs):
        pk = int(pk)
        project = ag_models.Project.objects.get(pk=pk)
        _check_can_edit(request.user, project)
        request_content = json.loads(request.body.decode('utf-8'))

        expected_patterns = request_content.pop(
            'expected_student_file_patterns', None)

        if expected_patterns is not None:
            project.expected_student_file_patterns = [
                ag_models.Project.FilePatternTuple(**obj)
                for obj in expected_patterns
            ]

        for field in self._EDITABLE_FIELDS:
            if field in request_content:
                setattr(project, field, request_content[field])

        project.validate_and_save()

        return http.HttpResponse(status=204)


class ListAddProjectFileEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        project = ag_models.Project.objects.get(pk=pk)
        _check_is_staff(request.user, project)

        response = {
            "uploaded_files": [
                {
                    "filename": os.path.basename(file_.name),
                    "size": file_.size,
                    "url": url_shortcuts.project_file_url(
                        project, os.path.basename(file_.name))
                }
                for file_ in project.get_project_files()
            ]
        }

        return http.JsonResponse(response)

    def post(self, request, pk, *args, **kwargs):
        pk = int(pk)
        project = ag_models.Project.objects.get(pk=pk)
        _check_can_edit(request.user, project)

        success = []
        failure = []

        for file_ in request.FILES.getlist('files'):
            try:
                project.add_project_file(file_)
                success.append({
                    'filename': os.path.basename(file_.name),
                    'size': file_.size,
                    'url': url_shortcuts.project_file_url(
                        project, os.path.basename(file_.name))
                })
            except exceptions.ValidationError as e:
                failure.append({
                    'filename': os.path.basename(file_.name),
                    'error_message': str(e)
                })

        response = {'success': success, 'failure': failure}

        return http.JsonResponse(response)


class GetUpdateDeleteProjectFileEndpoint(EndpointBase):
    pass


class ListAddAutograderTestCaseEndpoint(EndpointBase):
    pass


class ListAddStudentTestSuiteEndpoint(EndpointBase):
    pass


class ListAddSubmissionGroupEndpoint(EndpointBase):
    pass


class ListAddSubmissionGroupInvitationEndpoint(EndpointBase):
    pass


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


def _check_can_view(user, project):
    if project.semester.is_semester_staff(user):
        return

    if not project.visible_to_students:
        raise exceptions.PermissionDenied()

    if project.semester.is_enrolled_student(user):
        return

    if not project.allow_submissions_from_non_enrolled_students:
        raise exceptions.PermissionDenied()


def _check_is_staff(user, project):
    if not project.semester.is_semester_staff(user):
        raise exceptions.PermissionDenied()


def _check_can_edit(user, project):
    if not project.semester.course.is_administrator(user):
        raise exceptions.PermissionDenied()
