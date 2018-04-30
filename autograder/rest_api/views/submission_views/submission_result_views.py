from typing import BinaryIO, Callable, Optional

from django.core.cache import cache
from django.http.response import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import response
from rest_framework.exceptions import ValidationError

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
import autograder.rest_api.permissions as ag_permissions
from autograder.core.models.submission import get_submissions_with_results_queryset
from autograder.rest_api.views.ag_model_views import (AGModelAPIView, require_query_params)

_FDBK_CATEGORY_PARAM = 'feedback_category'


class SubmissionResultsViewBase(AGModelAPIView):
    permission_classes = (ag_permissions.can_view_project(),
                          ag_permissions.is_staff_or_group_member(),
                          ag_permissions.can_request_feedback_category())
    model_manager = ag_models.Submission.objects

    @method_decorator(require_query_params(_FDBK_CATEGORY_PARAM))
    def get(self, *args, **kwargs):
        fdbk_category = self._get_fdbk_category()
        fdbk_calculator = self._get_fdbk_calculator(fdbk_category)
        return self._make_response(fdbk_calculator, fdbk_category)

    def _get_fdbk_category(self) -> ag_models.FeedbackCategory:
        fdbk_category_arg = self.request.query_params.get(_FDBK_CATEGORY_PARAM)
        try:
            return ag_models.FeedbackCategory(fdbk_category_arg)
        except ValueError:
            raise ValidationError({
                _FDBK_CATEGORY_PARAM: 'Invalid value: {}'.format(fdbk_category_arg)
            })

    def _get_fdbk_calculator(
        self, fdbk_category: ag_models.FeedbackCategory
    ) -> ag_models.Submission.FeedbackCalculator:
        return self.get_object().get_fdbk(fdbk_category)

    def _make_response(self, fdbk_calculator: ag_models.Submission.FeedbackCalculator,
                       fdbk_category: ag_models.FeedbackCategory):
        raise NotImplementedError


class SubmissionResultsView(SubmissionResultsViewBase):
    def _get_fdbk_calculator(
        self, fdbk_category: ag_models.FeedbackCategory
    ) -> ag_models.Submission.FeedbackCalculator:
        """
        Loads the requested submission, prefetching result data, and
        returns a Submission.FeedbackCalculator initialized with
        fdbk_category.
        """
        model_manager = get_submissions_with_results_queryset(
            fdbk_category, base_manager=self.model_manager)
        submission = self.get_object(model_manager_override=model_manager)
        return submission.get_fdbk(fdbk_category)

    def _make_response(self, fdbk_calculator: ag_models.Submission.FeedbackCalculator,
                       fdbk_category: ag_models.FeedbackCategory):
        if (fdbk_category != ag_models.FeedbackCategory.normal or
                self.request.query_params.get('use_cache', 'true') != 'true'):
            return response.Response(self._get_fdbk_calculator(fdbk_category).to_dict())

        submission = self.get_object()
        not_done_enough_to_cache = (
            submission.status != ag_models.Submission.GradingStatus.waiting_for_deferred and
            submission.status != ag_models.Submission.GradingStatus.finished_grading)
        if not_done_enough_to_cache:
            return response.Response(self._get_fdbk_calculator(fdbk_category).to_dict())

        cache_key = 'project_{}_submission_normal_results_{}'.format(
            submission.group.project.pk,
            submission.pk)

        result = cache.get(cache_key)
        if result is None:
            # Re-load the submission, with result data prefetched.
            result = self._get_fdbk_calculator(fdbk_category).to_dict()
            cache.set(cache_key, result, timeout=None)

        return response.Response(result)


class AGTestSuiteResultsStdoutView(SubmissionResultsViewBase):
    def _make_response(self, fdbk_calculator: ag_models.Submission.FeedbackCalculator,
                       fdbk_category: ag_models.FeedbackCategory):
        suite_result_pk = self.kwargs['result_pk']
        return _get_setup_output(fdbk_calculator,
                                 fdbk_category,
                                 suite_result_pk,
                                 lambda fdbk_calc: fdbk_calc.setup_stdout)


class AGTestSuiteResultsStderrView(SubmissionResultsViewBase):
    def _make_response(self, fdbk_calculator: ag_models.Submission.FeedbackCalculator,
                       fdbk_category: ag_models.FeedbackCategory):
        suite_result_pk = self.kwargs['result_pk']
        return _get_setup_output(fdbk_calculator,
                                 fdbk_category,
                                 suite_result_pk,
                                 lambda fdbk_calc: fdbk_calc.setup_stderr)


GetOutputFnType = Callable[[ag_models.AGTestSuiteResult.FeedbackCalculator], str]


def _get_setup_output(submission_fdbk: ag_models.Submission.FeedbackCalculator,
                      fdbk_category: ag_models.FeedbackCategory,
                      suite_result_pk: int,
                      get_output_fn: GetOutputFnType):
    suite_result = _find_ag_suite_result(submission_fdbk, suite_result_pk)
    if suite_result is None:
        return response.Response(None)
    stream_data = get_output_fn(suite_result.get_fdbk(fdbk_category))
    if stream_data is None:
        return response.Response(None)
    return FileResponse(stream_data)


def _find_ag_suite_result(submission_fdbk: ag_models.Submission.FeedbackCalculator,
                          suite_result_pk: int) -> Optional[ag_models.AGTestSuiteResult]:
    for suite_result in submission_fdbk.ag_test_suite_results:
        if suite_result.pk == suite_result_pk:
            return suite_result

    return None


