from django.utils import timezone
from django import http
from django.core import exceptions
from django.contrib.auth.models import User

from django.db import transaction

from .endpoint_base import EndpointBase

from autograder.core import models as ag_models
from autograder.rest_api import url_shortcuts

import autograder.core.shared.feedback_configuration as fbc

from .utilities import check_can_view_project, check_can_view_group


class GetAutograderTestCaseResultEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        result = ag_models.AutograderTestCaseResult.objects.get(pk=pk)
        check_can_view_project(request.user, result.test_case.project)
        check_can_view_group(request.user, result.submission.submission_group)

        response = {
            "type": "autograder_test_case_result",
            "id": result.pk,

            "urls": {
                "self": url_shortcuts.ag_test_result_url(result),
                'submission': url_shortcuts.submission_url(result.submission)
            }
        }

        is_staff = result.test_case.project.semester.is_semester_staff(
            request.user)
        _check_visibility(request.user, result, is_staff)

        feedback_override = (
            fbc.AutograderTestCaseFeedbackConfiguration.get_max_feedback() if
            is_staff else None)

        data = result.to_json(feedback_override)
        response.update(data)

        return http.JsonResponse(response)


def _check_visibility(user, result, is_staff):
    if is_staff and user in result.submission.submission_group.members.all():
        return

    visibility_level = _get_visibility_level(user, result)
    if visibility_level != fbc.VisibilityLevel.show_to_students:
        raise exceptions.PermissionDenied()


def _get_visibility_level(user, result):
    if (result.test_case.post_deadline_final_submission_feedback_configuration
            is None):
        return result.test_case.feedback_configuration.visibility_level

    is_final_submission = (
        result.submission ==
        result.submission.submission_group.submissions.first())

    extended_due_date = result.submission.submission_group.extended_due_date
    if extended_due_date is not None:
        is_after_closing_time = timezone.now() > extended_due_date
    else:
        is_after_closing_time = (
            timezone.now() >
            result.submission.submission_group.project.closing_time)

    if is_final_submission and is_after_closing_time:
        return (result.test_case.
                post_deadline_final_submission_feedback_configuration.
                visibility_level)

    return result.test_case.feedback_configuration.visibility_level
