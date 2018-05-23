import tempfile
from typing import Dict, List, Sequence, Iterable, BinaryIO, Optional

from django.db import models, transaction
from django.db.models import Prefetch

from autograder.core.models import Submission, AGTestCommandResult, StudentTestSuiteResult
from autograder.core.models.ag_test.ag_test_suite_result import AGTestSuiteResult
from autograder.core.models.ag_test.ag_test_case_result import AGTestCaseResult
from autograder.core.models.ag_test.feedback_category import FeedbackCategory
from autograder.core.models.ag_model_base import ToDictMixin
from autograder.core.models.project import Project
from autograder.core.models.ag_test.ag_test_suite import AGTestSuite, AGTestSuiteFeedbackConfig
from autograder.core.models.ag_test.ag_test_case import AGTestCase, AGTestCaseFeedbackConfig
from autograder.core.models.ag_test.ag_test_command import (
    AGTestCommand, ExpectedOutputSource,
    ValueFeedbackLevel, ExpectedReturnCode, AGTestCommandFeedbackConfig,
    MAX_AG_TEST_COMMAND_FDBK_SETTINGS)

import autograder.core.utils as core_ut


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
            ag_test_case__ag_test_suite__project=project
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
    for serialized_suite_result in submission.denormalized_ag_test_results.values():
        deserialized_suite_result = AGTestSuiteResult(
            pk=serialized_suite_result['pk'],

            ag_test_suite_id=serialized_suite_result['ag_test_suite_id'],
            submission_id=serialized_suite_result['submission_id'],
            setup_return_code=serialized_suite_result['setup_return_code'],
            setup_timed_out=serialized_suite_result['setup_timed_out'],
            setup_stdout_truncated=serialized_suite_result['setup_stdout_truncated'],
            setup_stderr_truncated=serialized_suite_result['setup_stderr_truncated'],
        )

        case_results = [
            _deserialize_denormed_ag_test_case_result(case_result)
            for case_result in serialized_suite_result['ag_test_case_results'].values()
        ]

        result.append(DenormalizedAGTestSuiteResult(deserialized_suite_result, case_results))

    return result


def _deserialize_denormed_ag_test_case_result(case_result: dict) -> DenormalizedAGTestCaseResult:
    deserialized_case_result = AGTestCaseResult(
        pk=case_result['pk'],

        ag_test_case_id=case_result['ag_test_case_id'],
        ag_test_suite_result_id=case_result['ag_test_suite_result_id'],
    )

    cmd_results = [
        _deserialize_denormed_ag_test_cmd_result(cmd_result)
        for cmd_result in case_result['ag_test_command_results'].values()
    ]

    return DenormalizedAGTestCaseResult(deserialized_case_result, cmd_results)


