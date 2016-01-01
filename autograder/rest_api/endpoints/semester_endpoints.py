import json

from django.contrib.auth.models import User
from django import http
from django.core.urlresolvers import reverse
from django.core import exceptions

from .endpoint_base import EndpointBase

from autograder.core import models as ag_models
from autograder.rest_api import url_shortcuts

DEFAULT_ENROLLED_STUDENT_PAGE_SIZE = 20


class GetUpdateSemesterEndpoint(EndpointBase):
    _EDITABLE_FIELDS = ['name']

    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)

        semester = ag_models.Semester.objects.get(pk=pk)
        response = {
            "type": "semester",
            "id": pk,
            "name": semester.name,
            "urls": {
                "self": url_shortcuts.semester_url(semester),
                "course": url_shortcuts.course_url(semester.course),
                "projects": url_shortcuts.projects_url(semester)
            }
        }
        if semester.is_semester_staff(request.user):
            response['urls'].update({
                "staff": url_shortcuts.semester_staff_url(semester),
                "enrolled_students": (
                    url_shortcuts.semester_enrolled_url(semester)),
            })
        elif not semester.is_enrolled_student(request.user):
            raise exceptions.PermissionDenied()

        return http.JsonResponse(response)

    def patch(self, request, pk, *args, **kwargs):
        request_content = json.loads(request.body.decode('utf-8'))

        pk = int(pk)
        semester = ag_models.Semester.objects.get(pk=pk)
        _check_is_admin(request.user, semester)

        response = {}

        for field in self._EDITABLE_FIELDS:
            if field in request_content:
                setattr(semester, field, request_content[field])
                response[field] = request_content[field]

        semester.validate_and_save()

        return http.JsonResponse(response)


class ListAddRemoveSemesterStaffEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)

        semester = ag_models.Semester.objects.get(pk=pk)
        _check_is_staff(request.user, semester)

        response = {
            'staff': tuple(semester.semester_staff_names)
        }

        return http.JsonResponse(response)

    def post(self, request, pk, *args, **kwargs):
        pk = int(pk)

        semester = ag_models.Semester.objects.get(pk=pk)
        _check_is_admin(request.user, semester)

        request_content = json.loads(request.body.decode('utf-8'))
        users = [
            User.objects.get_or_create(username=username)[0]
            for username in request_content['staff']
        ]

        semester.staff.add(*users)

        response = {
            'staff': tuple(semester.semester_staff_names)
        }

        return http.JsonResponse(response, status=201)

    def delete(self, request, pk, *args, **kwargs):
        pk = int(pk)

        semester = ag_models.Semester.objects.get(pk=pk)
        _check_is_admin(request.user, semester)

        request_content = json.loads(request.body.decode('utf-8'))
        users = User.objects.filter(
            username__in=request_content['staff'])

        semester.staff.remove(*users)

        response = {
            'staff': tuple(semester.semester_staff_names)
        }

        return http.JsonResponse(response, status=200)


class ListAddUpdateRemoveEnrolledStudentsEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)

        semester = ag_models.Semester.objects.get(pk=pk)
        _check_is_enrolled_or_staff(request.user, semester)

        page_size = int(request.GET.get(
            'page_size', DEFAULT_ENROLLED_STUDENT_PAGE_SIZE))
        page_number = int(request.GET.get('page_number', 0))
        username_starts_with = request.GET.get('username_starts_with', '')

        response = self._get_students(
            semester, page_size=page_size, page_number=page_number,
            username_starts_with=username_starts_with)

        return http.JsonResponse(response)

    def post(self, request, pk, *args, **kwargs):
        pk = int(pk)

        semester = ag_models.Semester.objects.get(pk=pk)
        _check_is_admin(request.user, semester)

        request_content = json.loads(request.body.decode('utf-8'))

        users = [
            User.objects.get_or_create(username=username)[0]
            for username in request_content['enrolled_students']
        ]

        semester.enrolled_students.add(*users)

        return http.JsonResponse(self._get_students(semester), status=201)

    def patch(self, request, pk, *args, **kwargs):
        pk = int(pk)

        semester = ag_models.Semester.objects.get(pk=pk)
        _check_is_admin(request.user, semester)

        request_content = json.loads(request.body.decode('utf-8'))

        users = [
            User.objects.get_or_create(username=username)[0]
            for username in request_content['enrolled_students']
        ]

        semester.enrolled_students.set(users)

        return http.JsonResponse(self._get_students(semester), status=200)

    def delete(self, request, pk, *args, **kwargs):
        pk = int(pk)

        semester = ag_models.Semester.objects.get(pk=pk)
        _check_is_admin(request.user, semester)

        request_content = json.loads(request.body.decode('utf-8'))

        users = User.objects.filter(
            username__in=request_content['enrolled_students'])

        semester.enrolled_students.remove(*users)

        return http.JsonResponse(self._get_students(semester), status=200)

    def _get_students(self, semester,
                      page_size=DEFAULT_ENROLLED_STUDENT_PAGE_SIZE,
                      page_number=0, username_starts_with=''):
        if page_size < 1:
            raise exceptions.ValidationError('page_size must be at least 1')

        if page_number < 0:
            raise exceptions.ValidationError('page_number must be >= 0')

        if username_starts_with:
            queryset = semester.enrolled_students.filter(
                username__startswith=username_starts_with)
        else:
            queryset = semester.enrolled_students.all()

        total_num_students = semester.enrolled_students.count()
        slice_start = page_number * page_size
        slice_end = min(slice_start + page_size, total_num_students)
        users = queryset.order_by('username')[slice_start:slice_end]

        return {
            "enrolled_students": [
                user.username for user in users
            ],
            "num_enrolled_students_total": total_num_students
        }


class ListAddProjectEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)

        semester = ag_models.Semester.objects.get(pk=pk)
        _check_is_enrolled_or_staff(request.user, semester)

        if semester.is_semester_staff(request.user):
            projects = semester.projects.all()
        else:
            projects = semester.projects.filter(visible_to_students=True)

        response = {
            "projects": [
                {
                    "name": project.name,
                    "url": url_shortcuts.project_url(project)
                }
                for project in projects
            ]
        }

        return http.JsonResponse(response)

    def post(self, request, pk, *args, **kwargs):
        pk = int(pk)
        semester = ag_models.Semester.objects.get(pk=pk)
        _check_is_admin(request.user, semester)

        request_content = json.loads(request.body.decode('utf-8'))

        project = ag_models.Project.objects.validate_and_create(
            semester=semester, **request_content)

        response = {
            "name": project.name,
            "url": url_shortcuts.project_url(project)
        }

        return http.JsonResponse(response, status=201)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


def _check_is_admin(user, semester):
    if not semester.course.is_administrator(user):
        raise exceptions.PermissionDenied()


def _check_is_staff(user, semester):
    if not semester.is_semester_staff(user):
        raise exceptions.PermissionDenied()


def _check_is_enrolled(user, semester):
    if not semester.is_enrolled_student(user):
        raise exceptions.PermissionDenied()


def _check_is_enrolled_or_staff(user, semester):
    if not semester.is_enrolled_student(user):
        _check_is_staff(user, semester)
