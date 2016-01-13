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


class GetUpdateDeleteAutograderTestCaseEndpoint(EndpointBase):
    _EDITABLE_FIELDS = [
        "name",
        "command_line_arguments",
        "standard_input",
        "test_resource_files",
        "student_resource_files",
        "time_limit",
        "expected_return_code",
        "expect_any_nonzero_return_code",
        "expected_standard_output",
        "expected_standard_error_output",
        "use_valgrind",
        "valgrind_flags",

        "points_for_correct_return_code",
        "points_for_correct_output",
        "deduction_for_valgrind_errors",
        "points_for_compilation_success",

        "feedback_configuration",
        "post_deadline_final_submission_feedback_configuration",

        # compiled_test_case fields
        "compiler",
        "compiler_flags",
        "project_files_to_compile_together",
        "student_files_to_compile_together",
        "executable_name",
    ]

    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        ag_test = ag_models.AutograderTestCaseBase.objects.get(pk=pk)
        _check_can_view(request.user, ag_test)

        response = ag_test.to_dict()
        response.update({
            'urls': {
                "self": url_shortcuts.ag_test_url(ag_test),
                "project": url_shortcuts.project_url(ag_test.project)
            }
        })

        return http.JsonResponse(response)

    def patch(self, request, pk, *args, **kwargs):
        pk = int(pk)
        ag_test = ag_models.AutograderTestCaseBase.objects.get(pk=pk)
        _check_can_edit(request.user, ag_test)

        request_content = json.loads(request.body.decode('utf-8'))
        print(request_content)

        response = {}

        for field in self._EDITABLE_FIELDS:
            if field in request_content:
                setattr(ag_test, field, request_content[field])
                response[field] = request_content[field]

        ag_test.validate_and_save()

        return http.JsonResponse(response)

    def delete(self, request, pk, *args, **kwargs):
        pk = int(pk)
        ag_test = ag_models.AutograderTestCaseBase.objects.get(pk=pk)
        _check_can_edit(request.user, ag_test)

        ag_test.delete()

        return http.HttpResponse(status=204)

# -----------------------------------------------------------------------------


def _check_can_view(user, ag_test):
    if not ag_test.project.semester.is_semester_staff(user):
        raise exceptions.PermissionDenied()


def _check_can_edit(user, ag_test):
    if not ag_test.project.semester.course.is_administrator(user):
        raise exceptions.PermissionDenied()
