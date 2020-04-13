from typing import BinaryIO, Callable, Optional

from django.core.cache import cache
from django.http.response import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from drf_composable_permissions.p import P
from rest_framework import response, status
from rest_framework.exceptions import ValidationError

import autograder.core.models as ag_models
import autograder.core.utils as core_ut
import autograder.rest_api.permissions as ag_permissions
from autograder.core.caching import get_cached_submission_feedback
from autograder.core.models.submission import get_submissions_with_results_queryset
from autograder.core.submission_feedback import (AGTestCommandResultFeedback, AGTestPreLoader,
                                                 AGTestSuiteResultFeedback,
                                                 StudentTestSuitePreLoader,
                                                 SubmissionResultFeedback)
from autograder.rest_api.schema import APITags, CustomViewSchema
from autograder.rest_api.serialize_ultimate_submission_results import \
    get_submission_data_with_results
from autograder.rest_api.views.ag_model_views import AGModelAPIView, require_query_params

from .common import FDBK_CATEGORY_PARAM, make_fdbk_category_param_docs, validate_fdbk_category


class SubmissionResultsViewBase(AGModelAPIView):
    permission_classes = [
        ag_permissions.can_view_project(),
        ag_permissions.is_staff_or_group_member(),
        ag_permissions.can_request_feedback_category()
    ]
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
            submission,
            fdbk_category,
            AGTestPreLoader(submission.project)
        )

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        raise NotImplementedError


class SubmissionResultsView(SubmissionResultsViewBase):
    schema = CustomViewSchema([APITags.submissions], {
        'GET': {
            'parameters': [{'$ref': '#/components/parameters/feedbackCategory'}],
            'responses': {
                '200': {
                    'body': {
                        '$ref': '#/components/schemas/SubmissionResultFeedback'
                    }
                }
            }
        }
    })

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
            submission,
            fdbk_category,
            AGTestPreLoader(submission.project)
        )

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


class _OutputViewSchema(CustomViewSchema):
    def __init__(self):
        super().__init__([APITags.submission_output], {
            'GET': {
                'parameters': [{'$ref': '#/components/parameters/feedbackCategory'}],
                'responses': {
                    '200': {
                        'content_type': 'application/octet-stream',
                        'body': {'type': 'string', 'format': 'binary'},
                    }
                }
            }
        })


class AGTestSuiteResultsStdoutView(SubmissionResultsViewBase):
    schema = _OutputViewSchema()

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        suite_result_pk = self.kwargs['result_pk']
        return _get_setup_output(submission_fdbk,
                                 suite_result_pk,
                                 lambda fdbk_calc: fdbk_calc.setup_stdout)


class AGTestSuiteResultsStderrView(SubmissionResultsViewBase):
    schema = _OutputViewSchema()

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        suite_result_pk = self.kwargs['result_pk']
        return _get_setup_output(submission_fdbk,
                                 suite_result_pk,
                                 lambda fdbk_calc: fdbk_calc.setup_stderr)


