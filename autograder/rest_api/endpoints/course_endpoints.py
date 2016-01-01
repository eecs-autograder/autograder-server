import json

from django.contrib.auth.models import User
from django import http
from django.core.urlresolvers import reverse
from django.core import exceptions

from .endpoint_base import EndpointBase

from autograder.core import models as ag_models
from autograder.rest_api import url_shortcuts


class ListCreateCourseEndpoint(EndpointBase):
    def get(self, request, *args, **kwargs):
        self._check_permissions(request)

        content = {
            'courses': [
                {
                    'name': course.name,
                    'url': url_shortcuts.get_course(course)
                }
                for course in ag_models.Course.objects.all()
            ]
        }

        return http.JsonResponse(content)

    def post(self, request, *args, **kwargs):
        self._check_permissions(request)

        request_content = json.loads(request.body.decode('utf-8'))
        course = ag_models.Course.objects.validate_and_create(
            name=request_content['name'])

        response = {
            'name': course.name,
            'url': url_shortcuts.get_course(course)
        }

        return http.JsonResponse(response, status=201)

    def _check_permissions(self, request):
        if not request.user.is_superuser:
            raise exceptions.PermissionDenied()


class GetUpdateCourseEndpoint(EndpointBase):
    _EDITABLE_FIELDS = ['name']

    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        course = ag_models.Course.objects.get(pk=pk)

        response = {
            "type": "course",
            "id": pk,
            "name": course.name,
            "urls": {
                "self": url_shortcuts.get_course(course),
            }
        }

        if course.is_administrator(request.user):
            response['urls'].update({
                "administrators": url_shortcuts.get_course_admins(course),
                "semesters": url_shortcuts.get_semesters(course)
            })

        return http.JsonResponse(response)

    def patch(self, request, pk, *args, **kwargs):
        pk = int(pk)
        course = ag_models.Course.objects.get(pk=pk)
        _check_is_admin(course, request.user)

        request_content = json.loads(request.body.decode('utf-8'))

        response = {}

        for field in self._EDITABLE_FIELDS:
            if field in request_content:
                setattr(course, field, request_content[field])
                response[field] = request_content[field]

        course.validate_and_save()

        return http.JsonResponse(response)


class ListAddRemoveCourseAdministratorsEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        course = ag_models.Course.objects.get(pk=pk)
        _check_is_superuser_or_admin(course, request.user)
        response = {
            'administrators': course.administrator_names
        }

        return http.JsonResponse(response)

    def post(self, request, pk, *args, **kwargs):
        pk = int(pk)
        course = ag_models.Course.objects.get(pk=pk)
        _check_is_superuser_or_admin(course, request.user)

        request_content = json.loads(request.body.decode('utf-8'))

        users = [
            User.objects.get_or_create(username=username)[0]
            for username in request_content['administrators']
        ]

        course.administrators.add(*users)

        response = {
            'administrators': course.administrator_names
        }

        return http.JsonResponse(response, status=201)

    def delete(self, request, pk, *args, **kwargs):
        pk = int(pk)
        course = ag_models.Course.objects.get(pk=pk)
        _check_is_superuser_or_admin(course, request.user)

        request_content = json.loads(request.body.decode('utf-8'))

        if request.user.username in request_content['administrators']:
            raise exceptions.ValidationError(
                'You may not remove yourself from a list of administrators')

        users = [
            User.objects.get_or_create(username=username)[0]
            for username in request_content['administrators']
        ]

        course.administrators.remove(*users)

        response = {
            'administrators': course.administrator_names
        }

        return http.JsonResponse(response)


class ListAddSemesterEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        course = ag_models.Course.objects.get(pk=pk)
        _check_is_admin(course, request.user)

        response = {
            "semesters": [
                {
                    "name": semester.name,
                    "url": url_shortcuts.get_semester(semester)
                }
                for semester in course.semesters.all()
            ]
        }

        return http.JsonResponse(response)

    def post(self, request, pk, *args, **kwargs):
        pk = int(pk)
        course = ag_models.Course.objects.get(pk=pk)
        _check_is_admin(course, request.user)

        request_content = json.loads(request.body.decode('utf-8'))

        semester = ag_models.Semester.objects.validate_and_create(
            course=course, name=request_content['name'])

        response = {
            'name': semester.name,
            "url": url_shortcuts.get_semester(semester)
        }

        return http.JsonResponse(response, status=201)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


def _check_is_admin(course, user):
    if not course.is_administrator(user):
        raise exceptions.PermissionDenied()


def _check_is_superuser_or_admin(course, user):
    if not user.is_superuser:
        _check_is_admin(course, user)
