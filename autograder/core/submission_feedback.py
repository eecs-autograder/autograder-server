from __future__ import annotations

import os
from decimal import Decimal
from typing import BinaryIO, Dict, List, Mapping, Optional, Sequence, TypedDict, Union, cast

from django.db import transaction
from django.db.models import Prefetch
from django.utils.functional import cached_property

from autograder.core.models import AGTestCommandResult, MutationTestSuiteResult, Submission
from autograder.core.models.ag_model_base import ToDictMixin
from autograder.core.models.ag_test.ag_test_case import AGTestCase, AGTestCaseFeedbackConfig
from autograder.core.models.ag_test.ag_test_case_result import AGTestCaseResult
from autograder.core.models.ag_test.ag_test_command import AGTestCommand
from autograder.core.models.ag_test.ag_test_suite import AGTestSuite, AGTestSuiteFeedbackConfig
from autograder.core.models.ag_test.ag_test_suite_result import AGTestSuiteResult
from autograder.core.models.ag_test.feedback_category import FeedbackCategory
from autograder.core.models.mutation_test_suite import MutationTestSuite
from autograder.core.models.project import Project

from . import utils as core_ut


class AGTestPreLoader:
    def __init__(self, project: Project):
        self._project = project

        self._suites_by_pk: Optional[Dict[int, AGTestSuite]] = None
        self._cases_by_pk: Optional[Dict[int, AGTestCase]] = None
        self._cmds_by_pk: Optional[Dict[int, AGTestCommand]] = None

    def get_ag_test_suite(self, suite_pk: int) -> AGTestSuite:
        return self._suites[suite_pk]

    @property
    def _suites(self) -> Dict[int, AGTestSuite]:
        if self._suites_by_pk is None:
            suites = AGTestSuite.objects.filter(project=self._project)
            self._suites_by_pk = {
                suite.pk: suite for suite in suites
            }

        return self._suites_by_pk

    def get_ag_test_case(self, case_pk: int) -> AGTestCase:
        return self._cases[case_pk]

    @property
    def _cases(self) -> Dict[int, AGTestCase]:
        if self._cases_by_pk is None:
            cases = AGTestCase.objects.filter(ag_test_suite__project=self._project)
            self._cases_by_pk = {
                case.pk: case for case in cases
            }

        return self._cases_by_pk

    def get_ag_test_cmd(self, cmd_pk: int) -> AGTestCommand:
        return self._cmds[cmd_pk]

    @property
    def _cmds(self) -> Dict[int, AGTestCommand]:
        if self._cmds_by_pk is None:
            cmds = AGTestCommand.objects.filter(ag_test_case__ag_test_suite__project=self._project)
            self._cmds_by_pk = {
                cmd.pk: cmd for cmd in cmds
            }

        return self._cmds_by_pk


class MutationTestSuitePreLoader:
    def __init__(self, project: Project):
        self._project = project
        self._suites_by_pk: Optional[Dict[int, MutationTestSuite]] = None

    def get_mutation_test_suite(self, suite_pk: int) -> MutationTestSuite:
        return self._suites[suite_pk]

    @property
    def _suites(self) -> Dict[int, MutationTestSuite]:
        if self._suites_by_pk is None:
            suites = MutationTestSuite.objects.filter(project=self._project)
            self._suites_by_pk = {
                suite.pk: suite for suite in suites
            }

        return self._suites_by_pk


# The primary key of an object as a string
PkStr = str


class AGTestSuiteResultDict(TypedDict):
    ag_test_case_results: Dict[PkStr, AGTestCaseResultDict]


class AGTestCaseResultDict(TypedDict):
    ag_test_command_results: Dict[PkStr, Dict[str, object]]


DenormedAGSuiteResType = Union[AGTestSuiteResult, 'SerializedAGTestSuiteResultWrapper']
DenormedAGCaseResType = Union[AGTestCaseResult, 'SerializedAGTestCaseResultWrapper']
DenormedAGCommandResType = Union[AGTestCommandResult, 'SerializedAGTestCommandResultWrapper']


