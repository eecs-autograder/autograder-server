import itertools
import os
import json

from django.utils import timezone
from django import http
from django.core import exceptions
from django.contrib.auth.models import User

from django.db.models import Q

from .endpoint_base import EndpointBase

from autograder.core import models as ag_models
from autograder.rest_api import url_shortcuts

from .utilities import check_can_view_project, check_can_view_group

import autograder.core.shared.feedback_configuration as fbc


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
    def get(self, request, pk, filename, *args, **kwargs):
        pk = int(pk)
        submission = ag_models.Submission.objects.get(pk=pk)
        check_can_view_project(
            request.user, submission.submission_group.project)
        check_can_view_group(request.user, submission.submission_group)

        file_ = submission.get_file(filename)
        response = {
            "type": "submitted_file",
            "filename": file_.name,
            "size": file_.size,
            "content": file_.read(),

            "urls": {
                "self": url_shortcuts.submitted_file_url(
                    submission, file_.name),
                "submission": url_shortcuts.submission_url(submission)
            }
        }

        return http.JsonResponse(response)


class ListAutograderTestCaseResultsEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        submission = ag_models.Submission.objects.get(pk=pk)
        check_can_view_project(
            request.user, submission.submission_group.project)
        check_can_view_group(request.user, submission.submission_group)

        queryset = self._get_queryset(request, submission)
        is_staff = submission.submission_group.project.semester.is_semester_staff(
            request.user)

        response = {
            'autograder_test_case_results': []
        }

        for result in queryset:
            data = {
                "test_case_name": result.test_case.name,
                "url": url_shortcuts.ag_test_result_url(result)
            }
            data.update(result.total_points_as_dict(max_feedback=is_staff))
            response['autograder_test_case_results'].append(data)

        return http.JsonResponse(response)

    def _get_queryset(self, request, submission):
        if (submission.submission_group.project.semester.is_semester_staff(
                request.user) and
                request.user.username in submission.submission_group.member_names):
            return submission.results.all()

        deadline = (submission.submission_group.extended_due_date if
                    submission.submission_group.extended_due_date is not None else
                    submission.submission_group.project.closing_time)

        if (timezone.now() < deadline or submission !=
                submission.submission_group.submissions.first()):
            return submission.results.filter(
                test_case__feedback_configuration__visibility_level=fbc.VisibilityLevel.show_to_students.value)

        return submission.results.filter(
            (Q(test_case__post_deadline_final_submission_feedback_configuration__isnull=False) &
             Q(test_case__post_deadline_final_submission_feedback_configuration__visibility_level=fbc.VisibilityLevel.show_to_students.value)) |
            (Q(test_case__post_deadline_final_submission_feedback_configuration=None) &
             Q(test_case__feedback_configuration__visibility_level=fbc.VisibilityLevel.show_to_students.value)),
        )


class ListStudentTestSuiteResultsEndpoint(EndpointBase):
    def get(self, request, pk, *args, **kwargs):
        pk = int(pk)
        submission = ag_models.Submission.objects.get(pk=pk)
        check_can_view_project(
            request.user, submission.submission_group.project)
        check_can_view_group(request.user, submission.submission_group)

        queryset = self._get_queryset(request, submission)
        is_staff = submission.submission_group.project.semester.is_semester_staff(
            request.user)

        response = {
            "student_test_suite_results": []
        }

        for result in queryset:
            data = {
                "test_suite_name": result.test_suite.name,
                "url": url_shortcuts.suite_result_url(result)
            }
            data.update(result.total_points_as_dict(max_feedback=is_staff))
            response['student_test_suite_results'].append(data)

        return http.JsonResponse(response)

    def _get_queryset(self, request, submission):
        if (submission.submission_group.project.semester.is_semester_staff(
                request.user) and
                request.user.username in submission.submission_group.member_names):
            return submission.suite_results.all()

        deadline = (submission.submission_group.extended_due_date if
                    submission.submission_group.extended_due_date is not None else
                    submission.submission_group.project.closing_time)

        if (timezone.now() < deadline or submission !=
                submission.submission_group.submissions.first()):
            return submission.suite_results.filter(
                test_suite__feedback_configuration__visibility_level=fbc.VisibilityLevel.show_to_students.value)

        return submission.suite_results.filter(
            (Q(test_suite__post_deadline_final_submission_feedback_configuration__isnull=False) &
             Q(test_suite__post_deadline_final_submission_feedback_configuration__visibility_level=fbc.VisibilityLevel.show_to_students.value)) |
            (Q(test_suite__post_deadline_final_submission_feedback_configuration=None) &
             Q(test_suite__feedback_configuration__visibility_level=fbc.VisibilityLevel.show_to_students.value)),
        )
        # annotate(
        #     is_visible=Case(
        #         # When(
        #         #     Q(test_suite__post_deadline_final_submission_feedback_configuration__isnull=False) &
        #         #     Q(test_suite__post_deadline_final_submission_feedback_configuration__visibility_level=fbc.VisibilityLevel.show_to_students.value),
        #         #     then=Value(True)
        #         # ),
        #         When(
        #             Q(test_suite__post_deadline_final_submission_feedback_configuration__isnull=True) &
        #             Q(test_suite__feedback_configuration__visibility_level=fbc.VisibilityLevel.show_to_students.value),
        #             then=Value(True)
        #         ),
        #         default=Value(False),
        #         output_field=BooleanField()
        #     )
        # ).filter(is_visible=True)
