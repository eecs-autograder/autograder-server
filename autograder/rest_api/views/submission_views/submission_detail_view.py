from django.core import exceptions
from django.db import transaction
from django.http.response import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import decorators, mixins, permissions, response, status, viewsets

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins
from ..load_object_mixin import build_load_object_mixin
from ..permission_components import user_can_view_group


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

        if 'setup_stdout_for_suite' in request.query_params:
            suite_result_pk = int(request.query_params.get('setup_stdout_for_suite'))
            return self._get_setup_stdout(fdbk_calculator, fdbk_category, suite_result_pk)
        elif 'setup_stderr_for_suite' in request.query_params:
            suite_result_pk = int(request.query_params.get('setup_stderr_for_suite'))
            return self._get_setup_stderr(fdbk_calculator, fdbk_category, suite_result_pk)

        elif 'teardown_stdout_for_suite' in request.query_params:
            suite_result_pk = int(request.query_params.get('teardown_stdout_for_suite'))
            return self._get_teardown_stdout(fdbk_calculator, fdbk_category, suite_result_pk)
        elif 'teardown_stderr_for_suite' in request.query_params:
            suite_result_pk = int(request.query_params.get('teardown_stderr_for_suite'))
            return self._get_teardown_stderr(fdbk_calculator, fdbk_category, suite_result_pk)

        elif 'stdout_for_cmd_result' in request.query_params:
            cmd_result_pk = request.query_params.get('stdout_for_cmd_result')
            return self._get_cmd_result_stdout(fdbk_calculator, fdbk_category, cmd_result_pk)
        elif 'stderr_for_cmd_result' in request.query_params:
            cmd_result_pk = request.query_params.get('stderr_for_cmd_result')
            return self._get_cmd_result_stderr(fdbk_calculator, fdbk_category, cmd_result_pk)

        elif 'stdout_diff_for_cmd_result' in request.query_params:
            cmd_result_pk = request.query_params.get('stdout_diff_for_cmd_result')
            return self._get_cmd_result_stdout_diff(
                fdbk_calculator, fdbk_category, cmd_result_pk)
        elif 'stderr_diff_for_cmd_result' in request.query_params:
            cmd_result_pk = request.query_params.get('stderr_diff_for_cmd_result')
            return self._get_cmd_result_stderr_diff(
                fdbk_calculator, fdbk_category, cmd_result_pk)

        elif 'stdout_for_student_suite_setup' in request.query_params:
            student_suite_result_pk = request.query_params.get(
                'stdout_for_student_suite_setup')
            return self._get_student_suite_result_output_field(
                'setup_stdout', fdbk_calculator, fdbk_category, student_suite_result_pk)
        elif 'stderr_for_student_suite_setup' in request.query_params:
            student_suite_result_pk = request.query_params.get(
                'stderr_for_student_suite_setup')
            return self._get_student_suite_result_output_field(
                'setup_stderr', fdbk_calculator, fdbk_category, student_suite_result_pk)

        elif 'stdout_for_student_suite_get_test_names' in request.query_params:
            student_suite_result_pk = request.query_params.get(
                'stdout_for_student_suite_get_test_names')
            return self._get_student_suite_result_output_field(
                'get_student_test_names_stdout', fdbk_calculator,
                fdbk_category, student_suite_result_pk)
        elif 'stderr_for_student_suite_get_test_names' in request.query_params:
            student_suite_result_pk = request.query_params.get(
                'stderr_for_student_suite_get_test_names')
            return self._get_student_suite_result_output_field(
                'get_student_test_names_stderr', fdbk_calculator,
                fdbk_category, student_suite_result_pk)

        elif 'stdout_for_student_suite_validity_check' in request.query_params:
            student_suite_result_pk = request.query_params.get(
                'stdout_for_student_suite_validity_check')
            return self._get_student_suite_result_output_field(
                'validity_check_stdout', fdbk_calculator, fdbk_category, student_suite_result_pk)
        elif 'stderr_for_student_suite_validity_check' in request.query_params:
            student_suite_result_pk = request.query_params.get(
                'stderr_for_student_suite_validity_check')
            return self._get_student_suite_result_output_field(
                'validity_check_stderr', fdbk_calculator, fdbk_category, student_suite_result_pk)

        elif 'stdout_for_student_suite_grade_buggy_impls' in request.query_params:
            student_suite_result_pk = request.query_params.get(
                'stdout_for_student_suite_grade_buggy_impls')
            return self._get_student_suite_result_output_field(
                'grade_buggy_impls_stdout', fdbk_calculator,
                fdbk_category, student_suite_result_pk)
        elif 'stderr_for_student_suite_grade_buggy_impls' in request.query_params:
            student_suite_result_pk = request.query_params.get(
                'stderr_for_student_suite_grade_buggy_impls')
            return self._get_student_suite_result_output_field(
                'grade_buggy_impls_stderr', fdbk_calculator,
                fdbk_category, student_suite_result_pk)

        else:
            return response.Response(fdbk_calculator.to_dict())

    def _get_setup_stdout(self, submission_fdbk: ag_models.Submission.FeedbackCalculator,
                          fdbk_category: ag_models.FeedbackCategory,
                          suite_result_pk: int):
        suite_result = self._find_ag_suite_result(submission_fdbk, suite_result_pk)
        if suite_result is None:
            return response.Response(None)
        stream_data = suite_result.get_fdbk(fdbk_category).setup_stdout
        if stream_data is None:
            return response.Response(None)
        return FileResponse(stream_data)

    def _get_setup_stderr(self, submission_fdbk: ag_models.Submission.FeedbackCalculator,
                          fdbk_category: ag_models.FeedbackCategory,
                          suite_result_pk: int):
        suite_result = self._find_ag_suite_result(submission_fdbk, suite_result_pk)
        if suite_result is None:
            return response.Response(None)
        stream_data = suite_result.get_fdbk(fdbk_category).setup_stderr
        if stream_data is None:
            return response.Response(None)
        return FileResponse(stream_data)

    def _get_teardown_stdout(self, submission_fdbk: ag_models.Submission.FeedbackCalculator,
                             fdbk_category: ag_models.FeedbackCategory,
                             suite_result_pk: int):
        suite_result = self._find_ag_suite_result(submission_fdbk, suite_result_pk)
        if suite_result is None:
            return response.Response(None)
        stream_data = suite_result.get_fdbk(fdbk_category).teardown_stdout
        if stream_data is None:
            return response.Response(None)
        return FileResponse(stream_data)

    def _get_teardown_stderr(self, submission_fdbk: ag_models.Submission.FeedbackCalculator,
                             fdbk_category: ag_models.FeedbackCategory,
                             suite_result_pk: int):
        suite_result = self._find_ag_suite_result(submission_fdbk, suite_result_pk)
        if suite_result is None:
            return response.Response(None)
        stream_data = suite_result.get_fdbk(fdbk_category).teardown_stderr
        if stream_data is None:
            return response.Response(None)
        return FileResponse(stream_data)

    def _find_ag_suite_result(self, submission_fdbk: ag_models.Submission.FeedbackCalculator,
                              suite_result_pk: int) -> ag_models.AGTestSuiteResult:
        for suite_result in submission_fdbk.ag_test_suite_results:
            if suite_result.pk == suite_result_pk:
                return suite_result

        return None

    def _get_cmd_result_stdout(self, submission_fdbk: ag_models.Submission.FeedbackCalculator,
                               fdbk_category: ag_models.FeedbackCategory,
                               cmd_result_pk: int):
        cmd_result = self._find_ag_test_cmd_result(submission_fdbk, fdbk_category, cmd_result_pk)
        if cmd_result is None:
            return response.Response(None)
        stream_data = cmd_result.get_fdbk(fdbk_category).stdout
        if stream_data is None:
            return response.Response(None)
        return FileResponse(stream_data)

    def _get_cmd_result_stderr(self, submission_fdbk: ag_models.Submission.FeedbackCalculator,
                               fdbk_category: ag_models.FeedbackCategory,
                               cmd_result_pk: int):
        cmd_result = self._find_ag_test_cmd_result(submission_fdbk, fdbk_category, cmd_result_pk)
        if cmd_result is None:
            return response.Response(None)
        stream_data = cmd_result.get_fdbk(fdbk_category).stderr
        if stream_data is None:
            return response.Response(None)
        return FileResponse(stream_data)

    def _get_cmd_result_stdout_diff(self, submission_fdbk: ag_models.Submission.FeedbackCalculator,
                                    fdbk_category: ag_models.FeedbackCategory,
                                    cmd_result_pk: int):
        cmd_result = self._find_ag_test_cmd_result(submission_fdbk, fdbk_category, cmd_result_pk)
        if cmd_result is None:
            return response.Response(None)
        diff = cmd_result.get_fdbk(fdbk_category).stdout_diff
        if diff is None:
            return response.Response(None)
        return JsonResponse(diff.diff_content, safe=False)

    def _get_cmd_result_stderr_diff(self, submission_fdbk: ag_models.Submission.FeedbackCalculator,
                                    fdbk_category: ag_models.FeedbackCategory,
                                    cmd_result_pk: int):
        cmd_result = self._find_ag_test_cmd_result(submission_fdbk, fdbk_category, cmd_result_pk)
        if cmd_result is None:
            return response.Response(None)
        diff = cmd_result.get_fdbk(fdbk_category).stderr_diff
        if diff is None:
            return response.Response(None)
        return JsonResponse(diff.diff_content, safe=False)

    def _find_ag_test_cmd_result(self, submission_fdbk: ag_models.Submission.FeedbackCalculator,
                                 fdbk_category: ag_models.FeedbackCategory,
                                 cmd_result_pk: int):
        """
        :raises: Http404 exception if a command result with the
                 given primary key doesn't exist in the database.
        :return: The command result with the given primary key
                 if it can be found in submission_fdbk, None otherwise.
        """
        queryset = ag_models.AGTestCommandResult.objects.select_related(
            'ag_test_case_result__ag_test_suite_result')
        cmd_result = get_object_or_404(queryset, pk=cmd_result_pk)

        for suite_result in submission_fdbk.ag_test_suite_results:
            if suite_result.pk != cmd_result.ag_test_case_result.ag_test_suite_result.pk:
                continue

            for case_result in suite_result.get_fdbk(fdbk_category).ag_test_case_results:
                if case_result.pk != cmd_result.ag_test_case_result.pk:
                    continue

                for cmd_res in case_result.get_fdbk(fdbk_category).ag_test_command_results:
                    if cmd_res == cmd_result:
                        return cmd_res

        return None

    def _get_student_suite_result_output_field(
            self,
            field_name,
            submission_fdbk: ag_models.Submission.FeedbackCalculator,
            fdbk_category: ag_models.FeedbackCategory,
            student_suite_result_pk):
        result = self._find_student_suite_result(submission_fdbk, student_suite_result_pk)
        if result is None:
            return response.Response(None)

        output_stream = getattr(result.get_fdbk(fdbk_category), field_name)
        if output_stream is None:
            return response.Response(None)

        return FileResponse(output_stream)

    def _find_student_suite_result(self, submission_fdbk: ag_models.Submission.FeedbackCalculator,
                                   student_suite_result_pk: int):
        """
        :raises: Http404 exception if a student suite result with the given primary
                 key doesn't exist in the database.

        :return: The student suite result with the given primary key
                 if it can be found in submission_fdbk, None otherwise.
        """
        student_suite_result = get_object_or_404(
            ag_models.StudentTestSuiteResult.objects.all(),
            pk=student_suite_result_pk)

        for result in submission_fdbk.student_test_suite_results:
            if result.pk == student_suite_result.pk:
                return result

        return None

    # TODO: output endpoints for student suite setup, get test names, validity check, and buggy impl grading