class DenormalizedAGTestSuiteResult:
    def __init__(self, ag_test_suite_result: DenormedAGSuiteResType,
                 ag_test_case_results: List[DenormalizedAGTestCaseResult]):
        self.ag_test_suite_result = ag_test_suite_result
        self.ag_test_case_results = ag_test_case_results


class DenormalizedAGTestCaseResult:
    def __init__(self, ag_test_case_result: DenormedAGCaseResType,
                 ag_test_command_results: Sequence[DenormedAGCommandResType]):
        self.ag_test_case_result = ag_test_case_result
        self.ag_test_command_results = ag_test_command_results


class SerializedAGTestSuiteResultWrapper:
    def __init__(self, suite_result_dict: Mapping[str, object]):
        self._suite_result_dict = suite_result_dict

    @property
    def pk(self) -> int:
        return cast(int, self._suite_result_dict['pk'])

    @property
    def ag_test_suite_id(self) -> int:
        return cast(int, self._suite_result_dict['ag_test_suite_id'])

    @property
    def submission_id(self) -> int:
        return cast(int, self._suite_result_dict['submission_id'])

    @property
    def setup_return_code(self) -> int:
        return cast(int, self._suite_result_dict['setup_return_code'])

    @property
    def setup_timed_out(self) -> bool:
        return cast(bool, self._suite_result_dict['setup_timed_out'])

    @property
    def setup_stdout_truncated(self) -> bool:
        return cast(bool, self._suite_result_dict['setup_stdout_truncated'])

    @property
    def setup_stderr_truncated(self) -> bool:
        return cast(bool, self._suite_result_dict['setup_stderr_truncated'])

    # ------------------------------------------------------------------

    @property
    def setup_stdout_filename(self) -> str:
        return self._ag_test_suite_result.setup_stdout_filename

    @property
    def setup_stderr_filename(self) -> str:
        return self._ag_test_suite_result.setup_stderr_filename

    @cached_property
    def _ag_test_suite_result(self) -> AGTestSuiteResult:
        return AGTestSuiteResult.objects.get(pk=self.pk)


class SerializedAGTestCaseResultWrapper:
    def __init__(self, case_result_dict: Mapping[str, object]):
        self._case_result_dict = case_result_dict

    @property
    def pk(self) -> int:
        return cast(int, self._case_result_dict['pk'])

    @property
    def ag_test_case_id(self) -> int:
        return cast(int, self._case_result_dict['ag_test_case_id'])

    @property
    def ag_test_suite_result_id(self) -> int:
        return cast(int, self._case_result_dict['ag_test_suite_result_id'])


class SerializedAGTestCommandResultWrapper:
    def __init__(self, cmd_result_dict: Dict[str, object]):
        self._cmd_result_dict = cmd_result_dict

    @property
    def pk(self) -> int:
        return cast(int, self._cmd_result_dict['pk'])

    @property
    def ag_test_command_id(self) -> int:
        return cast(int, self._cmd_result_dict['ag_test_command_id'])

    @property
    def ag_test_case_result_id(self) -> int:
        return cast(int, self._cmd_result_dict['ag_test_case_result_id'])

    @property
    def return_code(self) -> int:
        return cast(int, self._cmd_result_dict['return_code'])

    @property
    def return_code_correct(self) -> bool:
        return cast(bool, self._cmd_result_dict['return_code_correct'])

    @property
    def stdout_correct(self) -> bool:
        return cast(bool, self._cmd_result_dict['stdout_correct'])

    @property
    def stderr_correct(self) -> bool:
        return cast(bool, self._cmd_result_dict['stderr_correct'])

    @property
    def timed_out(self) -> bool:
        return cast(bool, self._cmd_result_dict['timed_out'])

    @property
    def stdout_truncated(self) -> bool:
        return cast(bool, self._cmd_result_dict['stdout_truncated'])

    @property
    def stderr_truncated(self) -> bool:
        return cast(bool, self._cmd_result_dict['stderr_truncated'])

    # ------------------------------------------------------------------

    @property
    def stdout_filename(self) -> str:
        return self._ag_test_command_result.stdout_filename

    @property
    def stderr_filename(self) -> str:
        return self._ag_test_command_result.stderr_filename

    @cached_property
    def _ag_test_command_result(self) -> AGTestCommandResult:
        return AGTestCommandResult.objects.get(pk=self.pk)


