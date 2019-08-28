from typing import BinaryIO, Callable, Optional

from django.core.cache import cache
from django.http.response import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from drf_composable_permissions.p import P
from drf_yasg.openapi import Parameter, Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import response, status
from rest_framework.exceptions import ValidationError

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
import autograder.rest_api.permissions as ag_permissions
from autograder.core.caching import get_cached_submission_feedback
from autograder.core.models.submission import get_submissions_with_results_queryset
from autograder.core.submission_feedback import (
    SubmissionResultFeedback, AGTestSuiteResultFeedback, AGTestCommandResultFeedback,
    AGTestPreLoader)
from autograder.rest_api.views.ag_model_views import AGModelAPIView, require_query_params
from autograder.rest_api.views.schema_generation import APITags, AGModelSchemaBuilder
from autograder.rest_api.serialize_ultimate_submission_results import (
    get_submission_data_with_results)

from .common import make_fdbk_category_param_docs, validate_fdbk_category, FDBK_CATEGORY_PARAM


class SubmissionResultsViewBase(AGModelAPIView):
    permission_classes = (ag_permissions.can_view_project(),
                          ag_permissions.is_staff_or_group_member(),
                          ag_permissions.can_request_feedback_category())
    model_manager = ag_models.Submission.objects.select_related('project')

    @method_decorator(require_query_params(FDBK_CATEGORY_PARAM))
    def get(self, *args, **kwargs):
        fdbk_category = self._get_fdbk_category()
        submission_fdbk = self._get_submission_fdbk(fdbk_category)
        return self._make_response(submission_fdbk, fdbk_category)

    def _get_fdbk_category(self) -> ag_models.FeedbackCategory:
        fdbk_category_arg = self.request.query_params.get(FDBK_CATEGORY_PARAM)
        return validate_fdbk_category(fdbk_category_arg)

    def _get_submission_fdbk(
        self, fdbk_category: ag_models.FeedbackCategory
    ) -> SubmissionResultFeedback:
        submission = self.get_object()
        return SubmissionResultFeedback(
            submission, fdbk_category, AGTestPreLoader(submission.project))

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        raise NotImplementedError


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
        manual_parameters=[make_fdbk_category_param_docs()],
        responses={
            '200': AGModelSchemaBuilder.get().get_schema(SubmissionResultFeedback)
        }
    )
)
class SubmissionResultsView(SubmissionResultsViewBase):
    def _get_submission_fdbk(
        self, fdbk_category: ag_models.FeedbackCategory
    ) -> SubmissionResultFeedback:
        """
        Loads the requested submission, prefetching result data, and
        returns a SubmissionResultFeedback initialized with
        fdbk_category.
        """
        model_manager = get_submissions_with_results_queryset(base_manager=self.model_manager)
        submission = self.get_object(model_manager_override=model_manager)
        return SubmissionResultFeedback(
            submission, fdbk_category, AGTestPreLoader(submission.project))

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        if (fdbk_category != ag_models.FeedbackCategory.normal
                or self.request.query_params.get('use_cache', 'true') != 'true'):
            return response.Response(submission_fdbk.to_dict())

        submission = self.get_object()
        not_done_enough_to_cache = (
            submission.status != ag_models.Submission.GradingStatus.waiting_for_deferred
            and submission.status != ag_models.Submission.GradingStatus.finished_grading)
        if not_done_enough_to_cache:
            return response.Response(submission_fdbk.to_dict())

        return response.Response(get_cached_submission_feedback(submission, submission_fdbk))


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(manual_parameters=[make_fdbk_category_param_docs()])
)
class AGTestSuiteResultsStdoutView(SubmissionResultsViewBase):
    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        suite_result_pk = self.kwargs['result_pk']
        return _get_setup_output(submission_fdbk,
                                 suite_result_pk,
                                 lambda fdbk_calc: fdbk_calc.setup_stdout)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(manual_parameters=[make_fdbk_category_param_docs()])
)
class AGTestSuiteResultsStderrView(SubmissionResultsViewBase):
    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        suite_result_pk = self.kwargs['result_pk']
        return _get_setup_output(submission_fdbk,
                                 suite_result_pk,
                                 lambda fdbk_calc: fdbk_calc.setup_stderr)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
        manual_parameters=[make_fdbk_category_param_docs()],
        responses={'200': Schema(
            type='object',
            properties={
                'setup_stdout_size': Parameter('setup_stdout_size', 'body', type='Optional[int]'),
                'setup_stderr_size': Parameter('setup_stderr_size', 'body', type='Optional[int]'),
            }
        )}
    )
)
class AGTestSuiteResultsOutputSizeView(SubmissionResultsViewBase):
    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        suite_result_pk = self.kwargs['result_pk']
        suite_fdbk = _find_ag_suite_result(submission_fdbk, suite_result_pk)
        if suite_fdbk is None:
            return response.Response(None)
        return response.Response({
            'setup_stdout_size': suite_fdbk.get_setup_stdout_size(),
            'setup_stderr_size': suite_fdbk.get_setup_stderr_size(),
        })


