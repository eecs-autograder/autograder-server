import os
from io import FileIO
from typing import Sequence

from django.db import models

import autograder.core.fields as ag_fields
from .student_test_suite import (
    BugsExposedFeedbackLevel, StudentTestSuite, StudentTestSuiteFeedbackConfig,
    MAX_STUDENT_SUITE_FDBK_SETTINGS)
from ..ag_command import AGCommandResult
from ..ag_model_base import AutograderModel, ToDictMixin
from ..ag_test.feedback_category import FeedbackCategory

import autograder.core.utils as core_ut


def _make_get_test_names_result_default() -> int:
    return AGCommandResult.objects.validate_and_create().pk


class StudentTestSuiteResult(AutograderModel):

    class Meta:
        unique_together = ('student_test_suite', 'submission')
        ordering = ('student_test_suite___order',)

    student_test_suite = models.ForeignKey(StudentTestSuite, on_delete=models.CASCADE)
    submission = models.ForeignKey('Submission', related_name='student_test_suite_results',
                                   on_delete=models.CASCADE)

    student_tests = ag_fields.StringArrayField(
        blank=True, default=list,
        help_text="The names of discovered student test cases.")
    discarded_tests = ag_fields.StringArrayField(
        blank=True, default=list,
        help_text=""""The names of student tests that were discarded due
                      to too many tests being discovered.""")
    invalid_tests = ag_fields.StringArrayField(
        blank=True, default=list,
        help_text="The names of student test cases that failed the validity check.")
    timed_out_tests = ag_fields.StringArrayField(
        blank=True, default=list,
        help_text="The names of student test cases that timed out during the validity check.")

    bugs_exposed = ag_fields.StringArrayField(
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
    def validity_check_stdout_filename(self):
        return os.path.join(core_ut.get_result_output_dir(self.submission),
                            'student_suite_result_{}_validity_check_stdout'.format(self.pk))

    @property
    def validity_check_stderr_filename(self):
        return os.path.join(core_ut.get_result_output_dir(self.submission),
                            'student_suite_result_{}_validity_check_stderr'.format(self.pk))

    @property
    def grade_buggy_impls_stdout_filename(self):
        return os.path.join(core_ut.get_result_output_dir(self.submission),
                            'student_suite_result_{}_grade_buggy_impls_stdout'.format(self.pk))

    @property
    def grade_buggy_impls_stderr_filename(self):
        return os.path.join(core_ut.get_result_output_dir(self.submission),
                            'student_suite_result_{}_grade_buggy_impls_stderr'.format(self.pk))

    def save(self, *args, **kwargs):
        is_create = self.pk is None
        super().save(*args, **kwargs)

        if is_create:
            # The result output dir is created by self.submission
            open(self.validity_check_stdout_filename, 'w').close()
            open(self.validity_check_stderr_filename, 'w').close()
            open(self.grade_buggy_impls_stdout_filename, 'w').close()
            open(self.grade_buggy_impls_stderr_filename, 'w').close()

    def get_fdbk(self,
                 fdbk_category: FeedbackCategory) -> 'StudentTestSuiteResult.FeedbackCalculator':
        return StudentTestSuiteResult.FeedbackCalculator(self, fdbk_category)

    class FeedbackCalculator(ToDictMixin):
        """
        Instances of this class dynamically calculate the appropriate
        feedback data to give for a StudentTestSuiteResult
        """

        def __init__(self, student_test_suite_result: 'StudentTestSuiteResult',
                     fdbk_category: FeedbackCategory):
            self._student_test_suite_result = student_test_suite_result
            self._student_test_suite = self._student_test_suite_result.student_test_suite

            if fdbk_category == FeedbackCategory.normal:
                self._fdbk = self._student_test_suite.normal_fdbk_config
            elif fdbk_category == FeedbackCategory.ultimate_submission:
                self._fdbk = self._student_test_suite.ultimate_submission_fdbk_config
            elif fdbk_category == FeedbackCategory.past_limit_submission:
                self._fdbk = self._student_test_suite.past_limit_submission_fdbk_config
            elif fdbk_category == FeedbackCategory.staff_viewer:
                self._fdbk = self._student_test_suite.staff_viewer_fdbk_config
            elif fdbk_category == FeedbackCategory.max:
                self._fdbk = StudentTestSuiteFeedbackConfig(**MAX_STUDENT_SUITE_FDBK_SETTINGS)

        @property
        def pk(self):
            return self._student_test_suite_result.pk

        @property
        def student_test_suite_name(self):
            return self._student_test_suite.name

        @property
        def student_test_suite_pk(self):
            return self._student_test_suite.pk

        @property
        def fdbk_conf(self) -> StudentTestSuiteFeedbackConfig:
            """
            :return: The StudentTestCaseFeedbackConfig object that this object
                     was initialized with.
            """
            return self._fdbk

        @property
        def fdbk_settings(self) -> dict:
            """
            :return: A dictionary representation of this object's feedback config.
            """
            return self.fdbk_conf.to_dict()

        @property
        def has_setup_command(self) -> bool:
            return self._student_test_suite.use_setup_command

        @property
        def setup_command_name(self) -> str:
            if not self._student_test_suite.use_setup_command:
                return None

            return self._student_test_suite.setup_command.name

        @property
        def setup_return_code(self) -> int:
            if not self._fdbk.show_setup_return_code:
                return None

            if self._student_test_suite_result.setup_result is None:
                return None

            return self._student_test_suite_result.setup_result.return_code

        @property
        def setup_timed_out(self):
            if self.setup_return_code is None:
                return None

            return self._student_test_suite_result.setup_result.timed_out

        @property
        def setup_stdout(self) -> FileIO:
            if not self._fdbk.show_setup_stdout:
                return None

            if self._student_test_suite_result.setup_result is None:
                return None

            return open(self._student_test_suite_result.setup_result.stdout_filename, 'rb')

        @property
        def setup_stderr(self) -> FileIO:
            if not self._fdbk.show_setup_stderr:
                return None

            if self._student_test_suite_result.setup_result is None:
                return None

            return open(self._student_test_suite_result.setup_result.stderr_filename, 'rb')

        @property
        def student_tests(self) -> Sequence[str]:
            return self._student_test_suite_result.student_tests

        @property
        def discarded_tests(self):
            return self._student_test_suite_result.discarded_tests

        @property
        def invalid_tests(self) -> Sequence[str]:
            if not self._fdbk.show_invalid_test_names:
                return None

            return self._student_test_suite_result.invalid_tests

        @property
        def timed_out_tests(self) -> Sequence[str]:
            if not self._fdbk.show_invalid_test_names:
                return None

            return self._student_test_suite_result.timed_out_tests

        @property
        def get_student_test_names_return_code(self):
            if not self._fdbk.show_get_test_names_return_code:
                return None

            return self._student_test_suite_result.get_test_names_result.return_code

        @property
        def get_student_test_names_timed_out(self):
            if self.get_student_test_names_return_code is None:
                return None

            return self._student_test_suite_result.get_test_names_result.timed_out

        @property
        def get_student_test_names_stdout(self) -> FileIO:
            if not self._fdbk.show_get_test_names_stdout:
                return None

            return open(
                self._student_test_suite_result.get_test_names_result.stdout_filename, 'rb')

        @property
        def get_student_test_names_stderr(self) -> FileIO:
            if not self._fdbk.show_get_test_names_stderr:
                return None

            return open(
                self._student_test_suite_result.get_test_names_result.stderr_filename, 'rb')

        @property
        def num_bugs_exposed(self) -> int:
            if self._fdbk.bugs_exposed_fdbk_level < BugsExposedFeedbackLevel.num_bugs_exposed:
                return None

            return len(self._student_test_suite_result.bugs_exposed)

        @property
        def bugs_exposed(self) -> Sequence[str]:
            if self._fdbk.bugs_exposed_fdbk_level != BugsExposedFeedbackLevel.exposed_bug_names:
                return None

            return self._student_test_suite_result.bugs_exposed

        @property
        def validity_check_stdout(self) -> FileIO:
            if not self._fdbk.show_validity_check_stdout:
                return None

            return open(self._student_test_suite_result.validity_check_stdout_filename, 'rb')

        @property
        def validity_check_stderr(self) -> FileIO:
            if not self._fdbk.show_validity_check_stderr:
                return None

            return open(self._student_test_suite_result.validity_check_stderr_filename, 'rb')

        @property
        def grade_buggy_impls_stdout(self) -> FileIO:
            if not self._fdbk.show_grade_buggy_impls_stdout:
                return None

            return open(self._student_test_suite_result.grade_buggy_impls_stdout_filename, 'rb')

        @property
        def grade_buggy_impls_stderr(self) -> FileIO:
            if not self._fdbk.show_grade_buggy_impls_stderr:
                return None

            return open(self._student_test_suite_result.grade_buggy_impls_stderr_filename, 'rb')

        @property
        def total_points(self) -> int:
            if self.num_bugs_exposed is None:
                return 0

            return min(self.total_points_possible,
                       self.num_bugs_exposed * self._student_test_suite.points_per_exposed_bug)

        @property
        def total_points_possible(self) -> int:
            if not self._fdbk.show_points or self.num_bugs_exposed is None:
                return 0

            if self._student_test_suite.max_points is not None:
                return self._student_test_suite.max_points

            return (len(self._student_test_suite.buggy_impl_names) *
                    self._student_test_suite.points_per_exposed_bug)

        SERIALIZABLE_FIELDS = (
            'pk',
            'student_test_suite_name',
            'student_test_suite_pk',
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
            'total_points',
            'total_points_possible',
        )