def _deserialize_denormed_ag_test_results(
    submission: Submission
) -> List[DenormalizedAGTestSuiteResult]:
    result = []
    data = cast(Dict[PkStr, AGTestSuiteResultDict], submission.denormalized_ag_test_results)
    for serialized_suite_result in data.values():
        deserialized_suite_result = SerializedAGTestSuiteResultWrapper(serialized_suite_result)

        case_results = [
            _deserialize_denormed_ag_test_case_result(case_result)
            for case_result in serialized_suite_result['ag_test_case_results'].values()
        ]

        result.append(DenormalizedAGTestSuiteResult(deserialized_suite_result, case_results))

    return result


def _deserialize_denormed_ag_test_case_result(
    case_result: AGTestCaseResultDict
) -> DenormalizedAGTestCaseResult:
    deserialized_case_result = SerializedAGTestCaseResultWrapper(case_result)

    cmd_results = [
        _deserialize_denormed_ag_test_cmd_result(cmd_result)
        for cmd_result in case_result['ag_test_command_results'].values()
    ]

    return DenormalizedAGTestCaseResult(deserialized_case_result, cmd_results)


def _deserialize_denormed_ag_test_cmd_result(
    cmd_result: Dict[str, object]
) -> SerializedAGTestCommandResultWrapper:
    return SerializedAGTestCommandResultWrapper(cmd_result)


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


class SubmissionResultFeedback(ToDictMixin):
    def __init__(self, submission: Submission,
                 fdbk_category: FeedbackCategory,
                 ag_test_preloader: AGTestPreLoader,
                 mutation_test_suite_preloader: Optional[MutationTestSuitePreLoader]=None):
        self._submission = submission
        self._fdbk_category = fdbk_category
        self._project = self._submission.group.project

        self._ag_test_loader = ag_test_preloader
        self._mutation_test_suite_preloader = (
            mutation_test_suite_preloader if mutation_test_suite_preloader is not None
            else MutationTestSuitePreLoader(self._project))

        self._ag_test_suite_results = _deserialize_denormed_ag_test_results(self._submission)

    @property
    def ag_test_preloader(self) -> AGTestPreLoader:
        return self._ag_test_loader

    @property
    def mutation_test_suite_preloader(self) -> MutationTestSuitePreLoader:
        return self._mutation_test_suite_preloader

    @property
    def pk(self) -> int:
        return cast(int, self._submission.pk)

    @property
    def submission(self) -> Submission:
        return self._submission

    @cached_property
    def total_points(self) -> Union[int, Decimal]:
        ag_suite_points = sum((
            ag_test_suite_result.total_points
            for ag_test_suite_result in self.ag_test_suite_results
        ))

        mutation_suite_points = sum((
            fdbk.total_points for fdbk in self.mutation_test_suite_results
        ))

        return ag_suite_points + mutation_suite_points

    @cached_property
    def total_points_possible(self) -> Union[int, Decimal]:
        ag_suite_points = sum((
            ag_test_suite_result.total_points_possible
            for ag_test_suite_result in self.ag_test_suite_results
        ))

        mutation_suite_points = sum((
            fdbk.total_points_possible for fdbk in self.mutation_test_suite_results
        ))

        return ag_suite_points + mutation_suite_points

    @cached_property
    def ag_test_suite_results(self) -> List[AGTestSuiteResultFeedback]:
        visible = []
        for result in self._ag_test_suite_results:
            try:
                fdbk = AGTestSuiteResultFeedback(result, self._fdbk_category, self._ag_test_loader)
                if fdbk.fdbk_conf.visible:
                    visible.append(fdbk)
            except KeyError:
                # In certain rare cases, possibly caused by race condition when
                # deleting a suite/test/command at just the right time, a
                # submissions's denormalized AG test results can end up
                # contaning the PK for a suite/test/command that no longer
                # exists. Since this is unlikely to happen on a large scale,
                # we'll just ignore those elements.
                continue

        visible.sort(key=lambda item: item.ag_test_suite_order)
        return visible

    @cached_property
    def mutation_test_suite_results(self) -> List[MutationTestSuiteResult.FeedbackCalculator]:
        visible = []
        for result in self._submission.mutation_test_suite_results.all():
            fdbk = result.get_fdbk(self._fdbk_category, self._mutation_test_suite_preloader)
            if fdbk.fdbk_conf.visible:
                visible.append(fdbk)

        return visible

    def to_dict(self) -> Dict[str, object]:
        result = super().to_dict()

        result['ag_test_suite_results'] = [
            res_fdbk.to_dict() for res_fdbk in
            cast(List[AGTestSuiteResultFeedback], result['ag_test_suite_results'])
        ]

        result['mutation_test_suite_results'] = [
            result.to_dict() for result in
            cast(List[ToDictMixin], result['mutation_test_suite_results'])
        ]

        return result

    SERIALIZABLE_FIELDS = (
        'pk',
        'total_points',
        'total_points_possible',
        'ag_test_suite_results',
        'mutation_test_suite_results'
    )


