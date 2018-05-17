from typing import Dict, List, Sequence, Iterable, BinaryIO, Optional

from django.utils.functional import cached_property

from autograder.core.models import Submission, AGTestCommandResult, StudentTestSuiteResult
from autograder.core.models.ag_test.ag_test_suite_result import AGTestSuiteResult
from autograder.core.models.ag_test.ag_test_case_result import AGTestCaseResult
from autograder.core.models.ag_test.feedback_category import FeedbackCategory
from autograder.core.models.ag_model_base import ToDictMixin
from autograder.core.models.project import Project
from autograder.core.models.ag_test.ag_test_suite import AGTestSuite, AGTestSuiteFeedbackConfig
from autograder.core.models.ag_test.ag_test_case import AGTestCase
from autograder.core.models.ag_test.ag_test_command import AGTestCommand


class AGTestPreLoader:
    def __init__(self, project: Project):
        suites = AGTestSuite.objects.filter(
            project=project
        ).select_related(
            'normal_fdbk_config',
            'past_limit_submission_fdbk_config',
            'ultimate_submission_fdbk_config',
            'staff_viewer_fdbk_config'
        )
        self._suites: Dict[int, AGTestSuite] = {
            suite.pk: suite for suite in suites
        }
        cases = AGTestCase.objects.filter(
            ag_test_suite__project=project
        ).select_related(
            'normal_fdbk_config',
            'past_limit_submission_fdbk_config',
            'ultimate_submission_fdbk_config',
            'staff_viewer_fdbk_config'
        )
        self._cases: Dict[int, AGTestCase] = {
            case.pk: case for case in cases
        }

        cmds = AGTestCommand.objects.filter(
            ag_test_suite__project=project
        ).select_related(
            'normal_fdbk_config',
            'past_limit_submission_fdbk_config',
            'ultimate_submission_fdbk_config',
            'staff_viewer_fdbk_config'
        )
        self._cmds: Dict[int, AGTestCommand] = {
            cmd.pk: cmd for cmd in cmds
        }

    def get_ag_test_suite(self, suite_pk: int) -> AGTestSuite:
        return self._suites[suite_pk]

    def get_ag_test_case(self, case_pk: int) -> AGTestCase:
        return self._cases[case_pk]

    def get_ag_test_cmd(self, cmd_pk: int) -> AGTestCommand:
        return self._cmds[cmd_pk]


class DenormalizedAGTestCaseResult:
    def __init__(self, ag_test_case_result: AGTestCaseResult,
                 ag_test_command_results: List[AGTestCommandResult]):
        self.ag_test_case_result = ag_test_case_result
        self.ag_test_command_results = ag_test_command_results


class DenormalizedAGTestSuiteResult:
    def __init__(self, ag_test_suite_result: AGTestSuiteResult,
                 ag_test_case_results: List[DenormalizedAGTestCaseResult]):
        self.ag_test_suite_result = ag_test_suite_result
        self.ag_test_case_results = ag_test_case_results


def _deserialize_denormed_ag_test_results(
    submission: Submission
) -> List[DenormalizedAGTestSuiteResult]:
    result = []
    for serialized_suite_result in submission.get_serialized_ag_test_results():
        deserialized_suite_result = AGTestSuiteResult(
            ag_test_suite_id=serialized_suite_result['ag_test_suite_id'],
            submission_id=serialized_suite_result['submission_id'],
            setup_return_code=serialized_suite_result['setup_return_code'],
            setup_timed_out=serialized_suite_result['setup_timed_out'],
            setup_stdout_truncated=serialized_suite_result['setup_stdout_truncated'],
            setup_stderr_truncated=serialized_suite_result['setup_stderr_truncated'],
        )

        case_results = [
            _deserialize_denormed_ag_test_case_result(case_result)
            for case_result in serialized_suite_result['ag_test_case_results']
        ]

        result.append(DenormalizedAGTestSuiteResult(deserialized_suite_result, case_results))

    return result


def _deserialize_denormed_ag_test_case_result(case_result: dict) -> DenormalizedAGTestCaseResult:
    deserialized_case_result = AGTestCaseResult(
        ag_test_case_id=case_result['ag_test_case_id'],
        ag_test_suite_result_id=case_result['ag_test_suite_result_id'],
    )

    cmd_results = [
        _deserialize_denormed_ag_test_cmd_result(cmd_result)
        for cmd_result in case_result['ag_test_command_results']]

    return DenormalizedAGTestCaseResult(deserialized_case_result, cmd_results)