GetOutputFnType = Callable[[AGTestSuiteResultFeedback], str]


def _get_setup_output(submission_fdbk: SubmissionResultFeedback,
                      suite_result_pk: int,
                      get_output_fn: GetOutputFnType):
    suite_fdbk = _find_ag_suite_result(submission_fdbk, suite_result_pk)
    if suite_fdbk is None:
        return response.Response(None)
    stream_data = get_output_fn(suite_fdbk)
    if stream_data is None:
        return response.Response(None)
    return FileResponse(stream_data)


def _find_ag_suite_result(submission_fdbk: SubmissionResultFeedback,
                          suite_result_pk: int) -> Optional[AGTestSuiteResultFeedback]:
    """
    :raises: Http404 exception if a suite result with the
             given primary key doesn't exist in the database.
    :return: The suite result with the given primary key
             if it can be found in submission_fdbk, None otherwise.
    """
    suite_result = get_object_or_404(ag_models.AGTestSuiteResult.objects.all(),
                                     pk=suite_result_pk)

    for suite_fdbk in submission_fdbk.ag_test_suite_results:
        if suite_fdbk.pk == suite_result.pk:
            return suite_fdbk

    return None


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(manual_parameters=[make_fdbk_category_param_docs()])
)
class AGTestCommandResultStdoutView(SubmissionResultsViewBase):
    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        cmd_result_pk = self.kwargs['result_pk']
        return _get_cmd_result_output(
            submission_fdbk,
            cmd_result_pk,
            lambda fdbk_calc: fdbk_calc.stdout)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(manual_parameters=[make_fdbk_category_param_docs()])
)
class AGTestCommandResultStderrView(SubmissionResultsViewBase):
    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        cmd_result_pk = self.kwargs['result_pk']
        return _get_cmd_result_output(
            submission_fdbk,
            cmd_result_pk,
            lambda fdbk_calc: fdbk_calc.stderr)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
        manual_parameters=[make_fdbk_category_param_docs()],
        responses={'200': Schema(
            type='object',
            properties={
                'stdout_size': Parameter('stdout_size', 'body', type='Optional[int]'),
                'stderr_size': Parameter('stderr_size', 'body', type='Optional[int]'),
                'stdout_diff_size': Parameter('stdout_diff_size', 'body', type='Optional[int]'),
                'stderr_diff_size': Parameter('stderr_diff_size', 'body', type='Optional[int]'),
            }
        )}
    )
)
class AGTestCommandResultOutputSizeView(SubmissionResultsViewBase):
    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        cmd_result_pk = self.kwargs['result_pk']
        cmd_fdbk = _find_ag_test_cmd_result(submission_fdbk, cmd_result_pk)
        if cmd_fdbk is None:
            return response.Response(None)
        return response.Response({
            'stdout_size': cmd_fdbk.get_stdout_size(),
            'stderr_size': cmd_fdbk.get_stderr_size(),
            'stdout_diff_size': cmd_fdbk.get_stdout_diff_size(),
            'stderr_diff_size': cmd_fdbk.get_stderr_diff_size(),
        })


