from typing import List

from django.db import models

from autograder.core.models.ag_model_base import ToDictMixin
import autograder.core.constants as constants
import autograder.core.utils as core_ut

from ..ag_model_base import AutograderModel
from .ag_test_suite import AGTestSuite
from .ag_test_command import AGTestCommand, AGTestCommandFeedbackConfig, ExpectedReturnCode, ValueFeedbackLevel


class AGTestCommandResult(AutograderModel):
    """
    This class stores the data from an AGTestCommand
    and provides an interface for serializing the data with different
    feedback levels.
    """
    class Meta:
        unique_together = ('ag_test_command',)

    ag_test_command = models.ForeignKey(
        AGTestCommand, help_text='The AGTestCommand this result belongs to.')

    return_code = models.IntegerField(help_text='The return code of the completed command.')

    stdout = models.TextField(help_text='The stdout contents from running the command.')
    sterr = models.TextField(help_text='The stderr contents from running the command.')

    timed_out = models.BooleanField(help_text='Whether the program exceeded the time limit.')

    stdout_diff = models.TextField(
        help_text='''If the AGTestCommand this result belongs to checks stdout,
                     this field will store a diff of the expected and actual stdout contents.''')

    stderr_diff = models.TextField(
        help_text='''If the AGTestCommand this result belongs to checks stderr,
                     this field will store a diff of the expected and actual stderr contents.''')

    return_code_correct = models.BooleanField(null=True, default=None)
    stdout_correct = models.BooleanField(null=True, default=None)
    stderr_correct = models.BooleanField(null=True, default=None)

    def save(self, *args, **kwargs):
        self._check_len_and_truncate('stdout')
        self._check_len_and_truncate('stderr')

        super().save(*args, **kwargs)

    def _check_len_and_truncate(self, field_name):
        value = getattr(self, field_name)
        if len(value) > constants.MAX_OUTPUT_LENGTH:
            setattr(self, field_name,
                    value[:constants.MAX_OUTPUT_LENGTH] + '\nOutput truncated')

    def get_normal_feedback(self):
        '''
        Returns a FeedbackCalculator object for this result initialized
        with self.ag_test_command.normal_fdbk_config as its feedback
        config.
        '''
        return AGTestCommandResult.FeedbackCalculator(
            self, self.ag_test_command.normal_fdbk_config)

    def get_ultimate_submission_feedback(self):
        '''
        Returns a FeedbackCalculator object for this result initialized
        with self.ag_test_command.ultimate_submission_fdbk_config as its
        feedback config.
        '''
        return AGTestCommandResult.FeedbackCalculator(
            self, self.ag_test_command.ultimate_submission_fdbk_config)

    def get_staff_viewer_feedback(self):
        '''
        Returns a FeedbackCalculator object for this result initialized
        with self.ag_test_command.staff_viewer_fdbk_config as its feedback
        config.
        '''
        return AGTestCommandResult.FeedbackCalculator(
            self, self.ag_test_command.staff_viewer_fdbk_config)

    def get_past_submission_limit_feedback(self):
        '''
        Returns a FeedbackCalculator object for this result initialized
        with self.ag_test_command.past_limit_submission_fdbk_config as its
        feedback config.
        '''
        return AGTestCommandResult.FeedbackCalculator(
            self, self.ag_test_command.past_limit_submission_fdbk_config)

    def get_max_feedback(self):
        '''
        Returns a FeedbackCalculator object for this result initialized
        with maximum feedback settings.
        '''
        fdbk_settings = AGTestCommandFeedbackConfig(
            return_code_fdbk_level=ValueFeedbackLevel.get_max(),
            stdout_fdbk_level=ValueFeedbackLevel.get_max(),
            stderr_fdbk_level=ValueFeedbackLevel.get_max(),
            show_points=True,
            show_actual_return_code=True,
            show_actual_stdout=True,
            show_actual_stderr=True)

        return AGTestCommandResult.FeedbackCalculator(self, fdbk_settings)

    class FeedbackCalculator(ToDictMixin):
        """
        Instances of this class dynamically calculate the appropriate
        feedback data to give for an AGTestCommandResult.
        """

        def __init__(self, result: 'AGTestCommandResult',
                     fdbk_conf: 'AGTestCommandFeedbackConfig'):
            self._fdbk = fdbk_conf
            self._result = result

        SERIALIZABLE_FIELDS = (
            'ag_test_case_command',
            'ag_test_case_command_name',
            'status',

            'timed_out',

            'return_code_correct',
            'expected_return_code',
            'actual_return_code',
            'return_code_points',
            'return_code_points_possible',

            'stdout_correct',
            'stdout_content',
            'stdout_diff',
            'stdout_points',
            'stdout_points_possible',

            'stderr_correct',
            'stderr_content',
            'stderr_diff',
            'stderr_points',
            'stderr_points_possible',

            'total_points',
            'total_points_possible'
        )

        @property
        def fdbk_conf(self):
            """
            Returns the FeedbackConfig object that this object was
            initialized with.
            """
            return self._fdbk

        @property
        def pk(self):
            return self._result.pk

        @property
        def status(self):
            return self._result.status

        @property
        def ag_test_command_name(self):
            return self._result.ag_test_command.name

        @property
        def fdbk_settings(self) -> dict:
            return self._result.ag_test_command.

        @property
        def timed_out(self):
            raise NotImplementedError


        @property
        def return_code_correct(self):
            raise NotImplementedError


        @property
        def expected_return_code(self):
            raise NotImplementedError

        @property
        def actual_return_code(self):
            raise NotImplementedError

        @property
        def return_code_points(self):
            raise NotImplementedError

        @property
        def return_code_points_possible(self):
            raise NotImplementedError

        @property
        def stdout_correct(self):
            raise NotImplementedError

        @property
        def stdout_content(self):
            raise NotImplementedError

        @property
        def stdout_diff(self):
            raise NotImplementedError

        @property
        def stdout_points(self):
            raise NotImplementedError

        @property
        def stdout_points_possible(self):
            raise NotImplementedError

        @property
        def stderr_correct(self):
            raise NotImplementedError

        @property
        def stderr_content(self):
            raise NotImplementedError

        @property
        def stderr_diff(self):
            raise NotImplementedError

        @property
        def stderr_points(self):
            raise NotImplementedError

        @property
        def stderr_points_possible(self):
            raise NotImplementedError

        @property
        def total_points(self):
            return self.return_code_points + self.stdout_points + self.stderr_points

        @property
        def total_points_possible(self):
            return (self.return_code_points_possible + self.stdout_points_possible +
                    self.stderr_points_possible)
