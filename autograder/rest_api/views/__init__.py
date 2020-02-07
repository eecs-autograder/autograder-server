from .ag_test_views.ag_test_case_views import (
    AGTestCaseListCreateView, AGTestCaseOrderView, AGTestCaseDetailViewSet)
from .ag_test_views.ag_test_command_views import (
    AGTestCommandListCreateView, AGTestCommandOrderView, AGTestCommandDetailViewSet)
from .ag_test_views.ag_test_suite_views import (
    AGTestSuiteListCreateView, AGTestSuiteOrderView, AGTestSuiteDetailViewSet)

from .sandbox_docker_image_views import (
    ListCreateSandboxDockerImageViewSet,
    SandboxDockerImageDetailViewSet,
    SandboxDockerImageForCourseViewSet)

from .course_views.course_admins import CourseAdminViewSet
from .course_views.course_handgraders import CourseHandgradersViewSet
from .course_views.course_staff import CourseStaffViewSet
from .course_views.course_students import CourseStudentsViewSet
from .course_views.course_views import CourseViewSet, CourseByNameSemesterYearView, CopyCourseView

from .group_invitation_views import ListCreateGroupInvitationViewSet, GroupInvitationDetailViewSet
from .group_views import GroupsViewSet, CreateSoloGroupView, GroupDetailViewSet

from .oauth2callback import oauth2_callback

from autograder.rest_api.views.project_views.expected_student_file_views import (
    ExpectedStudentFilePatternDetailViewSet, ListCreateExpectedStudentFilesViewSet)

from .project_views.instructor_file_views import (
    ListCreateInstructorFilesViewSet, InstructorFileDetailViewSet, InstructorFileContentView)
from .project_views.project_views import (
    ProjectDetailViewSet,
    ListCreateProjectView,
    CopyProjectView,
    ImportHandgradingRubricView,
    DownloadTaskDetailViewSet,
    EditBonusSubmissionsView
)

from .rerun_submissions_task_views import (
    RerunSubmissionsTaskListCreateView, RerunSubmissionsTaskDetailVewSet)
from .student_test_suite_views import (
    StudentTestSuiteListCreateView, StudentTestSuiteOrderView, StudentTestSuiteDetailViewSet)

from .submission_views.submission_views import (
    ListCreateSubmissionViewSet,
    ListSubmissionsWithResults,
    SubmissionDetailViewSet
)

from .submission_views.submission_result_views import (
    SubmissionResultsView,
    AGTestSuiteResultsStdoutView,
    AGTestSuiteResultsStderrView,
    AGTestSuiteResultsOutputSizeView,
    AGTestCommandResultStdoutView,
    AGTestCommandResultStderrView,
    AGTestCommandResultStdoutDiffView,
    AGTestCommandResultStderrDiffView,
    AGTestCommandResultOutputSizeView,

    StudentTestSuiteResultSetupStdoutView,
    StudentTestSuiteResultSetupStderrView,
    StudentTestSuiteResultGetStudentTestsStdoutView,
    StudentTestSuiteResultGetStudentTestsStderrView,
    StudentTestSuiteResultValidityCheckStdoutView,
    StudentTestSuiteResultValidityCheckStderrView,
    StudentTestSuiteResultGradeBuggyImplsStdoutView,
    StudentTestSuiteResultGradeBuggyImplsStderrView,
    StudentTestSuiteOutputSizeView,
)

from .user_views import UserViewSet, CurrentUserCanCreateCoursesView, UserLateDaysView

from .submission_views.all_ultimate_submission_results_view import AllUltimateSubmissionResults
