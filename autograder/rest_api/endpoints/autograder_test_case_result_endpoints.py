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
        feedback_override = (
            fbc.AutograderTestCaseFeedbackConfiguration.get_max_feedback() if
            is_staff else None)
        response.update(result.to_json(feedback_override))

        return http.JsonResponse(response)
