import itertools
import os
import json

from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django import http
from django.core import exceptions
from django.contrib.auth.models import User

from .endpoint_base import EndpointBase

from autograder.core import models as ag_models
from autograder.rest_api import url_shortcuts

from .utilities import (
    check_can_view_project, check_is_group_member,
    check_can_view_group)


class GetUpdateDeleteSubmissionGroupEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        group = ag_models.SubmissionGroup.objects.get(pk=pk)
        check_can_view_group(request.user, group)
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
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        group = ag_models.SubmissionGroup.objects.get(pk=pk)
        check_can_view_group(request.user, group)
        check_can_view_project(request.user, group.project)

        response = {
            "submissions": [
                {
                    "timestamp": submission.timestamp,
                    "url": url_shortcuts.submission_url(submission)
                }
                for submission in group.submissions.all()
            ]
        }

        return http.JsonResponse(response)

    def post(self, request, pk, *args, **kwargs):
        timestamp = timezone.now()
        pk = int(pk)
        submitted_files = request.FILES.getlist('files')

        with transaction.atomic():
            group = ag_models.SubmissionGroup.objects.select_for_update().get(
                pk=pk)
            _check_can_submit(request.user, group, timestamp)
            submission = ag_models.Submission.objects.validate_and_create(
                submitted_files=submitted_files, submission_group=group,
                timestamp=timestamp)

        response = {
            "timestamp": timestamp,
            "url": url_shortcuts.submission_url(submission)
        }

        return http.JsonResponse(response, status=201)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


def _check_can_submit(user, group, timestamp):
    check_is_group_member(user, group)
    check_can_view_project(user, group.project)

    if _group_has_active_submission(group):
        raise exceptions.ValidationError(
            'You currently have a submission being processed. '
            'Please wait until it is finished before submitting again.')

    if group.project.semester.is_semester_staff(user):
        return

    if _deadline_passed(group, timestamp):
        raise exceptions.PermissionDenied(
            'The deadline for this project has passed')

    if group.project.disallow_student_submissions:
        raise exceptions.PermissionDenied(
            'Submissions are currently disabled for this project')


def _deadline_passed(group, timestamp):
    if group.extended_due_date is not None:
        deadline = group.extended_due_date
    else:
        deadline = group.project.closing_time

    if deadline is None:
        return False

    return timestamp > deadline


def _group_has_active_submission(group):
    return ag_models.Submission.objects.filter(
        submission_group=group
    ).filter(
        Q(status=ag_models.Submission.GradingStatus.received) |
        Q(status=ag_models.Submission.GradingStatus.queued) |
        Q(status=ag_models.Submission.GradingStatus.being_graded)).exists()


def _check_can_edit_group(user, group):
    if not group.project.semester.course.is_administrator(user):
        raise exceptions.PermissionDenied()
