import os

from django.db import models

import autograder.core.utils as core_ut
from ..ag_model_base import AutograderModel
from .ag_test_suite import AGTestSuite


class AGTestSuiteResult(AutograderModel):
    class Meta:
        unique_together = ('ag_test_suite', 'submission')
        ordering = ('ag_test_suite___order',)

    ag_test_suite = models.ForeignKey(
        AGTestSuite, on_delete=models.CASCADE,
        help_text='The AGTestSuite that this result belongs to.')

    submission = models.ForeignKey(
        'Submission', related_name='ag_test_suite_results',
        on_delete=models.CASCADE,
        help_text='The Submission that this result is for.')

    setup_return_code = models.IntegerField(
        blank=True, null=True, default=None,
        help_text="The return code of this suite's setup command.")
    setup_timed_out = models.BooleanField(
        blank=True, default=False,
        help_text="Whether this suite's setup command took too long to run.")
    setup_stdout = models.TextField(
        blank=True, help_text="The stdout content of this suite's setup command.")
    setup_stderr = models.TextField(
        blank=True, help_text="The stderr content of this suite's setup command.")
    setup_stdout_truncated = models.BooleanField(
        blank=True, default=False, help_text="Whether the setup command's stdout was truncated")
    setup_stderr_truncated = models.BooleanField(
        blank=True, default=False, help_text="Whether the setup command's stderr was truncated")

    teardown_return_code = models.IntegerField(
        blank=True, null=True, default=None,
        help_text="The return code of this suite's teardown command.")
    teardown_timed_out = models.BooleanField(
        blank=True, default=False,
        help_text="Whether this suite's teardown command took too long to run.")
    teardown_stdout = models.TextField(
        blank=True, help_text="The stdout content of this suite's teardown command.")
    teardown_stderr = models.TextField(
        blank=True, help_text="The stderr content of this suite's teardown command.")
    teardown_stdout_truncated = models.BooleanField(
        blank=True, default=False, help_text="Whether the teardown command's stdout was truncated")
    teardown_stderr_truncated = models.BooleanField(
        blank=True, default=False, help_text="Whether the teardown command's stderr was truncated")

    def open_setup_stdout(self, mode='rb'):
        return open(self.setup_stdout_filename, mode)

    @property
    def setup_stdout_filename(self):
        return os.path.join(core_ut.get_result_output_dir(self.submission),
                            'suite_result_{}_setup_stdout'.format(self.pk))

    def open_setup_stderr(self, mode='rb'):
        return open(self.setup_stderr_filename, mode)

    @property
    def setup_stderr_filename(self):
        return os.path.join(core_ut.get_result_output_dir(self.submission),
                            'suite_result_{}_setup_stderr'.format(self.pk))

    def open_teardown_stdout(self, mode='rb'):
        return open(self.teardown_stdout_filename, mode)

    @property
    def teardown_stdout_filename(self):
        return os.path.join(core_ut.get_result_output_dir(self.submission),
                            'suite_result_{}_teardown_stdout'.format(self.pk))

    def open_teardown_stderr(self, mode='rb'):
        return open(self.teardown_stderr_filename, mode)

    @property
    def teardown_stderr_filename(self):
        return os.path.join(core_ut.get_result_output_dir(self.submission),
                            'suite_result_{}_teardown_stderr'.format(self.pk))

    # Serializing AGTestSuiteResults should be used for DENORMALIZATION
    # ONLY.
    SERIALIZABLE_FIELDS = (
        'pk',

        'ag_test_suite_id',
        'submission_id',
        'setup_return_code',
        'setup_timed_out',
        'setup_stdout_truncated',
        'setup_stderr_truncated',
    )

    def to_dict(self):
        result = super().to_dict()
        result['ag_test_case_results'] = {
            case_res.ag_test_case_id: case_res.to_dict()
            for case_res in self.ag_test_case_results.all()
        }

        return result
