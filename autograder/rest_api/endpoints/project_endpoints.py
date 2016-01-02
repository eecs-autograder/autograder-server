import itertools
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

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


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
                    "url": url_shortcuts.project_file_url(project, file_.name)
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
                    'url': url_shortcuts.project_file_url(project, file_.name)
                })
            except exceptions.ValidationError as e:
                failure.append({
                    'filename': os.path.basename(file_.name),
                    'error_message': str(e)
                })

        response = {'success': success, 'failure': failure}

        return http.JsonResponse(response)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class GetUpdateDeleteProjectFileEndpoint(EndpointBase):
    def get(self, request, pk, filename, *args, **kwargs):
        pk = int(pk)
        project = ag_models.Project.objects.get(pk=pk)
        _check_is_staff(request.user, project)

        file_ = project.get_file(filename)

        response = {
            "type": "project_file",
            "filename": file_.name,
            "size": file_.size,
            "content": str(file_.read()),
            "urls": {
                "self": url_shortcuts.project_file_url(project, file_.name),
                "project": url_shortcuts.project_url(project)
            }
        }

        return http.JsonResponse(response)

    def patch(self, request, pk, filename, *args, **kwargs):
        pk = int(pk)
        project = ag_models.Project.objects.get(pk=pk)
        _check_can_edit(request.user, project)
        request_content = json.loads(request.body.decode('utf-8'))

        if 'content' in request_content:
            project.update_project_file(filename, request_content['content'])

        response = {
            'size': project.get_file(filename).size
        }

        return http.JsonResponse(response)

    def delete(self, request, pk, filename, *args, **kwargs):
        pk = int(pk)
        project = ag_models.Project.objects.get(pk=pk)
        _check_can_edit(request.user, project)

        project.remove_project_file(filename)

        return http.HttpResponse(status=204)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddAutograderTestCaseEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        project = ag_models.Project.objects.get(pk=pk)
        _check_is_staff(request.user, project)

        response = {
            "autograder_test_cases": [
                {
                    "name": ag_test.name,
                    "url": url_shortcuts.ag_test_url(ag_test)
                }
                for ag_test in project.autograder_test_cases.all()
            ]
        }

        return http.JsonResponse(response)

    def post(self, request, pk, *args, **kwargs):
        pk = int(pk)
        project = ag_models.Project.objects.get(pk=pk)
        _check_can_edit(request.user, project)
        request_content = json.loads(request.body.decode('utf-8'))
        type_str = request_content.pop('type')

        ag_test = ag_models.AutograderTestCaseFactory.validate_and_create(
            type_str, project=project, **request_content)

        response = {
            "name": ag_test.name,
            "type": ag_test.get_type_str(),
            "url": url_shortcuts.ag_test_url(ag_test)
        }

        return http.JsonResponse(response, status=201)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddStudentTestSuiteEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        project = ag_models.Project.objects.get(pk=pk)
        _check_is_staff(request.user, project)

        response = {
            "student_test_suites": [
                {
                    "name": suite.name,
                    "url": url_shortcuts.suite_url(suite)
                }
                for suite in project.student_test_suites.all()
            ]
        }

        return http.JsonResponse(response)

    def post(self, request, pk, *args, **kwargs):
        pk = int(pk)
        project = ag_models.Project.objects.get(pk=pk)
        _check_can_edit(request.user, project)
        request_content = json.loads(request.body.decode('utf-8'))
        type_str = request_content.pop('type')

        suite = ag_models.StudentTestSuiteFactory.validate_and_create(
            type_str, project=project, **request_content)

        response = {
            "name": suite.name,
            "type": suite.get_type_str(),
            "url": url_shortcuts.suite_url(suite)
        }

        return http.JsonResponse(response, status=201)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddSubmissionGroupEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        project = ag_models.Project.objects.get(pk=pk)
        _check_can_view(request.user, project)

        try:
            group_user_is_in = request.user.groups_is_member_of.get(
                project=project)
            response = {
                "user_submission_group": {
                    "members": group_user_is_in.member_names,
                    "url": "/submission_groups/<group id>/"
                },
            }
        except exceptions.ObjectDoesNotExist:
            response = {'user_submission_group': None}

        if not project.semester.is_semester_staff(request.user):
            return http.JsonResponse(response)

        page_size = request.GET.get(
            'page_size', DEFAULT_SUBMISSION_GROUP_PAGE_SIZE)
        page_num = request.GET.get('page_num', 0)
        username_filter = request.GET.get('username_filters', None)

        # if username_filter

        if page_size < 1:
            raise exceptions.ValidationError('page_size must be at least 1')

        if page_num < 0:
            raise exceptions.ValidationError('page_num may not be negative')

        total_num_groups = project.submission_groups.count()

        slice_start = page_num * page_size
        slice_end = min(slice_start + page_size, total_num_groups)

        # if username_filters:
        #     queryset = []
        #     for username in username_filters:
        #         try:
        #             group = User.objects.get(
        #                 username=username
        #             ).groups_is_member_of.get(project=project)
        #             queryset.append()
        #         except exceptions.ObjectDoesNotExist:
        #             continue

        #     # queryset = itertools.chain.from_iterable(
        #     #     User.objects.filter()


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


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