def _deserialize_denormed_ag_test_cmd_result(cmd_result: dict) -> AGTestCommandResult:
    return AGTestCommandResult(
        pk=cmd_result['pk'],

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


@transaction.atomic()
def update_denormalized_ag_test_results(submission_pk: int) -> Submission:
    """
    Updates the denormalized_ag_test_results field for the submission
    with the given primary key.

    Returns the updated submission.
    """
    submission_manager = Submission.objects.select_for_update().prefetch_related(
        Prefetch(
            'ag_test_suite_results',
            AGTestSuiteResult.objects.prefetch_related(
                Prefetch(
                    'ag_test_case_results',
                    AGTestCaseResult.objects.prefetch_related(
                        Prefetch('ag_test_command_results', AGTestCommandResult.objects.all())
                    )
                )
            )
        )
    )

    submission = submission_manager.get(pk=submission_pk)
    submission.denormalized_ag_test_results = {
        str(suite_res.ag_test_suite_id): suite_res.to_dict()
        for suite_res in submission.ag_test_suite_results.all()
    }

    submission.save()
    return submission


def get_submission_fdbk(submission: Submission,
                        fdbk_category: FeedbackCategory) -> 'SubmissionResultFeedback':
    return SubmissionResultFeedback(submission, fdbk_category)


class SubmissionResultFeedback(ToDictMixin):
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
            ag_test_suite_result.total_points
            for ag_test_suite_result in self.ag_test_suite_results
        ))

        student_suite_points = sum((
            student_test_suite_result.get_fdbk(self._fdbk_category).total_points
            for student_test_suite_result in self._visible_student_test_suite_results
        ))

        return ag_suite_points + student_suite_points

    @property
    def total_points_possible(self) -> int:
        ag_suite_points = sum((
            ag_test_suite_result.total_points_possible
            for ag_test_suite_result in self.ag_test_suite_results
        ))

        student_suite_points = sum((
            student_test_suite_result.get_fdbk(self._fdbk_category).total_points_possible
            for student_test_suite_result in self._visible_student_test_suite_results
        ))

        return ag_suite_points + student_suite_points

    @property
    def ag_test_suite_results(self) -> List['AGTestSuiteResultFeedback']:
        visible = filter(
            lambda result: AGTestSuiteResultFeedback(result,
                                                     self._fdbk_category,
                                                     self._ag_test_loader).fdbk_conf.visible,
            self._ag_test_suite_results)

        def suite_result_sort_key(suite_res: DenormalizedAGTestSuiteResult):
            suite = self._ag_test_loader.get_ag_test_suite(
                suite_res.ag_test_suite_result.ag_test_suite_id)
            return suite._order

        return [
            AGTestSuiteResultFeedback(
                ag_test_suite_result, self._fdbk_category, self._ag_test_loader)
            for ag_test_suite_result in sorted(visible, key=suite_result_sort_key)
        ]

    @property
    def student_test_suite_results(self) -> List['StudentTestSuiteResult']:
        return list(self._visible_student_test_suite_results)

    @property
    def _visible_student_test_suite_results(self) -> Sequence['StudentTestSuiteResult']:
        return list(
            filter(
                lambda result: result.get_fdbk(self._fdbk_category).fdbk_conf.visible,
                self._submission.student_test_suite_results.all()
            )
        )

    def to_dict(self):
        result = super().to_dict()

        result['ag_test_suite_results'] = [
            res_fdbk.to_dict() for res_fdbk in result['ag_test_suite_results']
        ]

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


class AGTestSuiteResultFeedback(ToDictMixin):
    def __init__(self, ag_test_suite_result: DenormalizedAGTestSuiteResult,
                 fdbk_category: FeedbackCategory,
                 ag_test_preloader: AGTestPreLoader):
        self._ag_test_suite_result = ag_test_suite_result.ag_test_suite_result
        self._fdbk_category = fdbk_category
        self._ag_test_case_results = ag_test_suite_result.ag_test_case_results

        self._ag_test_preloader = ag_test_preloader

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
        return sum((
            ag_test_case_result.total_points
            for ag_test_case_result in self._visible_ag_test_case_results
        ))

    @property
    def total_points_possible(self) -> int:
        return sum((
            ag_test_case_fdbk.total_points_possible
            for ag_test_case_fdbk in self._visible_ag_test_case_results
        ))

    @property
    def ag_test_case_results(self) -> List['AGTestCaseResultFeedback']:
        if not self._fdbk.show_individual_tests:
            return []

        return list(self._visible_ag_test_case_results)

    @property
    def _visible_ag_test_case_results(self) -> Iterable['AGTestCaseResultFeedback']:
        result_fdbk = (
            AGTestCaseResultFeedback(result, self._fdbk_category, self._ag_test_preloader)
            for result in self._ag_test_case_results
        )
        visible = filter(lambda result_fdbk: result_fdbk.fdbk_conf.visible, result_fdbk)

        def case_res_sort_key(case_res: AGTestCaseResultFeedback):
            case = self._ag_test_preloader.get_ag_test_case(
                case_res.ag_test_case_pk)
            return case._order

        return sorted(visible, key=case_res_sort_key)

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

        'ag_test_case_results'
    )

    def to_dict(self):
        result = super().to_dict()
        result['ag_test_case_results'] = [
            res_fdbk.to_dict() for res_fdbk in result['ag_test_case_results']
        ]

        return result


