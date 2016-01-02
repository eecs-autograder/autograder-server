import itertools
import os
import json

from django import http
from django.core import exceptions
from django.contrib.auth.models import User

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
                    "url": url_shortcuts.group_url(group_user_is_in)
                }
            }
        except exceptions.ObjectDoesNotExist:
            response = {'user_submission_group': None}

        if not project.semester.is_semester_staff(request.user):
            return http.JsonResponse(response)

        page_size = int(request.GET.get(
            'page_size', DEFAULT_SUBMISSION_GROUP_PAGE_SIZE))
        page_num = int(request.GET.get('page_num', 0))
        username_filter = request.GET.get('group_contains', None)

        if username_filter:
            try:
                queryset = User.objects.get(
                    username=username_filter
                ).groups_is_member_of.all()
            except exceptions.ObjectDoesNotExist:
                queryset = project.submission_groups.none()
        else:
            queryset = project.submission_groups.all()

        num_groups = queryset.count()

        slice_start = page_num * page_size
        slice_end = slice_start + page_size

        response.update({
            "submission_groups": [
                {
                    "members": group.member_names,
                    "url": url_shortcuts.group_url(group)
                }
                for group in queryset[slice_start:slice_end]
            ],
            "total_num_groups_matching_query": num_groups
        })

        return http.JsonResponse(response)

    def post(self, request, pk, *args, **kwargs):
        pk = int(pk)
        project = ag_models.Project.objects.get(pk=pk)
        request_content = json.loads(request.body.decode('utf-8'))

        _check_can_view(request.user, project)

        members = request_content['members']
        is_admin = project.semester.course.is_administrator(request.user)

        if is_admin:
            return self._create_group(
                project, members, check_project_group_limits=False)

        if len(members) != 1:
            raise exceptions.PermissionDenied(
                'You do not have permission to create multi-member groups '
                'directly. Please use group invitations instead.')

        if request.user.username not in members:
            raise exceptions.PermissionDenied(
                'You do not have permission to create groups that do '
                'not contain yourself.')

        return self._create_group(project, members)

    def _create_group(self, project, members, check_project_group_limits=True):
        group = ag_models.SubmissionGroup.objects.validate_and_create(
            members=members,
            project=project,
            check_project_group_limits=check_project_group_limits)

        response = {
            "members": group.member_names,
            "url": url_shortcuts.group_url(group)
        }

        return http.JsonResponse(response, status=201)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class ListAddSubmissionGroupInvitationEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        project = ag_models.Project.objects.get(pk=pk)
        _check_can_view(request.user, project)

        response = {
            "invitations_sent": [
                {
                    "users_invited": tuple(invitation.invited_usernames),
                    "url": url_shortcuts.invitation_url(invitation)
                }
                for invitation in
                request.user.group_invitations_sent.filter(project=project)
            ],
            "invitations_received": [
                {
                    "invitation_creator": (
                        invitation.invitation_creator.username),
                    "url": url_shortcuts.invitation_url(invitation)
                }
                for invitation in
                request.user.group_invitations_received.filter(project=project)
            ]
        }

        return http.JsonResponse(response)

    def post(self, request, pk, *args, **kwargs):
        pk = int(pk)
        project = ag_models.Project.objects.get(pk=pk)
        _check_can_view(request.user, project)
        request_content = json.loads(request.body.decode('utf-8'))

        to_invite = request_content['users_to_invite']

        invitation = (
            ag_models.SubmissionGroupInvitation.objects.validate_and_create(
                invitation_creator=request.user.username,
                invited_users=to_invite,
                project=project))

        response = {
            "invitation_creator": invitation.invitation_creator.username,
            "url": url_shortcuts.invitation_url(invitation)
        }

        for user in User.objects.filter(username__in=to_invite):
            user.notifications.create(
                message='{} has invited you to be in '
                        'a group for {} - {} - {}'.format(
                            request.user.username,
                            project.semester.course.name,
                            project.semester.name,
                            project.name))

        return http.JsonResponse(response, status=201)


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