def _deserialize_denormed_ag_test_cmd_result(cmd_result: dict) -> AGTestCommandResult:
    return AGTestCommandResult(
        ag_test_command_id=cmd_result['ag_test_command_id'],
        ag_test_case_result_id=cmd_result['ag_test_case_result_id'],

        return_code=cmd_result['return_code'],
        return_code_correct=cmd_result['return_code_correct'],

        stdout_correct=cmd_result['stdout_correct'],
        stderr_correct=cmd_result['stderr_correct'],

        timed_out=cmd_result['timed_out'],

        stdout_truncated=cmd_result['stdout_truncated'],
        stderr_truncated=cmd_result['stderr_truncated'],
    )


def get_submission_fdbk(submission: Submission,
                        fdbk_category: FeedbackCategory) -> 'SubmissionFeedbackCalculator':
    return SubmissionFeedbackCalculator(submission, fdbk_category)


class SubmissionFeedbackCalculator(ToDictMixin):
    def __init__(self, submission: Submission, fdbk_category: FeedbackCategory):
        self._submission = submission
        self._fdbk_category = fdbk_category
        self._project = self._submission.group.project

        self._ag_test_loader = AGTestPreLoader(self._project)

        self._ag_test_suite_results = _deserialize_denormed_ag_test_results(self._submission)

    @property
    def pk(self):
        return self._submission.pk

    @property
    def total_points(self) -> int:
        ag_suite_points = sum((
            AGTestSuiteFeedback(
                ag_test_suite_result, self._fdbk_category, self._ag_test_loader
            ).total_points
            for ag_test_suite_result in self._visible_ag_test_suite_results
        ))

        student_suite_points = sum((
            student_test_suite_result.get_fdbk(self._fdbk_category).total_points
            for student_test_suite_result in self._visible_student_test_suite_results
        ))

        return ag_suite_points + student_suite_points

    @property
    def total_points_possible(self) -> int:
        ag_suite_points = sum((
            AGTestSuiteFeedback(
                ag_test_suite_result, self._fdbk_category, self._ag_test_loader
            ).total_points_possible
            for ag_test_suite_result in self._visible_ag_test_suite_results
        ))

        student_suite_points = sum((
            student_test_suite_result.get_fdbk(self._fdbk_category).total_points_possible
            for student_test_suite_result in self._visible_student_test_suite_results
        ))

        return ag_suite_points + student_suite_points

    @property
    def ag_test_suite_results(self) -> List[DenormalizedAGTestSuiteResult]:
        return list(self._visible_ag_test_suite_results)

    @cached_property
    def _visible_ag_test_suite_results(self) -> Iterable[DenormalizedAGTestSuiteResult]:
        visible = filter(
            lambda result: AGTestSuiteFeedback(result,
                                               self._fdbk_category,
                                               self._ag_test_loader).fdbk_conf.visible,
            self._ag_test_suite_results)
        return sorted(
            visible,
            key=lambda result: self._ag_test_loader.get_ag_test_suite(
                result.ag_test_suite_result.ag_test_suite_id)._order
        )

    @property
    def student_test_suite_results(self) -> List['StudentTestSuiteResult']:
        return list(self._visible_student_test_suite_results)

    @cached_property
    def _visible_student_test_suite_results(self) -> Iterable['StudentTestSuiteResult']:
        return filter(
            lambda result: result.get_fdbk(self._fdbk_category).fdbk_conf.visible,
            self._submission.student_test_suite_results.all())

    def to_dict(self):
        result = super().to_dict()
        result['ag_test_suite_results'] = [
            AGTestSuiteFeedback(
                result, self._fdbk_category, self._ag_test_loader
            ).to_dict()
            for result in result['ag_test_suite_results']]
        result['student_test_suite_results'] = [
            result.get_fdbk(self._fdbk_category).to_dict()
            for result in result['student_test_suite_results']]
        return result

    SERIALIZABLE_FIELDS = (
        'pk',
        'total_points',
        'total_points_possible',
        'ag_test_suite_results',
        'student_test_suite_results'
    )


