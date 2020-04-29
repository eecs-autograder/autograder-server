from .ag_test_views.ag_test_case_views import (AGTestCaseDetailView, AGTestCaseListCreateView,
                                               AGTestCaseOrderView)
from .ag_test_views.ag_test_command_views import (AGTestCommandDetailView,
                                                  AGTestCommandListCreateView,
                                                  AGTestCommandOrderView)
from .ag_test_views.ag_test_suite_views import (AGTestSuiteDetailView, AGTestSuiteListCreateView,
                                                AGTestSuiteOrderView)
from .course_views.course_admins import CourseAdminViewSet
from .course_views.course_handgraders import CourseHandgradersViewSet
from .course_views.course_staff import CourseStaffViewSet
from .course_views.course_students import CourseStudentsViewSet
from .course_views.course_views import (CopyCourseView, CourseByNameSemesterYearView,
                                        CourseDetailView, CourseUserRolesView,
                                        ListCreateCourseView)
from .group_invitation_views import (AcceptGroupInvitationView, GroupInvitationDetailView,
                                     ListCreateGroupInvitationView)
from .group_views import (CreateSoloGroupView, GroupDetailView, GroupUltimateSubmissionView,
                          ListCreateGroupsView, MergeGroupsView)
from .oauth2callback import oauth2_callback
from .project_views.expected_student_file_views import (ExpectedStudentFileDetailView,
                                                        ListCreateExpectedStudentFileView)
from .project_views.instructor_file_views import (InstructorFileContentView,
                                                  InstructorFileDetailView,
                                                  ListCreateInstructorFileView,
                                                  RenameInstructorFileView)
from .project_views.project_views import (AllScoresTaskView, AllSubmittedFilesTaskView,
                                          ClearResultsCacheView, CopyProjectView,
                                          DownloadTaskDetailView, DownloadTaskResultView,
                                          ImportHandgradingRubricView,
                                          ListCreateProjectView, ListDownloadTasksView,
                                          NumQueuedSubmissionsView, ProjectDetailView,
                                          UltimateSubmissionScoresTaskView,
                                          UltimateSubmissionSubmittedFilesTaskView)
from .rerun_submissions_task_views import (CancelRerunSubmissionsTaskView,
                                           RerunSubmissionsTaskDetailView,
                                           RerunSubmissionsTaskListCreateView)
from .sandbox_docker_image_views import (BuildTaskDetailView, CancelBuildTaskView,
                                         ListBuildTasksForCourseView,
                                         ListCreateGlobalSandboxDockerImageView,
                                         ListCreateSandboxDockerImageForCourseView,
                                         ListGlobalBuildTasksView, RebuildSandboxDockerImageView,
                                         SandboxDockerImageDetailView)
from .student_test_suite_views import (StudentTestSuiteDetailView, StudentTestSuiteListCreateView,
                                       StudentTestSuiteOrderView)
from .submission_views.all_ultimate_submission_results_view import AllUltimateSubmissionResults
from .submission_views.submission_result_views import (
    AGTestCommandResultOutputSizeView, AGTestCommandResultStderrDiffView,
    AGTestCommandResultStderrView, AGTestCommandResultStdoutDiffView,
    AGTestCommandResultStdoutView, AGTestSuiteResultOutputSizeView, AGTestSuiteResultStderrView,
    AGTestSuiteResultStdoutView, StudentTestSuiteOutputSizeView,
    StudentTestSuiteResultGetStudentTestsStderrView,
    StudentTestSuiteResultGetStudentTestsStdoutView,
    StudentTestSuiteResultGradeBuggyImplsStderrView,
    StudentTestSuiteResultGradeBuggyImplsStdoutView, StudentTestSuiteResultSetupStderrView,
    StudentTestSuiteResultSetupStdoutView, StudentTestSuiteResultValidityCheckStderrView,
    StudentTestSuiteResultValidityCheckStdoutView, SubmissionResultsView)
from .submission_views.submission_views import (GetSubmittedFileView, ListCreateSubmissionView,
                                                ListSubmissionsWithResults,
                                                RemoveSubmissionFromQueueView,
                                                SubmissionDetailView)
from .user_views import (CoursesIsAdminForView, CoursesIsEnrolledInView,
                         CoursesIsHandgraderForView, CoursesIsStaffForView,
                         CurrentUserCanCreateCoursesView, CurrentUserView,
                         GroupInvitationsReceivedView, GroupInvitationsSentView,
                         GroupsIsMemberOfView, UserDetailView, UserLateDaysView)
