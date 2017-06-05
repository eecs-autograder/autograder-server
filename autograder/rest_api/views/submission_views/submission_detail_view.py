from django.core import exceptions
from django.db import transaction
from django.http.response import FileResponse

from rest_framework import (
    viewsets, mixins, permissions, decorators, response, status)

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins
import autograder.rest_api.permissions as ag_permissions

from ..permission_components import user_can_view_group
from ..load_object_mixin import build_load_object_mixin


class _Permissions(permissions.BasePermission):
    def has_object_permission(self, request, view, submission):
        if request.method not in permissions.SAFE_METHODS:
            return submission.submission_group.project.course.is_administrator(
                request.user)

        return user_can_view_group(request.user, submission.submission_group)


class _RemoveFromQueuePermissions(permissions.BasePermission):
    def has_object_permission(self, request, view, submission):
        group = submission.submission_group
        if not user_can_view_group(request.user, group):
            return False

        return group.members.filter(pk=request.user.pk).exists()


class SubmissionDetailViewSet(build_load_object_mixin(ag_models.Submission),
                              mixins.RetrieveModelMixin,
                              transaction_mixins.TransactionUpdateMixin,
                              viewsets.GenericViewSet):
    queryset = ag_models.Submission.objects.all()
    serializer_class = ag_serializers.SubmissionSerializer
    permission_classes = (permissions.IsAuthenticated, _Permissions)

    @decorators.detail_route()
    def file(self, request, *args, **kwargs):
        submission = self.get_object()

        try:
            filename = request.query_params['filename']
            return FileResponse(submission.get_file(filename))
        except KeyError:
            return response.Response(
                'Missing required query parameter "filename"',
                status=status.HTTP_400_BAD_REQUEST)
        except exceptions.ObjectDoesNotExist:
            return response.Response('File "{}" not found'.format(filename),
                                     status=status.HTTP_404_NOT_FOUND)

    @transaction.atomic()
    @decorators.detail_route(methods=['post'],
                             permission_classes=(permissions.IsAuthenticated,
                                                 _RemoveFromQueuePermissions))
    def remove_from_queue(self, request, *args, **kwargs):
        submission = self.get_object()
        removeable_statuses = [ag_models.Submission.GradingStatus.received,
                               ag_models.Submission.GradingStatus.queued]
        if submission.status not in removeable_statuses:
            return response.Response('This submission is not currently queued',
                                     status=status.HTTP_400_BAD_REQUEST)

        submission.status = (
            ag_models.Submission.GradingStatus.removed_from_queue)
        submission.save()

        return response.Response(status=status.HTTP_204_NO_CONTENT)

    @decorators.detail_route(
        permission_classes=(
            permissions.IsAuthenticated,
            ag_permissions.can_view_project(
                lambda submission: submission.submission_group.project),
            ag_permissions.is_staff_or_group_member(
                lambda submission: submission.submission_group),
            ag_permissions.can_request_feedback_category())
    )
    def feedback(self, request, *args, **kwargs):
        self.queryset = self.queryset.prefetch_related(
            'ag_test_suites__ag_test_cases__ag_test_commands')
        submission = self.get_object()  # type: ag_models.Submission
        fdbk_category = ag_models.FeedbackCategory(request.query_params.get('feedback_category'))
        fdbk_calculator = submission.get_fdbk(fdbk_category)

        if 'stdout_for_cmd_result' in request.query_params:
            cmd_result_pk = request.query_params.get('stdout_for_cmd_result')
            field_name = 'stdout'
        elif 'stderr_for_cmd_result' in request.query_params:
            cmd_result_pk = request.query_params.get('stderr_for_cmd_result')
            field_name = 'stderr'
        elif 'stdout_diff_for_cmd_result' in request.query_params:
            cmd_result_pk = request.query_params.get('stdout_diff_for_cmd_result')
            field_name = 'stdout_diff'
        elif 'stderr_diff_for_cmd_result' in request.query_params:
            cmd_result_pk = request.query_params.get('stderr_diff_for_cmd_result')
            field_name = 'stderr_diff'
        else:
            return response.Response(fdbk_calculator.to_dict())

        cmd_result = ag_models.AGTestCommandResult.objects.select_related(
            'ag_test_case_result__ag_test_suite_result').get(pk=cmd_result_pk)

        for suite_result in fdbk_calculator.ag_test_suite_results:
            if suite_result.pk != cmd_result.ag_test_case_result.ag_test_suite_result.pk:
                continue

            for case_result in suite_result.get_fdbk(fdbk_category).ag_test_case_results:
                if case_result.pk != cmd_result.ag_test_case_result.pk:
                    continue

                for cmd_res in case_result.get_fdbk(fdbk_category).ag_test_command_results:
                    if cmd_res == cmd_result:
                        return response.Response(
                            getattr(cmd_res.get_fdbk(fdbk_category), field_name))

        return response.Response(None)