class AGTestSuiteFeedback(ToDictMixin):
    def __init__(self, ag_test_suite_result: DenormalizedAGTestSuiteResult,
                 fdbk_category: FeedbackCategory,
                 ag_test_preloader: AGTestPreLoader):
        self._ag_test_suite_result = ag_test_suite_result.ag_test_suite_result
        self._fdbk_category = fdbk_category
        self._ag_test_case_results = ag_test_suite_result.ag_test_case_results

        self._ag_test_suite = ag_test_preloader.get_ag_test_suite(
            self._ag_test_suite_result.ag_test_suite_id)

        if fdbk_category == FeedbackCategory.normal:
            self._fdbk = self._ag_test_suite.normal_fdbk_config
        elif fdbk_category == FeedbackCategory.ultimate_submission:
            self._fdbk = self._ag_test_suite.ultimate_submission_fdbk_config
        elif fdbk_category == FeedbackCategory.past_limit_submission:
            self._fdbk = self._ag_test_suite.past_limit_submission_fdbk_config
        elif fdbk_category == FeedbackCategory.staff_viewer:
            self._fdbk = self._ag_test_suite.staff_viewer_fdbk_config
        elif fdbk_category == FeedbackCategory.max:
            self._fdbk = AGTestSuiteFeedbackConfig(
                show_individual_tests=True,
                show_setup_and_teardown_stdout=True,
                show_setup_and_teardown_stderr=True)

    @property
    def fdbk_conf(self):
        return self._fdbk

    @property
    def pk(self):
        return self._ag_test_suite_result.pk

    @property
    def ag_test_suite_name(self) -> str:
        return self._ag_test_suite.name

    @property
    def ag_test_suite_pk(self) -> int:
        return self._ag_test_suite.pk

    @property
    def fdbk_settings(self) -> dict:
        return self._fdbk.to_dict()

    @property
    def setup_name(self) -> Optional[str]:
        if not self._show_setup_and_teardown_names:
            return None

        return self._ag_test_suite.setup_suite_cmd_name

    @property
    def setup_return_code(self) -> Optional[int]:
        if not self._fdbk.show_setup_and_teardown_return_code:
            return None

        return self._ag_test_suite_result.setup_return_code

    @property
    def setup_timed_out(self) -> Optional[bool]:
        if not self._fdbk.show_setup_and_teardown_timed_out:
            return None

        return self._ag_test_suite_result.setup_timed_out

    @property
    def setup_stdout(self) -> Optional[BinaryIO]:
        if not self._fdbk.show_setup_and_teardown_stdout:
            return None

        return self._ag_test_suite_result.open_setup_stdout()

    @property
    def setup_stderr(self) -> Optional[BinaryIO]:
        if not self._fdbk.show_setup_and_teardown_stderr:
            return None

        return self._ag_test_suite_result.open_setup_stderr()

    @property
    def teardown_name(self) -> Optional[str]:
        if not self._show_setup_and_teardown_names:
            return None

        return self._ag_test_suite.teardown_suite_cmd_name

    @property
    def teardown_return_code(self) -> Optional[int]:
        if not self._fdbk.show_setup_and_teardown_return_code:
            return None

        return self._ag_test_suite_result.teardown_return_code

    @property
    def teardown_timed_out(self) -> Optional[bool]:
        if not self._fdbk.show_setup_and_teardown_timed_out:
            return None

        return self._ag_test_suite_result.teardown_timed_out

    @property
    def teardown_stdout(self) -> Optional[BinaryIO]:
        if not self._fdbk.show_setup_and_teardown_stdout:
            return None

        return self._ag_test_suite_result.open_teardown_stdout()

    @property
    def teardown_stderr(self) -> Optional[BinaryIO]:
        if not self._fdbk.show_setup_and_teardown_stderr:
            return None

        return self._ag_test_suite_result.open_teardown_stderr()

    @property
    def _show_setup_and_teardown_names(self):
        return (self._fdbk.show_setup_and_teardown_stdout
                or self._fdbk.show_setup_and_teardown_stderr
                or self._fdbk.show_setup_and_teardown_return_code
                or self._fdbk.show_setup_and_teardown_timed_out)

    @property
    def total_points(self) -> int:
        return sum((ag_test_case_result.get_fdbk(self._fdbk_category).total_points
                    for ag_test_case_result in
                    self._visible_ag_test_case_results))

    @property
    def total_points_possible(self) -> int:
        return sum((ag_test_case_result.get_fdbk(self._fdbk_category).total_points_possible
                    for ag_test_case_result in
                    self._visible_ag_test_case_results))

    @property
    def ag_test_case_results(self) -> List[AGTestCaseResult]:
        if not self._fdbk.show_individual_tests:
            return []

        return list(self._visible_ag_test_case_results)

    @property
    def _visible_ag_test_case_results(self) -> Iterable[AGTestCaseResult]:
        res = list(filter(
            lambda result: result.get_fdbk(self._fdbk_category).fdbk_conf.visible,
            self._ag_test_suite_result.ag_test_case_results.all()))
        return res

    def to_dict(self):
        result = super().to_dict()
        ag_test_case_results = self.ag_test_case_results
        result['ag_test_case_results'] = [
            result.get_fdbk(self._fdbk_category).to_dict()
            for result in ag_test_case_results
        ]
        return result

    SERIALIZABLE_FIELDS = (
        'pk',
        'ag_test_suite_name',
        'ag_test_suite_pk',
        'fdbk_settings',
        'total_points',
        'total_points_possible',
        'setup_name',
        'setup_return_code',
        'setup_timed_out',
        'teardown_name',
        'teardown_return_code',
        'teardown_timed_out',
    )
