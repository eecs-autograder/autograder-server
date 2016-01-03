import itertools
import os
import json

from django.utils import timezone
from django import http
from django.core import exceptions
from django.contrib.auth.models import User

from django.db import transaction

from .endpoint_base import EndpointBase

from autograder.core import models as ag_models
from autograder.rest_api import url_shortcuts

import autograder.core.shared.feedback_configuration as fbc


class GetUpdateDeleteStudentTestSuiteEndpoint(EndpointBase):
    _EDITABLE_FIELDS = [
        "name",
        "student_test_case_filename_pattern",
        "correct_implementation_filename",
        "buggy_implementation_filenames",
        "implementation_file_alias",
        "suite_resource_filenames",
        "time_limit",
        "points_per_buggy_implementation_exposed",
        "feedback_configuration",
        "post_deadline_final_submission_feedback_configuration",
        "compiler",
        "compiler_flags",
        "suite_resource_files_to_compile_together"    ,
    ]

    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        suite = ag_models.StudentTestSuiteBase.objects.get(pk=pk)
        _check_can_view(request.user, suite)

        response = suite.to_dict()
        response.update({
            'urls': {
                "self": url_shortcuts.suite_url(suite),
                "project": url_shortcuts.project_url(suite.project)
            }
        })

        return http.JsonResponse(response)

    def patch(self, request, pk, *args, **kwargs):
        pk = int(pk)
        suite = ag_models.StudentTestSuiteBase.objects.get(pk=pk)
        _check_can_edit(request.user, suite)

        request_content = json.loads(request.body.decode('utf-8'))

        response = {}

        for field in self._EDITABLE_FIELDS:
            if field in request_content:
                setattr(suite, field, request_content[field])
                response[field] = request_content[field]

        suite.validate_and_save()

        return http.JsonResponse(response)

    def delete(self, request, pk, *args, **kwargs):
        pk = int(pk)
        suite = ag_models.StudentTestSuiteBase.objects.get(pk=pk)
        _check_can_edit(request.user, suite)

        suite.delete()

        return http.HttpResponse(status=204)

# -----------------------------------------------------------------------------


def _check_can_view(user, suite):
    if not suite.project.semester.is_semester_staff(user):
        raise exceptions.PermissionDenied()


def _check_can_edit(user, suite):
    if not suite.project.semester.course.is_administrator(user):
        raise exceptions.PermissionDenied()
