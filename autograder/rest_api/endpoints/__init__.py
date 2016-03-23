from .user_endpoints import (
    GetCurrentUserEndpoint,
    GetUser,
    GetUserCoursesIsAdminForEndpoint,
    GetUserSemstersIsStaffForEndpoint,
    GetUserSemestersIsEnrolledInEndpoint,
    GetUserGroupsIsMemberOfEndpoint,
    GetGroupInvitationsSentEndpoint,
    GetGroupInvitationsReceivedEndpoint,
    GetUserNotificationsEndpoint,
    GetUserNotificationEndpoint,
)

from .course_endpoints import (
    ListCreateCourseEndpoint,
    GetUpdateCourseEndpoint,
    ListAddRemoveCourseAdministratorsEndpoint,
    ListAddSemesterEndpoint)

from .semester_endpoints import (
    GetUpdateSemesterEndpoint,
    ListAddRemoveSemesterStaffEndpoint,
    ListAddUpdateRemoveEnrolledStudentsEndpoint,
    ListAddProjectEndpoint)

from .project_endpoints import (
    GetUpdateProjectEndpoint,
    ListAddProjectFileEndpoint,
    GetUpdateDeleteProjectFileEndpoint,
    ListAddAutograderTestCaseEndpoint,
    ListAddStudentTestSuiteEndpoint,
    ListAddSubmissionGroupEndpoint,
    ListAddSubmissionGroupInvitationEndpoint,
)

from .autograder_test_case_endpoints import (
    GetUpdateDeleteAutograderTestCaseEndpoint,
)

from .autograder_test_case_result_endpoints import (
    GetAutograderTestCaseResultEndpoint,
)

from .student_test_suite_endpoints import (
    GetUpdateDeleteStudentTestSuiteEndpoint,
)

from .student_test_suite_result_endpoints import (
    GetStudentTestSuiteResultEndpoint,
)

from .submission_group_endpoints import (
    GetUpdateDeleteSubmissionGroupEndpoint,
    AddListSubmissionsEndpoint
)

from .submission_group_invitation_endpoints import (
    GetRejectSubmissionGroupInvitationEndpoint,
    AcceptSubmissionGroupInvitationEndpoint
)

from .submission_endpoints import (
    GetSubmissionEndpoint,
    ListSubmittedFilesEndpoint,
    GetSubmittedFileEndpoint,
    ListAutograderTestCaseResultsEndpoint,
    ListStudentTestSuiteResultsEndpoint,
    RemoveSubmissionFromQueue
)
