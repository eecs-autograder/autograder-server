from django.db import models

from ..ag_model_base import AutograderModel
from .ag_test_case import AGTestCase


class AGTestCaseResult(AutograderModel):
    class Meta:
        unique_together = ('ag_test_case', 'ag_test_suite_result')
        ordering = ('ag_test_case___order',)

    ag_test_case = models.ForeignKey(
        AGTestCase, related_name='related_ag_test_case_results',
        on_delete=models.CASCADE,
        help_text='The AGTestCase that this result belongs to.')

    ag_test_suite_result = models.ForeignKey(
        'AGTestSuiteResult', related_name='ag_test_case_results',
        on_delete=models.CASCADE,
        help_text='The AGTestSuiteResult that this result belongs to.')

    # Serializing AGTestCaseResults should be used for DENORMALIZATION
    # ONLY.
    SERIALIZABLE_FIELDS = (
        'pk',

        'ag_test_case_id',
        'ag_test_suite_result_id',
    )

    def to_dict(self):
        result = super().to_dict()
        result['ag_test_command_results'] = {
            str(cmd_res.ag_test_command_id): cmd_res.to_dict()
            for cmd_res in self.ag_test_command_results.all()
        }

        return result
