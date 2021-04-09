from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Dict, List, Optional, cast

from django.contrib.postgres import fields as pg_fields
from django.db import models

import autograder.core.utils as core_ut
from autograder.core.constants import MAX_CHAR_FIELD_LEN

from ..ag_command import AGCommandResult
from ..ag_command.command import Command
from ..ag_model_base import AutograderModel, AutograderModelManager, ToDictMixin
from ..ag_test.feedback_category import FeedbackCategory
from .mutation_test_suite import (
    BugsExposedFeedbackLevel, MutationTestSuite, MutationTestSuiteFeedbackConfig
)

if TYPE_CHECKING:
    from autograder.core.submission_feedback import MutationTestSuitePreLoader


def _make_get_test_names_result_default() -> int:
    return cast(int, AGCommandResult.objects.validate_and_create().pk)


class MutationTestSuiteResult(AutograderModel):
    objects = AutograderModelManager['MutationTestSuiteResult']()

    class Meta:
        unique_together = ('mutation_test_suite', 'submission')
        ordering = ('mutation_test_suite___order',)

    mutation_test_suite = models.ForeignKey(MutationTestSuite, on_delete=models.CASCADE)
    submission = models.ForeignKey('Submission', related_name='mutation_test_suite_results',
                                   on_delete=models.CASCADE)

    student_tests = pg_fields.ArrayField(
        models.CharField(max_length=MAX_CHAR_FIELD_LEN, blank=False),
        blank=True, default=list,
        help_text="The names of discovered student test cases.")
    discarded_tests = pg_fields.ArrayField(
        models.CharField(max_length=MAX_CHAR_FIELD_LEN, blank=False),
        blank=True, default=list,
        help_text=""""The names of student tests that were discarded due
                      to too many tests being discovered.""")
    invalid_tests = pg_fields.ArrayField(
        models.CharField(max_length=MAX_CHAR_FIELD_LEN, blank=False),
        blank=True, default=list,
        help_text="The names of student test cases that failed the validity check.")
    timed_out_tests = pg_fields.ArrayField(
        models.CharField(max_length=MAX_CHAR_FIELD_LEN, blank=False),
        blank=True, default=list,
        help_text="The names of student test cases that timed out during the validity check.")

    bugs_exposed = pg_fields.ArrayField(
        models.CharField(max_length=MAX_CHAR_FIELD_LEN, blank=False),
        blank=True, default=list,
        help_text="""The names of instructor buggy implementations that were exposed
                     by the student's test cases.""")

    setup_result = models.OneToOneField(
        AGCommandResult,
        on_delete=models.PROTECT,
        blank=True, null=True, default=None, related_name='+')
    get_test_names_result = models.OneToOneField(
        AGCommandResult,
        on_delete=models.PROTECT,
        default=_make_get_test_names_result_default, related_name='+')

    @property
    def validity_check_stdout_filename(self) -> str:
        return os.path.join(core_ut.get_result_output_dir(self.submission),
                            'student_suite_result_{}_validity_check_stdout'.format(self.pk))

    @property
    def validity_check_stderr_filename(self) -> str:
        return os.path.join(core_ut.get_result_output_dir(self.submission),
                            'student_suite_result_{}_validity_check_stderr'.format(self.pk))

    @property
    def grade_buggy_impls_stdout_filename(self) -> str:
        return os.path.join(core_ut.get_result_output_dir(self.submission),
                            'student_suite_result_{}_grade_buggy_impls_stdout'.format(self.pk))

    @property
    def grade_buggy_impls_stderr_filename(self) -> str:
        return os.path.join(core_ut.get_result_output_dir(self.submission),
                            'student_suite_result_{}_grade_buggy_impls_stderr'.format(self.pk))

    def save(self, *args: Any, **kwargs: Any) -> None:
        is_create = self.pk is None
        super().save(*args, **kwargs)

        if is_create:
            # The result output dir is created by self.submission
            open(self.validity_check_stdout_filename, 'w').close()
            open(self.validity_check_stderr_filename, 'w').close()
            open(self.grade_buggy_impls_stdout_filename, 'w').close()
            open(self.grade_buggy_impls_stderr_filename, 'w').close()

    def get_fdbk(
        self,
        fdbk_category: FeedbackCategory,
        mutation_test_suite_preloader: MutationTestSuitePreLoader
    ) -> MutationTestSuiteResult.FeedbackCalculator:
        return MutationTestSuiteResult.FeedbackCalculator(
            self, fdbk_category, mutation_test_suite_preloader)

    class FeedbackCalculator(ToDictMixin):
        """
        Instances of this class dynamically calculate the appropriate
        feedback data to give for a MutationTestSuiteResult
        """

        _fdbk: MutationTestSuiteFeedbackConfig

        def __init__(self, mutation_test_suite_result: MutationTestSuiteResult,
                     fdbk_category: FeedbackCategory,
                     mutation_test_suite_preloader: 'MutationTestSuitePreLoader'):
            self._mutation_test_suite_result = mutation_test_suite_result
            self._mutation_test_suite = mutation_test_suite_preloader.get_mutation_test_suite(
                self._mutation_test_suite_result.mutation_test_suite_id)

            if fdbk_category == FeedbackCategory.normal:
                self._fdbk = self._mutation_test_suite.normal_fdbk_config
            elif fdbk_category == FeedbackCategory.ultimate_submission:
                self._fdbk = self._mutation_test_suite.ultimate_submission_fdbk_config
            elif fdbk_category == FeedbackCategory.past_limit_submission:
                self._fdbk = self._mutation_test_suite.past_limit_submission_fdbk_config
            elif fdbk_category == FeedbackCategory.staff_viewer:
                self._fdbk = self._mutation_test_suite.staff_viewer_fdbk_config
            elif fdbk_category == FeedbackCategory.max:
                self._fdbk = MutationTestSuiteFeedbackConfig.max_fdbk_config()
            else:
                assert False, f'Unexpected feedback category "{fdbk_category}"'

        @property
        def pk(self) -> int:
            return cast(int, self._mutation_test_suite_result.pk)

        @property
        def mutation_test_suite_name(self) -> str:
            return self._mutation_test_suite.name

        @property
        def mutation_test_suite_pk(self) -> int:
            return cast(int, self._mutation_test_suite.pk)

        @property
        def fdbk_conf(self) -> MutationTestSuiteFeedbackConfig:
            """
            :return: The MutationTestSuiteFeedbackConfig object that this object
                     was initialized with.
            """
            return self._fdbk

        @property
        def fdbk_settings(self) -> Dict[str, object]:
            """
            A dictionary representation of this object's feedback config.
            """
            return self.fdbk_conf.to_dict()

        @property
        def has_setup_command(self) -> bool:
            return self._mutation_test_suite.use_setup_command

        @property
        def setup_command_name(self) -> Optional[str]:
            if not self._mutation_test_suite.use_setup_command:
                return None

            return cast(Command, self._mutation_test_suite.setup_command).name

        @property
        def setup_return_code(self) -> Optional[int]:
            if not self._fdbk.show_setup_return_code:
                return None

            if self._mutation_test_suite_result.setup_result is None:
                return None

            return self._mutation_test_suite_result.setup_result.return_code

        @property
        def setup_timed_out(self) -> Optional[bool]:
            if not self._fdbk.show_setup_return_code:
                return None

            if self._mutation_test_suite_result.setup_result is None:
                return None

            return self._mutation_test_suite_result.setup_result.timed_out

        @property
        def setup_stdout(self) -> Optional[BinaryIO]:
            if (filename := self.setup_stdout_filename) is None:
                return None

            return open(filename, 'rb')

        @property
        def setup_stdout_filename(self) -> Path | None:
            if not self._show_setup_stdout:
                return None

            assert self._mutation_test_suite_result.setup_result is not None
            return Path(self._mutation_test_suite_result.setup_result.stdout_filename)

        def get_setup_stdout_size(self) -> Optional[int]:
            if not self._show_setup_stdout:
                return None

            assert self._mutation_test_suite_result.setup_result is not None
            return os.path.getsize(self._mutation_test_suite_result.setup_result.stdout_filename)

        @property
        def _show_setup_stdout(self) -> bool:
            return (self._fdbk.show_setup_stdout
                    and self._mutation_test_suite_result.setup_result is not None)

        @property
        def setup_stderr(self) -> Optional[BinaryIO]:
            if (filename := self.setup_stderr_filename) is None:
                return None

            return open(filename, 'rb')

        @property
        def setup_stderr_filename(self) -> Path | None:
            if not self._show_setup_stderr:
                return None

            assert self._mutation_test_suite_result.setup_result is not None
            return Path(self._mutation_test_suite_result.setup_result.stderr_filename)

        def get_setup_stderr_size(self) -> Optional[int]:
            if not self._show_setup_stderr:
                return None

            assert self._mutation_test_suite_result.setup_result is not None
            return os.path.getsize(self._mutation_test_suite_result.setup_result.stderr_filename)

        @property
        def _show_setup_stderr(self) -> bool:
            return (self._fdbk.show_setup_stderr
                    and self._mutation_test_suite_result.setup_result is not None)

        @property
        def student_tests(self) -> List[str]:
            return self._mutation_test_suite_result.student_tests

        @property
        def discarded_tests(self) -> List[str]:
            return self._mutation_test_suite_result.discarded_tests

        @property
        def invalid_tests(self) -> Optional[List[str]]:
            if not self._fdbk.show_invalid_test_names:
                return None

            return self._mutation_test_suite_result.invalid_tests

        @property
        def timed_out_tests(self) -> Optional[List[str]]:
            if not self._fdbk.show_invalid_test_names:
                return None

            return self._mutation_test_suite_result.timed_out_tests

        @property
        def get_student_test_names_return_code(self) -> Optional[int]:
            if not self._fdbk.show_get_test_names_return_code:
                return None

            return self._mutation_test_suite_result.get_test_names_result.return_code

        @property
        def get_student_test_names_timed_out(self) -> Optional[bool]:
            if self.get_student_test_names_return_code is None:
                return None

            return self._mutation_test_suite_result.get_test_names_result.timed_out

        @property
        def get_student_test_names_stdout(self) -> Optional[BinaryIO]:
            if (filename := self.get_student_test_names_stdout_filename) is None:
                return None

            return open(filename, 'rb')

        @property
        def get_student_test_names_stdout_filename(self) -> Path | None:
            if not self._fdbk.show_get_test_names_stdout:
                return None

            return Path(self._mutation_test_suite_result.get_test_names_result.stdout_filename)

        def get_student_test_names_stdout_size(self) -> Optional[int]:
            if not self._fdbk.show_get_test_names_stdout:
                return None

            return os.path.getsize(
                self._mutation_test_suite_result.get_test_names_result.stdout_filename)

        @property
        def get_student_test_names_stderr(self) -> Optional[BinaryIO]:
            if (filename := self.get_student_test_names_stderr_filename) is None:
                return None

            return open(filename, 'rb')

        @property
        def get_student_test_names_stderr_filename(self) -> Path | None:
            if not self._fdbk.show_get_test_names_stderr:
                return None

            return Path(self._mutation_test_suite_result.get_test_names_result.stderr_filename)

        def get_student_test_names_stderr_size(self) -> Optional[int]:
            if not self._fdbk.show_get_test_names_stderr:
                return None

            return os.path.getsize(
                self._mutation_test_suite_result.get_test_names_result.stderr_filename)

        @property
        def num_bugs_exposed(self) -> Optional[int]:
            if self._fdbk.bugs_exposed_fdbk_level < BugsExposedFeedbackLevel.num_bugs_exposed:
                return None

            return len(self._mutation_test_suite_result.bugs_exposed)

        @property
        def bugs_exposed(self) -> Optional[List[str]]:
            if self._fdbk.bugs_exposed_fdbk_level < BugsExposedFeedbackLevel.exposed_bug_names:
                return None

            return self._mutation_test_suite_result.bugs_exposed

        @property
        def all_bug_names(self) -> Optional[List[str]]:
            if self._fdbk.bugs_exposed_fdbk_level < BugsExposedFeedbackLevel.all_bug_names:
                return None

            return self._mutation_test_suite.buggy_impl_names

        @property
        def validity_check_stdout(self) -> Optional[BinaryIO]:
            if (filename := self.validity_check_stdout_filename) is None:
                return None

            return open(filename, 'rb')

        @property
        def validity_check_stdout_filename(self) -> Path | None:
            if not self._fdbk.show_validity_check_stdout:
                return None

            return Path(self._mutation_test_suite_result.validity_check_stdout_filename)

        def get_validity_check_stdout_size(self) -> Optional[int]:
            if not self._fdbk.show_validity_check_stdout:
                return None

            return os.path.getsize(self._mutation_test_suite_result.validity_check_stdout_filename)

        @property
        def validity_check_stderr(self) -> Optional[BinaryIO]:
            if (filename := self.validity_check_stderr_filename) is None:
                return None

            return open(filename, 'rb')

        @property
        def validity_check_stderr_filename(self) -> Path | None:
            if not self._fdbk.show_validity_check_stderr:
                return None

            return Path(self._mutation_test_suite_result.validity_check_stderr_filename)

        def get_validity_check_stderr_size(self) -> Optional[int]:
            if not self._fdbk.show_validity_check_stderr:
                return None

            return os.path.getsize(
                self._mutation_test_suite_result.validity_check_stderr_filename)

        @property
        def grade_buggy_impls_stdout(self) -> Optional[BinaryIO]:
            if (filename := self.grade_buggy_impls_stdout_filename) is None:
                return None

            return open(filename, 'rb')

        @property
        def grade_buggy_impls_stdout_filename(self) -> Path | None:
            if not self._fdbk.show_grade_buggy_impls_stdout:
                return None

            return Path(self._mutation_test_suite_result.grade_buggy_impls_stdout_filename)

        def get_grade_buggy_impls_stdout_size(self) -> Optional[int]:
            if not self._fdbk.show_grade_buggy_impls_stdout:
                return None

            return os.path.getsize(
                self._mutation_test_suite_result.grade_buggy_impls_stdout_filename)

        @property
        def grade_buggy_impls_stderr(self) -> Optional[BinaryIO]:
            if (filename := self.grade_buggy_impls_stderr_filename) is None:
                return None

            return open(filename, 'rb')

        @property
        def grade_buggy_impls_stderr_filename(self) -> Path | None:
            if not self._fdbk.show_grade_buggy_impls_stderr:
                return None

            return Path(self._mutation_test_suite_result.grade_buggy_impls_stderr_filename)

        def get_grade_buggy_impls_stderr_size(self) -> Optional[int]:
            if not self._fdbk.show_grade_buggy_impls_stderr:
                return None

            return os.path.getsize(
                self._mutation_test_suite_result.grade_buggy_impls_stderr_filename)

        @property
        def total_points(self) -> Decimal:
            if self.num_bugs_exposed is None:
                return Decimal(0)

            return min(self.total_points_possible,
                       self.num_bugs_exposed * self._mutation_test_suite.points_per_exposed_bug)

        @property
        def total_points_possible(self) -> Decimal:
            if not self._fdbk.show_points or self.num_bugs_exposed is None:
                return Decimal(0)

            if self._mutation_test_suite.max_points is not None:
                return Decimal(self._mutation_test_suite.max_points)

            return (len(self._mutation_test_suite.buggy_impl_names)
                    * self._mutation_test_suite.points_per_exposed_bug)

        SERIALIZABLE_FIELDS = (
            'pk',
            'mutation_test_suite_name',
            'mutation_test_suite_pk',
            'fdbk_settings',
            'has_setup_command',
            'setup_command_name',
            'setup_return_code',
            'setup_timed_out',
            'get_student_test_names_return_code',
            'get_student_test_names_timed_out',
            'student_tests',
            'discarded_tests',
            'invalid_tests',
            'timed_out_tests',
            'num_bugs_exposed',
            'bugs_exposed',
            'all_bug_names',
            'total_points',
            'total_points_possible',
        )
