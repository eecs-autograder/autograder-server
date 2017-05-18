# Import all Model classes here.

from .ag_model_base import AutograderModel, PolymorphicAutograderModel

from .notification import Notification

from .course import Course
from .project import Project
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


# These next imports need to be in this order to get around
# circular dependency.
from .autograder_test_case.autograder_test_case_result import AutograderTestCaseResult
# Note: Even though we are importing the different types of test cases here,
# you should only access them through the factory function below
from .autograder_test_case.autograder_test_case_base import AutograderTestCaseBase
from .autograder_test_case.compiled_autograder_test_case import (
    CompiledAutograderTestCase,
    CompiledAndRunAutograderTestCase,
    CompilationOnlyAutograderTestCase)
from .autograder_test_case.interpreted_autograder_test_case import InterpretedAutograderTestCase

from .autograder_test_case import AutograderTestCaseFactory

from .autograder_test_case.feedback_config import FeedbackConfig
