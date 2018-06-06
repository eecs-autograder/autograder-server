import autograder.core.models as ag_models
from autograder.core.models import Submission, FeedbackCategory
from autograder.core.submission_feedback import (
    DenormalizedAGTestCaseResult,
    DenormalizedAGTestSuiteResult, AGTestSuiteResultFeedback, AGTestPreLoader,
    AGTestCaseResultFeedback, AGTestCommandResultFeedback, SubmissionResultFeedback)


def get_submission_fdbk(submission: Submission,
                        fdbk_category: FeedbackCategory) -> SubmissionResultFeedback:
    return SubmissionResultFeedback(
        submission, fdbk_category, AGTestPreLoader(submission.group.project))


def get_suite_fdbk(result: ag_models.AGTestSuiteResult,
                   fdbk_category: ag_models.FeedbackCategory) -> AGTestSuiteResultFeedback:
    denormed_case_results = []
    for case_result in result.ag_test_case_results.all():
        denormed_case_results.append(
            DenormalizedAGTestCaseResult(
                case_result, case_result.ag_test_command_results.all()))

    denormed_suite_result = DenormalizedAGTestSuiteResult(result, denormed_case_results)
    return AGTestSuiteResultFeedback(
        denormed_suite_result, fdbk_category,
        AGTestPreLoader(result.ag_test_suite.project))


def get_case_fdbk(result: ag_models.AGTestCaseResult,
                  fdbk_category: ag_models.FeedbackCategory,
                  is_first_failure=False) -> AGTestCaseResultFeedback:
    denormed_case_result = DenormalizedAGTestCaseResult(
        result, result.ag_test_command_results.all())
    return AGTestCaseResultFeedback(
        denormed_case_result, fdbk_category,
        AGTestPreLoader(result.ag_test_case.ag_test_suite.project),
        is_first_failure=is_first_failure
    )


def get_cmd_fdbk(result: ag_models.AGTestCommandResult,
                 fdbk_category: ag_models.FeedbackCategory) -> AGTestCommandResultFeedback:
    return AGTestCommandResultFeedback(
        result, fdbk_category,
        AGTestPreLoader(result.ag_test_command.ag_test_case.ag_test_suite.project))
