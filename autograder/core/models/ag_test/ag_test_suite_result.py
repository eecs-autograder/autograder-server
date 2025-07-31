import os
from typing import Dict

from django.db import models

from autograder.core.constants import COMPRESSED_OUTPUT_SUFFIX
import autograder.core.utils as core_ut

from ..ag_model_base import AutograderModel, AutograderModelManager
from .ag_test_suite import AGTestSuite


class AGTestSuiteResult(AutograderModel):
    objects = AutograderModelManager['AGTestSuiteResult']()

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

    setup_stdout_truncated = models.BooleanField(
        blank=True, default=False, help_text="Whether the setup command's stdout was truncated")
    setup_stderr_truncated = models.BooleanField(
        blank=True, default=False, help_text="Whether the setup command's stderr was truncated")

    @property
    def setup_stdout_filename(self) -> str:
        filename = os.path.join(
            core_ut.get_result_output_dir(self.submission),
            'suite_result_{}_setup_stdout'.format(self.pk)
        )
        return (
            filename + COMPRESSED_OUTPUT_SUFFIX
            if self.setup_stdout_size is not None else filename
        )

    @property
    def setup_stderr_filename(self) -> str:
        filename = os.path.join(
            core_ut.get_result_output_dir(self.submission),
            'suite_result_{}_setup_stderr'.format(self.pk)

        )
        return (
            filename + COMPRESSED_OUTPUT_SUFFIX
            if self.setup_stderr_size is not None else filename
        )

    setup_stdout_size = models.IntegerField(
        blank=True, null=True, default=None,
        help_text="""The size in bytes of the setup command's stdout. None indicates:
            - The 2025.08.0 output storage compression hasn't been applied to this object
              (i.e., the output is uncompressed)
            - The output size should be retrieved from the filesystem

            When non-None, stores the size in bytes of the output and indicates
            that the output is compressed using LZMA: https://docs.python.org/3/library/lzma.html

            When zero, there will be NO ACTUAL FILE stored in the filesystem
        """
    )

    setup_stderr_size = models.IntegerField(
        blank=True, null=True, default=None,
        help_text="""The size in bytes of the setup command's stderr. None indicates:
            - The 2025.08.0 output storage compression hasn't been applied to this object
              (i.e., the output is uncompressed)
            - The output size should be retrieved from the filesystem

            When non-None, stores the size in bytes of the output and indicates
            that the output is compressed using LZMA: https://docs.python.org/3/library/lzma.html

            When zero, there will be NO ACTUAL FILE stored in the filesystem
        """
    )

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
        'setup_stdout_size',
        'setup_stderr_size',
    )

    def to_dict(self) -> Dict[str, object]:
        result = super().to_dict()
        result['ag_test_case_results'] = {
            str(case_res.ag_test_case_id): case_res.to_dict()
            for case_res in self.ag_test_case_results.all()
        }

        return result