class AGTestCommandResultStdoutView(SubmissionResultsViewBase):
    def _make_response(self, fdbk_calculator: ag_models.Submission.FeedbackCalculator,
                       fdbk_category: ag_models.FeedbackCategory):
        cmd_result_pk = self.kwargs['result_pk']
        return _get_cmd_result_output(
            fdbk_calculator,
            fdbk_category,
            cmd_result_pk,
            lambda fdbk_calc: fdbk_calc.stdout)


class AGTestCommandResultStderrView(SubmissionResultsViewBase):
    def _make_response(self, fdbk_calculator: ag_models.Submission.FeedbackCalculator,
                       fdbk_category: ag_models.FeedbackCategory):
        cmd_result_pk = self.kwargs['result_pk']
        return _get_cmd_result_output(
            fdbk_calculator,
            fdbk_category,
            cmd_result_pk,
            lambda fdbk_calc: fdbk_calc.stderr)


GetCmdOutputFnType = Callable[
    [ag_models.AGTestCommandResult.FeedbackCalculator], Optional[BinaryIO]]


def _get_cmd_result_output(submission_fdbk: ag_models.Submission.FeedbackCalculator,
                           fdbk_category: ag_models.FeedbackCategory,
                           cmd_result_pk: int,
                           get_output_fn: GetCmdOutputFnType):
    cmd_result = _find_ag_test_cmd_result(submission_fdbk, fdbk_category, cmd_result_pk)
    if cmd_result is None:
        return response.Response(None)
    stream_data = get_output_fn(cmd_result.get_fdbk(fdbk_category))
    if stream_data is None:
        return response.Response(None)
    return FileResponse(stream_data)


class AGTestCommandResultStdoutDiffView(SubmissionResultsViewBase):
    def _make_response(self, fdbk_calculator: ag_models.Submission.FeedbackCalculator,
                       fdbk_category: ag_models.FeedbackCategory):
        cmd_result_pk = self.kwargs['result_pk']
        return _get_cmd_result_diff(
            fdbk_calculator,
            fdbk_category,
            cmd_result_pk,
            lambda fdbk_calc: fdbk_calc.stdout_diff)


class AGTestCommandResultStderrDiffView(SubmissionResultsViewBase):
    def _make_response(self, fdbk_calculator: ag_models.Submission.FeedbackCalculator,
                       fdbk_category: ag_models.FeedbackCategory):
        cmd_result_pk = self.kwargs['result_pk']
        return _get_cmd_result_diff(
            fdbk_calculator,
            fdbk_category,
            cmd_result_pk,
            lambda fdbk_calc: fdbk_calc.stderr_diff)


GetDiffFnType = Callable[[ag_models.AGTestCommandResult.FeedbackCalculator], core_ut.DiffResult]


def _get_cmd_result_diff(submission_fdbk: ag_models.Submission.FeedbackCalculator,
                         fdbk_category: ag_models.FeedbackCategory,
                         cmd_result_pk: int,
                         get_diff_fn: GetDiffFnType):
    cmd_result = _find_ag_test_cmd_result(submission_fdbk, fdbk_category, cmd_result_pk)
    if cmd_result is None:
        return response.Response(None)

    diff = get_diff_fn(cmd_result.get_fdbk(fdbk_category))
    if diff is None:
        return response.Response(None)

    return JsonResponse(diff.diff_content, safe=False)


def _find_ag_test_cmd_result(submission_fdbk: ag_models.Submission.FeedbackCalculator,
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


class StudentTestSuiteResultSetupStdoutView(SubmissionResultsViewBase):
    def _make_response(self, fdbk_calculator: ag_models.Submission.FeedbackCalculator,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            fdbk_calculator,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.setup_stdout)


class StudentTestSuiteResultSetupStderrView(SubmissionResultsViewBase):
    def _make_response(self, fdbk_calculator: ag_models.Submission.FeedbackCalculator,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            fdbk_calculator,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.setup_stderr)


class StudentTestSuiteResultGetStudentTestsStdoutView(SubmissionResultsViewBase):
    def _make_response(self, fdbk_calculator: ag_models.Submission.FeedbackCalculator,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            fdbk_calculator,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.get_student_test_names_stdout)


class StudentTestSuiteResultGetStudentTestsStderrView(SubmissionResultsViewBase):
    def _make_response(self, fdbk_calculator: ag_models.Submission.FeedbackCalculator,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            fdbk_calculator,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.get_student_test_names_stderr)


class StudentTestSuiteResultValidityCheckStdoutView(SubmissionResultsViewBase):
    def _make_response(self, fdbk_calculator: ag_models.Submission.FeedbackCalculator,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            fdbk_calculator,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.validity_check_stdout)


class StudentTestSuiteResultValidityCheckStderrView(SubmissionResultsViewBase):
    def _make_response(self, fdbk_calculator: ag_models.Submission.FeedbackCalculator,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            fdbk_calculator,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.validity_check_stderr)


class StudentTestSuiteResultGradeBuggyImplsStdoutView(SubmissionResultsViewBase):
    def _make_response(self, fdbk_calculator: ag_models.Submission.FeedbackCalculator,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            fdbk_calculator,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.grade_buggy_impls_stdout)


class StudentTestSuiteResultGradeBuggyImplsStderrView(SubmissionResultsViewBase):
    def _make_response(self, fdbk_calculator: ag_models.Submission.FeedbackCalculator,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            fdbk_calculator,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.grade_buggy_impls_stderr)


GetStudentSuiteOutputFnType = Callable[
    [ag_models.StudentTestSuiteResult.FeedbackCalculator], Optional[BinaryIO]]


def _get_student_suite_result_output_field(
        submission_fdbk: ag_models.Submission.FeedbackCalculator,
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


def _find_student_suite_result(submission_fdbk: ag_models.Submission.FeedbackCalculator,
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
