# Import all Model classes here.

from .ag_model_base import AutograderModel, PolymorphicAutograderModel

from .notification import Notification

from .course import Course, UserRole
from .project import Project, UltimateSubmissionPolicy
from .project.expected_student_file_pattern import ExpectedStudentFilePattern
from .project.uploaded_file import UploadedFile

from .submission_group import SubmissionGroup, SubmissionGroupInvitation
from .submission import Submission

from .ag_test.ag_test_suite import AGTestSuite, AGTestSuiteFeedbackConfig
from .ag_test.ag_test_case import AGTestCase, AGTestCaseFeedbackConfig
from .ag_test.ag_test_command import (
    AGTestCommand, AGTestCommandFeedbackConfig, ValueFeedbackLevel, StdinSource,
    ExpectedOutputSource, ExpectedOutputSource, ExpectedReturnCode)
from .ag_test.ag_test_suite_result import AGTestSuiteResult
from .ag_test.ag_test_case_result import AGTestCaseResult
from .ag_test.ag_test_command_result import AGTestCommandResult
from .ag_test.feedback_category import FeedbackCategory