class AGTestSuiteResultFeedback(ToDictMixin):
    _fdbk: AGTestSuiteFeedbackConfig

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
            self._fdbk = AGTestSuiteFeedbackConfig()

    @property
    def fdbk_conf(self) -> AGTestSuiteFeedbackConfig:
        return self._fdbk

    @property
    def pk(self) -> int:
        return self._ag_test_suite_result.pk

    @property
    def ag_test_suite_name(self) -> str:
        return self._ag_test_suite.name

    @property
    def ag_test_suite(self) -> AGTestSuite:
        return self._ag_test_suite

    @property
    def ag_test_suite_pk(self) -> int:
        return cast(int, self._ag_test_suite.pk)

    @property
    def ag_test_suite_order(self) -> int:
        return self._ag_test_suite._order  # type: ignore

    @property
    def fdbk_settings(self) -> Dict[str, object]:
        return self._fdbk.to_dict()

    @property
    def setup_name(self) -> Optional[str]:
        if not self._show_setup_name:
            return None

        return self._ag_test_suite.setup_suite_cmd_name

    @property
    def setup_return_code(self) -> Optional[int]:
        if not self._fdbk.show_setup_return_code:
            return None

        return self._ag_test_suite_result.setup_return_code

    @property
    def setup_timed_out(self) -> Optional[bool]:
        if not self._fdbk.show_setup_timed_out:
            return None

        return self._ag_test_suite_result.setup_timed_out

    @property
    def setup_stdout(self) -> Optional[BinaryIO]:
        if not self._fdbk.show_setup_stdout:
            return None

        return open(self._ag_test_suite_result.setup_stdout_filename, 'rb')

    def get_setup_stdout_size(self) -> Optional[int]:
        if not self._fdbk.show_setup_stderr:
            return None

        return os.path.getsize(self._ag_test_suite_result.setup_stdout_filename)

    @property
    def setup_stdout_truncated(self) -> Optional[bool]:
        if not self._fdbk.show_setup_stderr:
            return None

        return self._ag_test_suite_result.setup_stdout_truncated

    @property
    def setup_stderr(self) -> Optional[BinaryIO]:
        if not self._fdbk.show_setup_stderr:
            return None

        return open(self._ag_test_suite_result.setup_stderr_filename, 'rb')

    def get_setup_stderr_size(self) -> Optional[int]:
        if not self._fdbk.show_setup_stderr:
            return None

        return os.path.getsize(self._ag_test_suite_result.setup_stderr_filename)

    @property
    def setup_stderr_truncated(self) -> Optional[bool]:
        if not self._fdbk.show_setup_stderr:
            return None

        return self._ag_test_suite_result.setup_stderr_truncated

    @property
    def _show_setup_name(self):
        has_setup_result = (self._ag_test_suite_result.setup_return_code is not None
                            or self._ag_test_suite_result.setup_timed_out)
        setup_info_is_available = (
            self._fdbk.show_setup_stdout
            or self._fdbk.show_setup_stderr
            or self._fdbk.show_setup_return_code
            or self._fdbk.show_setup_timed_out
        )

        return has_setup_result and setup_info_is_available

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
    def ag_test_case_results(self) -> List[AGTestCaseResultFeedback]:
        if not self._fdbk.show_individual_tests:
            return []

        return self._visible_ag_test_case_results

    @cached_property
    def _visible_ag_test_case_results(self) -> List[AGTestCaseResultFeedback]:
        visible = []
        first_failure_found = False
        for result in self._ag_test_case_results:
            try:
                fdbk = AGTestCaseResultFeedback(
                    result, self._fdbk_category, self._ag_test_preloader)

                if (self._fdbk_category == FeedbackCategory.normal
                        and not first_failure_found
                        and fdbk.total_points < fdbk.total_points_possible):
                    first_failure_found = True
                    fdbk.is_first_failure = True

                if fdbk.fdbk_conf.visible:
                    visible.append(fdbk)
            except KeyError:  # See comment in AGTestSuiteResultFeedback.ag_test_suite_results
                continue

        visible.sort(key=lambda item: item.ag_test_case_order)
        return visible

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

        'ag_test_case_results'
    )

    def to_dict(self) -> Dict[str, object]:
        result = super().to_dict()
        result['ag_test_case_results'] = [
            res_fdbk.to_dict() for res_fdbk in
            cast(List[AGTestCaseResultFeedback], result['ag_test_case_results'])
        ]

        return result