class AGTestCaseResultFeedback(ToDictMixin):
    def __init__(self, ag_test_case_result: DenormalizedAGTestCaseResult,
                 fdbk_category: FeedbackCategory,
                 ag_test_preloader: AGTestPreLoader):
        self._ag_test_case_result = ag_test_case_result.ag_test_case_result
        self._ag_test_command_results = ag_test_case_result.ag_test_command_results
        self._fdbk_category = fdbk_category
        self._ag_test_preloader = ag_test_preloader

        self._ag_test_case = self._ag_test_preloader.get_ag_test_case(
            self._ag_test_case_result.ag_test_case_id)

        if fdbk_category == FeedbackCategory.normal:
            self._fdbk = self._ag_test_case.normal_fdbk_config
        elif fdbk_category == FeedbackCategory.ultimate_submission:
            self._fdbk = self._ag_test_case.ultimate_submission_fdbk_config
        elif fdbk_category == FeedbackCategory.past_limit_submission:
            self._fdbk = self._ag_test_case.past_limit_submission_fdbk_config
        elif fdbk_category == FeedbackCategory.staff_viewer:
            self._fdbk = self._ag_test_case.staff_viewer_fdbk_config
        elif fdbk_category == FeedbackCategory.max:
            self._fdbk = AGTestCaseFeedbackConfig(show_individual_commands=True)

    @property
    def fdbk_conf(self):
        return self._fdbk

    @property
    def pk(self):
        return self._ag_test_case_result.pk

    @property
    def ag_test_case_name(self) -> str:
        return self._ag_test_case.name

    @property
    def ag_test_case_pk(self) -> int:
        return self._ag_test_case.pk

    @property
    def fdbk_settings(self) -> dict:
        return self._fdbk.to_dict()

    @property
    def total_points(self) -> int:
        points = sum((cmd_res.total_points for cmd_res in self._visible_cmd_results))
        return max(0, points)

    @property
    def total_points_possible(self) -> int:
        return sum((cmd_res.total_points_possible for cmd_res in self._visible_cmd_results))

    @property
    def ag_test_command_results(self) -> List['AGTestCommandResultFeedback']:
        if not self._fdbk.show_individual_commands:
            return []

        return list(self._visible_cmd_results)

    @property
    def _visible_cmd_results(self) -> Iterable['AGTestCommandResultFeedback']:
        results_fdbk = (
            AGTestCommandResultFeedback(result, self._fdbk_category, self._ag_test_preloader)
            for result in self._ag_test_command_results
        )
        visible = filter(lambda result_fdbk: result_fdbk.fdbk_conf.visible, results_fdbk)

        def cmd_res_sort_key(cmd_result: AGTestCommandResultFeedback):
            cmd = self._ag_test_preloader.get_ag_test_cmd(cmd_result.ag_test_command_pk)
            return cmd._order

        return sorted(visible, key=cmd_res_sort_key)

    SERIALIZABLE_FIELDS = (
        'pk',
        'ag_test_case_name',
        'ag_test_case_pk',
        'fdbk_settings',
        'total_points',
        'total_points_possible',

        'ag_test_command_results',
    )

    def to_dict(self):
        result = super().to_dict()
        result['ag_test_command_results'] = [
            res_fdbk.to_dict() for res_fdbk in result['ag_test_command_results']
        ]

        return result


