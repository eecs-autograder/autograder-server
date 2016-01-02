import itertools
import os
import json

from django.utils import timezone
from django import http
from django.core import exceptions
from django.contrib.auth.models import User

from .endpoint_base import EndpointBase

from autograder.core import models as ag_models
from autograder.rest_api import url_shortcuts

from .utilities import check_can_view_project, check_can_view_group


class GetSubmissionEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        submission = ag_models.Submission.objects.get(pk=pk)
        check_can_view_project(
            request.user, submission.submission_group.project)
        check_can_view_group(request.user, submission.submission_group)

        response = {
            "type": "submission",
            "id": pk,
            "discarded_files": submission.discarded_files,
            "timestamp": submission.timestamp,
            "status": submission.status,
            "invalid_reason_or_error": submission.invalid_reason_or_error,

            "urls": {
                "self": url_shortcuts.submission_url(submission),
                "submission_group": url_shortcuts.group_url(
                    submission.submission_group),
                "submitted_files": url_shortcuts.submitted_files_url(
                    submission),
                "autograder_test_case_results": (
                    url_shortcuts.ag_test_results_url(submission)),
                "student_test_suite_results": (
                    url_shortcuts.suite_results_url(submission))
            }
        }

        return http.JsonResponse(response)


class ListSubmittedFilesEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        submission = ag_models.Submission.objects.get(pk=pk)
        check_can_view_project(
            request.user, submission.submission_group.project)
        check_can_view_group(request.user, submission.submission_group)

        response = {
            'submitted_files': [
                {
                    "filename": file_.name,
                    "url": url_shortcuts.submitted_file_url(
                        submission, file_.name),
                }
                for file_ in submission.submitted_files
            ]
        }

        return http.JsonResponse(response)


class GetSubmittedFileEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        submission = ag_models.Submission.objects.get(pk=pk)
        check_can_view_project(
            request.user, submission.submission_group.project)
        check_can_view_group(request.user, submission.submission_group)


class ListAutograderTestCaseResultsEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        submission = ag_models.Submission.objects.get(pk=pk)
        check_can_view_project(
            request.user, submission.submission_group.project)
        check_can_view_group(request.user, submission.submission_group)


class ListStudentTestSuiteResultsEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        submission = ag_models.Submission.objects.get(pk=pk)
        check_can_view_project(
            request.user, submission.submission_group.project)
        check_can_view_group(request.user, submission.submission_group)