GetCmdOutputFnType = Callable[
    [AGTestCommandResultFeedback], Optional[BinaryIO]]


def _get_cmd_result_output(submission_fdbk: SubmissionResultFeedback,
                           cmd_result_pk: int,
                           get_output_fn: GetCmdOutputFnType):
    cmd_fdbk = _find_ag_test_cmd_result(submission_fdbk, cmd_result_pk)
    if cmd_fdbk is None:
        return response.Response(None)
    stream_data = get_output_fn(cmd_fdbk)
    if stream_data is None:
        return response.Response(None)
    return FileResponse(stream_data)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(manual_parameters=[make_fdbk_category_param_docs()])
)
class AGTestCommandResultStdoutDiffView(SubmissionResultsViewBase):
    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        cmd_result_pk = self.kwargs['result_pk']
        return _get_cmd_result_diff(
            submission_fdbk,
            cmd_result_pk,
            lambda fdbk_calc: fdbk_calc.stdout_diff)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(manual_parameters=[make_fdbk_category_param_docs()])
)
class AGTestCommandResultStderrDiffView(SubmissionResultsViewBase):
    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        cmd_result_pk = self.kwargs['result_pk']
        return _get_cmd_result_diff(
            submission_fdbk,
            cmd_result_pk,
            lambda fdbk_calc: fdbk_calc.stderr_diff)


GetDiffFnType = Callable[[AGTestCommandResultFeedback], core_ut.DiffResult]


def _get_cmd_result_diff(submission_fdbk: SubmissionResultFeedback,
                         cmd_result_pk: int,
                         get_diff_fn: GetDiffFnType):
    cmd_fdbk = _find_ag_test_cmd_result(submission_fdbk, cmd_result_pk)
    if cmd_fdbk is None:
        return response.Response(None)

    diff = get_diff_fn(cmd_fdbk)
    if diff is None:
        return response.Response(None)

    return JsonResponse(diff.diff_content, safe=False)