class AGTestCommandResultFeedback(ToDictMixin):
    """
    Instances of this class dynamically calculate the appropriate
    feedback data to give for an AGTestCommandResult.
    """

    def __init__(self, ag_test_command_result: AGTestCommandResult,
                 fdbk_category: FeedbackCategory,
                 ag_test_preloader: AGTestPreLoader):
        self._ag_test_command_result = ag_test_command_result
        self._ag_test_preloader = ag_test_preloader

        self._cmd = self._ag_test_preloader.get_ag_test_cmd(
            self._ag_test_command_result.ag_test_command_id)

        if fdbk_category == FeedbackCategory.normal:
            self._fdbk = self._cmd.normal_fdbk_config
        elif fdbk_category == FeedbackCategory.ultimate_submission:
            self._fdbk = self._cmd.ultimate_submission_fdbk_config
        elif fdbk_category == FeedbackCategory.past_limit_submission:
            self._fdbk = self._cmd.past_limit_submission_fdbk_config
        elif fdbk_category == FeedbackCategory.staff_viewer:
            self._fdbk = self._cmd.staff_viewer_fdbk_config
        elif fdbk_category == FeedbackCategory.max:
            self._fdbk = AGTestCommandFeedbackConfig(**MAX_AG_TEST_COMMAND_FDBK_SETTINGS)

    @property
    def pk(self):
        return self._ag_test_command_result.pk

    @property
    def ag_test_command_name(self) -> str:
        return self._cmd.name

    @property
    def ag_test_command_pk(self) -> pk:
        return self._cmd.pk

    @property
    def fdbk_conf(self) -> AGTestCommandFeedbackConfig:
        """
        :return: The FeedbackConfig object that this object was
        initialized with.
        """
        return self._fdbk

    @property
    def fdbk_settings(self) -> dict:
        return self.fdbk_conf.to_dict()

    @property
    def timed_out(self) -> Optional[bool]:
        if self._fdbk.show_whether_timed_out:
            return self._ag_test_command_result.timed_out

        return None

    @property
    def return_code_correct(self) -> Optional[bool]:
        if (self._cmd.expected_return_code == ExpectedReturnCode.none
                or self._fdbk.return_code_fdbk_level == ValueFeedbackLevel.no_feedback):
            return None

        return self._ag_test_command_result.return_code_correct

    @property
    def expected_return_code(self) -> Optional[ValueFeedbackLevel]:
        if self._fdbk.return_code_fdbk_level != ValueFeedbackLevel.expected_and_actual:
            return None

        return self._cmd.expected_return_code

    @property
    def actual_return_code(self) -> Optional[int]:
        if (self._fdbk.return_code_fdbk_level == ValueFeedbackLevel.expected_and_actual
                or self._fdbk.show_actual_return_code):
            return self._ag_test_command_result.return_code

        return None

    @property
    def return_code_points(self) -> int:
        if self.return_code_correct is None:
            return 0

        if self._ag_test_command_result.return_code_correct:
            return self._cmd.points_for_correct_return_code
        return self._cmd.deduction_for_wrong_return_code

    @property
    def return_code_points_possible(self) -> int:
        if self.return_code_correct is None:
            return 0

        return self._cmd.points_for_correct_return_code

    @property
    def stdout_correct(self) -> Optional[bool]:
        if (self._cmd.expected_stdout_source == ExpectedOutputSource.none
                or self._fdbk.stdout_fdbk_level == ValueFeedbackLevel.no_feedback):
            return None

        return self._ag_test_command_result.stdout_correct

    @property
    def stdout(self) -> Optional[BinaryIO]:
        if (self._fdbk.show_actual_stdout
                or self._fdbk.stdout_fdbk_level == ValueFeedbackLevel.expected_and_actual):
            return open(self._ag_test_command_result.stdout_filename, 'rb')

        return None

    @property
    def stdout_diff(self) -> Optional[core_ut.DiffResult]:
        if (self._cmd.expected_stdout_source == ExpectedOutputSource.none
                or self._fdbk.stdout_fdbk_level != ValueFeedbackLevel.expected_and_actual):
            return None

        stdout_filename = self._ag_test_command_result.stdout_filename
        diff_whitespace_kwargs = {
            'ignore_blank_lines': self._cmd.ignore_blank_lines,
            'ignore_case': self._cmd.ignore_case,
            'ignore_whitespace': self._cmd.ignore_whitespace,
            'ignore_whitespace_changes': self._cmd.ignore_whitespace_changes
        }

        # check source and return diff
        if self._cmd.expected_stdout_source == ExpectedOutputSource.text:
            with tempfile.NamedTemporaryFile('w') as expected_stdout:
                expected_stdout.write(self._cmd.expected_stdout_text)
                expected_stdout.flush()
                return core_ut.get_diff(expected_stdout.name, stdout_filename,
                                        **diff_whitespace_kwargs)
        elif self._cmd.expected_stdout_source == ExpectedOutputSource.instructor_file:
            return core_ut.get_diff(self._cmd.expected_stdout_instructor_file.abspath,
                                    stdout_filename,
                                    **diff_whitespace_kwargs)
        else:
            raise ValueError(
                'Invalid expected stdout source: {}'.format(self._cmd.expected_stdout_source))

    @property
    def stdout_points(self) -> int:
        if self.stdout_correct is None:
            return 0

        if self._ag_test_command_result.stdout_correct:
            return self._cmd.points_for_correct_stdout

        return self._cmd.deduction_for_wrong_stdout

    @property
    def stdout_points_possible(self) -> int:
        if self.stdout_correct is None:
            return 0

        return self._cmd.points_for_correct_stdout

    @property
    def stderr_correct(self) -> Optional[bool]:
        if (self._cmd.expected_stderr_source == ExpectedOutputSource.none
                or self._fdbk.stderr_fdbk_level == ValueFeedbackLevel.no_feedback):
            return None

        return self._ag_test_command_result.stderr_correct

    @property
    def stderr(self) -> Optional[BinaryIO]:
        if (self._fdbk.show_actual_stderr
                or self._fdbk.stderr_fdbk_level == ValueFeedbackLevel.expected_and_actual):
            return open(self._ag_test_command_result.stderr_filename, 'rb')

        return None

    @property
    def stderr_diff(self) -> Optional[core_ut.DiffResult]:
        if (self._cmd.expected_stderr_source == ExpectedOutputSource.none
                or self._fdbk.stderr_fdbk_level != ValueFeedbackLevel.expected_and_actual):
            return None

        stderr_filename = self._ag_test_command_result.stderr_filename
        diff_whitespace_kwargs = {
            'ignore_blank_lines': self._cmd.ignore_blank_lines,
            'ignore_case': self._cmd.ignore_case,
            'ignore_whitespace': self._cmd.ignore_whitespace,
            'ignore_whitespace_changes': self._cmd.ignore_whitespace_changes
        }

        if self._cmd.expected_stderr_source == ExpectedOutputSource.text:
            with tempfile.NamedTemporaryFile('w') as expected_stderr:
                expected_stderr.write(self._cmd.expected_stderr_text)
                expected_stderr.flush()
                return core_ut.get_diff(expected_stderr.name, stderr_filename,
                                        **diff_whitespace_kwargs)
        elif self._cmd.expected_stderr_source == ExpectedOutputSource.instructor_file:
            return core_ut.get_diff(self._cmd.expected_stderr_instructor_file.abspath,
                                    stderr_filename,
                                    **diff_whitespace_kwargs)
        else:
            raise ValueError(
                'Invalid expected stderr source: {}'.format(self._cmd.expected_stdout_source))

    @property
    def stderr_points(self) -> int:
        if self.stderr_correct is None:
            return 0

        if self._ag_test_command_result.stderr_correct:
            return self._cmd.points_for_correct_stderr

        return self._cmd.deduction_for_wrong_stderr

    @property
    def stderr_points_possible(self) -> int:
        if self.stderr_correct is None:
            return 0

        return self._cmd.points_for_correct_stderr

    @property
    def total_points(self) -> int:
        if not self._fdbk.show_points:
            return 0

        return self.return_code_points + self.stdout_points + self.stderr_points

    @property
    def total_points_possible(self) -> int:
        if not self._fdbk.show_points:
            return 0

        return (self.return_code_points_possible + self.stdout_points_possible
                + self.stderr_points_possible)

    SERIALIZABLE_FIELDS = (
        'pk',
        'ag_test_command_pk',
        'ag_test_command_name',
        'fdbk_settings',

        'timed_out',

        'return_code_correct',
        'expected_return_code',
        'actual_return_code',
        'return_code_points',
        'return_code_points_possible',

        'stdout_correct',
        'stdout_points',
        'stdout_points_possible',

        'stderr_correct',
        'stderr_points',
        'stderr_points_possible',

        'total_points',
        'total_points_possible'
    )
