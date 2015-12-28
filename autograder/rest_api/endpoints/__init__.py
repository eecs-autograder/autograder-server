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

from .student_test_suite_endpoints import (
    GetUpdateDeleteStudentTestSuiteEndpoint,
)

from .submission_group_endpoints import (
    GetUpdateDeleteSubmissionGroupEndpoint,
)

from .submission_group_invitation_endpoints import (
    GetUpdateDeleteSubmissionGroupInvitationEndpoint,
)

# from .user_endpoints import GetUser

# from .submission_endpoints import (
#     GetSubmissionEndpoint, ListSubmittedFilesTestCase,
#     ListAutograderTestCaseResultsTestCase,
#     ListStudentTestSuiteResultsTestCase
# )