def _find_ag_test_cmd_result(submission_fdbk: SubmissionResultFeedback,
                             cmd_result_pk: int) -> Optional[AGTestCommandResultFeedback]:
    """
    :raises: Http404 exception if a command result with the
             given primary key doesn't exist in the database.
    :return: The command result with the given primary key
             if it can be found in submission_fdbk, None otherwise.
    """
    queryset = ag_models.AGTestCommandResult.objects.select_related(
        'ag_test_case_result__ag_test_suite_result')
    cmd_result = get_object_or_404(queryset, pk=cmd_result_pk)

    for suite_fdbk in submission_fdbk.ag_test_suite_results:
        if suite_fdbk.pk != cmd_result.ag_test_case_result.ag_test_suite_result.pk:
            continue

        for case_fdbk in suite_fdbk.ag_test_case_results:
            if case_fdbk.pk != cmd_result.ag_test_case_result.pk:
                continue

            for cmd_fdbk in case_fdbk.ag_test_command_results:
                if cmd_fdbk.pk == cmd_result.pk:
                    return cmd_fdbk

    return None


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(manual_parameters=[make_fdbk_category_param_docs()])
)
class StudentTestSuiteResultSetupStdoutView(SubmissionResultsViewBase):
    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            submission_fdbk,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.setup_stdout)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(manual_parameters=[make_fdbk_category_param_docs()])
)
class StudentTestSuiteResultSetupStderrView(SubmissionResultsViewBase):
    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            submission_fdbk,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.setup_stderr)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(manual_parameters=[make_fdbk_category_param_docs()])
)
class StudentTestSuiteResultGetStudentTestsStdoutView(SubmissionResultsViewBase):
    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            submission_fdbk,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.get_student_test_names_stdout)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(manual_parameters=[make_fdbk_category_param_docs()])
)
class StudentTestSuiteResultGetStudentTestsStderrView(SubmissionResultsViewBase):
    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            submission_fdbk,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.get_student_test_names_stderr)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(manual_parameters=[make_fdbk_category_param_docs()])
)
class StudentTestSuiteResultValidityCheckStdoutView(SubmissionResultsViewBase):
    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            submission_fdbk,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.validity_check_stdout)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(manual_parameters=[make_fdbk_category_param_docs()])
)
class StudentTestSuiteResultValidityCheckStderrView(SubmissionResultsViewBase):
    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            submission_fdbk,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.validity_check_stderr)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(manual_parameters=[make_fdbk_category_param_docs()])
)
class StudentTestSuiteResultGradeBuggyImplsStdoutView(SubmissionResultsViewBase):
    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            submission_fdbk,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.grade_buggy_impls_stdout)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(manual_parameters=[make_fdbk_category_param_docs()])
)
class StudentTestSuiteResultGradeBuggyImplsStderrView(SubmissionResultsViewBase):
    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            submission_fdbk,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.grade_buggy_impls_stderr)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
        manual_parameters=[make_fdbk_category_param_docs()],
        responses={'200': Schema(
            type='object',
            properties={
                'setup_stdout_size': Parameter('setup_stdout_size', 'body', type='Optional[int]'),
                'setup_stderr_size': Parameter('setup_stderr_size', 'body', type='Optional[int]'),
                'get_student_test_names_stdout_size': Parameter(
                    'get_student_test_names_stdout_size', 'body', type='Optional[int]'),
                'get_student_test_names_stderr_size': Parameter(
                    'get_student_test_names_stderr_size', 'body', type='Optional[int]'),
                'validity_check_stdout_size': Parameter(
                    'validity_check_stdout_size', 'body', type='Optional[int]'),
                'validity_check_stderr_size': Parameter(
                    'validity_check_stderr_size', 'body', type='Optional[int]'),
                'grade_buggy_impls_stdout_size': Parameter(
                    'grade_buggy_impls_stdout_size', 'body', type='Optional[int]'),
                'grade_buggy_impls_stderr_size': Parameter(
                    'grade_buggy_impls_stderr_size', 'body', type='Optional[int]'),
            }
        )}
    )
)
class StudentTestSuiteOutputSizeView(SubmissionResultsViewBase):
    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        result = _find_student_suite_result(submission_fdbk, student_suite_result_pk)
        if result is None:
            return response.Response(None)

        fdbk = result.get_fdbk(fdbk_category)
        return response.Response({
            'setup_stdout_size': fdbk.get_setup_stdout_size(),
            'setup_stderr_size': fdbk.get_setup_stderr_size(),
            'get_student_test_names_stdout_size': fdbk.get_student_test_names_stdout_size(),
            'get_student_test_names_stderr_size': fdbk.get_student_test_names_stderr_size(),
            'validity_check_stdout_size': fdbk.get_validity_check_stdout_size(),
            'validity_check_stderr_size': fdbk.get_validity_check_stderr_size(),
            'grade_buggy_impls_stdout_size': fdbk.get_grade_buggy_impls_stdout_size(),
            'grade_buggy_impls_stderr_size': fdbk.get_grade_buggy_impls_stderr_size(),
        })


GetStudentSuiteOutputFnType = Callable[
    [ag_models.StudentTestSuiteResult.FeedbackCalculator], Optional[BinaryIO]]


def _get_student_suite_result_output_field(
        submission_fdbk: SubmissionResultFeedback,
        fdbk_category: ag_models.FeedbackCategory,
        student_suite_result_pk,
        get_output_fn: GetStudentSuiteOutputFnType):
    result = _find_student_suite_result(submission_fdbk, student_suite_result_pk)
    if result is None:
        return response.Response(None)

    output_stream = get_output_fn(result.get_fdbk(fdbk_category))
    if output_stream is None:
        return response.Response(None)

    return FileResponse(output_stream)


def _find_student_suite_result(submission_fdbk: SubmissionResultFeedback,
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
