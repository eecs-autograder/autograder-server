import itertools
import os
import json

from django.db import transaction
from django import http
from django.core import exceptions
from django.contrib.auth.models import User

from .endpoint_base import EndpointBase

from autograder.core import models as ag_models
from autograder.rest_api import url_shortcuts

from .utilities import check_can_view_project


class GetUpdateDeleteSubmissionGroupEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        group = ag_models.SubmissionGroup.objects.get(pk=pk)
        _check_can_view_group(request.user, group)
        check_can_view_project(request.user, group.project)

        response = {
            "type": "submission_group",
            "id": group.pk,
            "members": group.member_names,
            "extended_due_date": group.extended_due_date,
            "urls": {
                "self": url_shortcuts.group_url(group),
                "project": url_shortcuts.project_url(group.project),
                "submissions": url_shortcuts.submissions_url(group)
            }
        }

        return http.JsonResponse(response)

    def patch(self, request, pk, *args, **kwargs):
        pk = int(pk)
        group = ag_models.SubmissionGroup.objects.get(pk=pk)
        _check_can_edit_group(request.user, group)
        request_content = json.loads(request.body.decode('utf-8'))

        response = {}

        with transaction.atomic():
            if 'extended_due_date' in request_content:
                group.extended_due_date = request_content['extended_due_date']
                response['extended_due_date'] = group.extended_due_date

            if 'members' in request_content:
                group.update_group(
                    request_content['members'],
                    check_project_group_limits=False)
                response['members'] = group.member_names

        return http.JsonResponse(response)

    def delete(self, request, pk, *args, **kwargs):
        pk = int(pk)
        group = ag_models.SubmissionGroup.objects.get(pk=pk)
        _check_can_edit_group(request.user, group)

        group.delete()

        return http.HttpResponse(status=204)


class AddListSubmissionsEndpoint(EndpointBase):
    pass


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


def _check_can_view_group(user, group):
    if group.project.semester.is_semester_staff(user):
        return

    if not user.groups_is_member_of.filter(pk=group.pk).exists():
        raise exceptions.PermissionDenied()


def _check_can_edit_group(user, group):
    if not group.project.semester.course.is_administrator(user):
        raise exceptions.PermissionDenied()