class AGTestCaseResultFeedback(ToDictMixin):
    _fdbk: AGTestCaseFeedbackConfig

    def __init__(self, ag_test_case_result: DenormalizedAGTestCaseResult,
                 fdbk_category: FeedbackCategory,
                 ag_test_preloader: AGTestPreLoader,
                 is_first_failure: bool=False):
        self._denormalized_ag_test_case_result = ag_test_case_result
        self._ag_test_case_result = ag_test_case_result.ag_test_case_result
        self._ag_test_command_results = ag_test_case_result.ag_test_command_results
        self._fdbk_category = fdbk_category
        self._ag_test_preloader = ag_test_preloader

        self._ag_test_case = self._ag_test_preloader.get_ag_test_case(
            cast(int, self._ag_test_case_result.ag_test_case_id))

        if fdbk_category == FeedbackCategory.normal:
            self._fdbk = self._ag_test_case.normal_fdbk_config
        elif fdbk_category == FeedbackCategory.ultimate_submission:
            self._fdbk = self._ag_test_case.ultimate_submission_fdbk_config
        elif fdbk_category == FeedbackCategory.past_limit_submission:
            self._fdbk = self._ag_test_case.past_limit_submission_fdbk_config
        elif fdbk_category == FeedbackCategory.staff_viewer:
            self._fdbk = self._ag_test_case.staff_viewer_fdbk_config
        elif fdbk_category == FeedbackCategory.max:
            self._fdbk = AGTestCaseFeedbackConfig()
        else:
            assert False, f'Unexpected feedback category: {FeedbackCategory}'

        self.is_first_failure = is_first_failure

    @property
    def fdbk_conf(self) -> AGTestCaseFeedbackConfig:
        return self._fdbk

    @property
    def pk(self) -> int:
        return self._ag_test_case_result.pk

    @property
    def ag_test_case_name(self) -> str:
        return self._ag_test_case.name

    @property
    def ag_test_case_pk(self) -> int:
        return self._ag_test_case.pk

    @property
    def ag_test_case_order(self) -> int:
        return self._ag_test_case._order

    @property
    def denormalized_ag_test_case_result(self) -> DenormalizedAGTestCaseResult:
        return self._denormalized_ag_test_case_result

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
    def ag_test_command_results(self) -> List[AGTestCommandResultFeedback]:
        if not self._fdbk.show_individual_commands:
            return []

        return list(self._visible_cmd_results)

    @property
    def _visible_cmd_results(self) -> Iterable[AGTestCommandResultFeedback]:
        visible = []
        for result in self._ag_test_command_results:
            try:
                fdbk = AGTestCommandResultFeedback(
                    result, self._fdbk_category, self._ag_test_preloader,
                    is_in_first_failed_test=self.is_first_failure
                )
                if fdbk.fdbk_conf.visible:
                    visible.append(fdbk)
            except KeyError:  # See comment in AGTestSuiteResultFeedback.ag_test_suite_results
                continue

        visible.sort(key=lambda item: item.ag_test_command_order)
        return visible

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
                 ag_test_preloader: AGTestPreLoader,
                 is_in_first_failed_test: bool=False):
        self._ag_test_command_result = ag_test_command_result
        self._ag_test_preloader = ag_test_preloader

        self._cmd = self._ag_test_preloader.get_ag_test_cmd(
            self._ag_test_command_result.ag_test_command_id)

        self._is_in_first_failed_test = is_in_first_failed_test

        if fdbk_category == FeedbackCategory.normal:
            if (is_in_first_failed_test
                    and self._cmd.first_failed_test_normal_fdbk_config is not None):
                self._fdbk = self._cmd.first_failed_test_normal_fdbk_config
            else:
                self._fdbk = self._cmd.normal_fdbk_config
        elif fdbk_category == FeedbackCategory.ultimate_submission:
            self._fdbk = self._cmd.ultimate_submission_fdbk_config
        elif fdbk_category == FeedbackCategory.past_limit_submission:
            self._fdbk = self._cmd.past_limit_submission_fdbk_config
        elif fdbk_category == FeedbackCategory.staff_viewer:
            self._fdbk = self._cmd.staff_viewer_fdbk_config
        elif fdbk_category == FeedbackCategory.max:
            self._fdbk = AGTestCommandFeedbackConfig.max_fdbk_config()

    @property
    def pk(self):
        return self._ag_test_command_result.pk

    @property
    def ag_test_command_name(self) -> str:
        return self._cmd.name

    @property
    def ag_test_command_pk(self) -> int:
        return self._cmd.pk

    @property
    def ag_test_command_order(self) -> int:
        return self._cmd._order

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
    def expected_return_code(self) -> Optional[ExpectedReturnCode]:
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
        if self._show_actual_stdout:
            return open(self._ag_test_command_result.stdout_filename, 'rb')

        return None

    def get_stdout_size(self) -> Optional[int]:
        if self._show_actual_stdout:
            return os.path.getsize(self._ag_test_command_result.stdout_filename)

        return None

    @property
    def _show_actual_stdout(self) -> bool:
        return (self._fdbk.show_actual_stdout
                or self._fdbk.stdout_fdbk_level == ValueFeedbackLevel.expected_and_actual)

    @property
    def stdout_truncated(self) -> Optional[bool]:
        if self._show_actual_stdout:
            return self._ag_test_command_result.stdout_truncated

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

    def get_stdout_diff_size(self) -> Optional[int]:
        diff = self.stdout_diff
        if diff is None:
            return None

        return sum((len(line) for line in diff.diff_content))

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
        if self._show_actual_stderr:
            return open(self._ag_test_command_result.stderr_filename, 'rb')

        return None

    def get_stderr_size(self) -> Optional[int]:
        if self._show_actual_stderr:
            return os.path.getsize(self._ag_test_command_result.stderr_filename)

        return None

    @property
    def _show_actual_stderr(self):
        return (self._fdbk.show_actual_stderr
                or self._fdbk.stderr_fdbk_level == ValueFeedbackLevel.expected_and_actual)

    @property
    def stderr_truncated(self) -> Optional[bool]:
        if self._show_actual_stderr:
            return self._ag_test_command_result.stderr_truncated

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

    def get_stderr_diff_size(self) -> Optional[int]:
        diff = self.stderr_diff
        if diff is None:
            return None

        return sum((len(line) for line in diff.diff_content))

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