class AGTestSuiteResultsOutputSizeView(SubmissionResultsViewBase):
    schema = CustomViewSchema([APITags.submission_output], {
        'GET': {
            'parameters': [{'$ref': '#/components/parameters/feedbackCategory'}],
            'responses': {
                '200': {
                    'body': {
                        'type': 'object',
                        'properties': {
                            'setup_stdout_size': {
                                'type': 'integer',
                                'nullable': True,
                            },
                            'setup_stdout_truncated': {
                                'type': 'boolean',
                                'nullable': True,
                            },
                            'setup_stderr_size': {
                                'type': 'integer',
                                'nullable': True,
                            },
                            'setup_stderr_truncated': {
                                'type': 'boolean',
                                'nullable': True,
                            },
                        }
                    }
                }
            }
        }
    })

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        suite_result_pk = self.kwargs['result_pk']
        suite_fdbk = _find_ag_suite_result(submission_fdbk, suite_result_pk)
        if suite_fdbk is None:
            return response.Response(None)
        return response.Response({
            'setup_stdout_size': suite_fdbk.get_setup_stdout_size(),
            'setup_stdout_truncated': suite_fdbk.setup_stdout_truncated,
            'setup_stderr_size': suite_fdbk.get_setup_stderr_size(),
            'setup_stderr_truncated': suite_fdbk.setup_stderr_truncated,
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


class AGTestCommandResultStdoutView(SubmissionResultsViewBase):
    schema = _OutputViewSchema()

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        cmd_result_pk = self.kwargs['result_pk']
        return _get_cmd_result_output(
            submission_fdbk,
            cmd_result_pk,
            lambda fdbk_calc: fdbk_calc.stdout)


class AGTestCommandResultStderrView(SubmissionResultsViewBase):
    schema = _OutputViewSchema()

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        cmd_result_pk = self.kwargs['result_pk']
        return _get_cmd_result_output(
            submission_fdbk,
            cmd_result_pk,
            lambda fdbk_calc: fdbk_calc.stderr)


class AGTestCommandResultOutputSizeView(SubmissionResultsViewBase):
    schema = CustomViewSchema([APITags.submission_output], {
        'GET': {
            'parameters': [{'$ref': '#/components/parameters/feedbackCategory'}],
            'responses': {
                '200': {
                    'body': {
                        'type': 'object',
                        'properties': {
                            'stdout_size': {
                                'type': 'integer',
                                'nullable': True,
                            },
                            'stdout_truncated': {
                                'type': 'boolean',
                                'nullable': True,
                            },
                            'stderr_size': {
                                'type': 'integer',
                                'nullable': True,
                            },
                            'stderr_truncated': {
                                'type': 'boolean',
                                'nullable': True,
                            },
                            'stdout_diff_size': {
                                'type': 'integer',
                                'nullable': True,
                            },
                            'stderr_diff_size': {
                                'type': 'integer',
                                'nullable': True,
                            },
                        }
                    }
                }
            }
        }
    })

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        cmd_result_pk = self.kwargs['result_pk']
        cmd_fdbk = _find_ag_test_cmd_result(submission_fdbk, cmd_result_pk)
        if cmd_fdbk is None:
            return response.Response(None)
        return response.Response({
            'stdout_size': cmd_fdbk.get_stdout_size(),
            'stdout_truncated': cmd_fdbk.stdout_truncated,
            'stderr_size': cmd_fdbk.get_stderr_size(),
            'stderr_truncated': cmd_fdbk.stderr_truncated,
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


class AGTestCommandResultStdoutDiffView(SubmissionResultsViewBase):
    schema = _OutputViewSchema()

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        cmd_result_pk = self.kwargs['result_pk']
        return _get_cmd_result_diff(
            submission_fdbk,
            cmd_result_pk,
            lambda fdbk_calc: fdbk_calc.stdout_diff)


class AGTestCommandResultStderrDiffView(SubmissionResultsViewBase):
    schema = _OutputViewSchema()

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


class StudentTestSuiteResultSetupStdoutView(SubmissionResultsViewBase):
    schema = _OutputViewSchema()

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            submission_fdbk,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.setup_stdout)


class StudentTestSuiteResultSetupStderrView(SubmissionResultsViewBase):
    schema = _OutputViewSchema()

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            submission_fdbk,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.setup_stderr)


class StudentTestSuiteResultGetStudentTestsStdoutView(SubmissionResultsViewBase):
    schema = _OutputViewSchema()

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            submission_fdbk,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.get_student_test_names_stdout)


class StudentTestSuiteResultGetStudentTestsStderrView(SubmissionResultsViewBase):
    schema = _OutputViewSchema()

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            submission_fdbk,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.get_student_test_names_stderr)


class StudentTestSuiteResultValidityCheckStdoutView(SubmissionResultsViewBase):
    schema = _OutputViewSchema()

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            submission_fdbk,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.validity_check_stdout)


class StudentTestSuiteResultValidityCheckStderrView(SubmissionResultsViewBase):
    schema = _OutputViewSchema()

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            submission_fdbk,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.validity_check_stderr)


class StudentTestSuiteResultGradeBuggyImplsStdoutView(SubmissionResultsViewBase):
    schema = _OutputViewSchema()

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            submission_fdbk,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.grade_buggy_impls_stdout)


class StudentTestSuiteResultGradeBuggyImplsStderrView(SubmissionResultsViewBase):
    schema = _OutputViewSchema()

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        return _get_student_suite_result_output_field(
            submission_fdbk,
            fdbk_category,
            student_suite_result_pk,
            lambda fdbk_calc: fdbk_calc.grade_buggy_impls_stderr)


class StudentTestSuiteOutputSizeView(SubmissionResultsViewBase):
    schema = CustomViewSchema([APITags.submission_output], {
        'GET': {
            'parameters': [{'$ref': '#/components/parameters/feedbackCategory'}],
            'responses': {
                '200': {
                    'body': {
                        'type': 'object',
                        'properties': {
                            'setup_stdout_size': {
                                'type': 'integer',
                                'nullable': True,
                            },
                            'setup_stderr_size': {
                                'type': 'integer',
                                'nullable': True,
                            },
                            'get_student_test_names_stdout_size': {
                                'type': 'integer',
                                'nullable': True,
                            },
                            'get_student_test_names_stderr_size': {
                                'type': 'integer',
                                'nullable': True,
                            },
                            'validity_check_stdout_size': {
                                'type': 'integer',
                                'nullable': True,
                            },
                            'validity_check_stderr_size': {
                                'type': 'integer',
                                'nullable': True,
                            },
                            'grade_buggy_impls_stdout_size': {
                                'type': 'integer',
                                'nullable': True,
                            },
                            'grade_buggy_impls_stderr_size': {
                                'type': 'integer',
                                'nullable': True,
                            },
                        }
                    }
                }
            }
        }
    })

    def _make_response(self, submission_fdbk: SubmissionResultFeedback,
                       fdbk_category: ag_models.FeedbackCategory):
        student_suite_result_pk = self.kwargs['result_pk']
        result = _find_student_suite_result(submission_fdbk, student_suite_result_pk)
        if result is None:
            return response.Response(None)

        fdbk = result.get_fdbk(fdbk_category, submission_fdbk.student_test_suite_preloader)
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

    output_stream = get_output_fn(
        result.get_fdbk(fdbk_category, submission_fdbk.student_test_suite_preloader))
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
