from django.conf import settings
from django.conf.urls import include, url
from django.urls import path
from rest_framework import permissions
from rest_framework.schemas import get_schema_view

from autograder.rest_api import views

# schema_view = get_schema_view(
#     openapi.Info(
#         title="Autograder API",
#         default_version=settings.VERSION,
#         description="""
# <h3>Welcome to the Autograder API documentation!</h3>
# <div>
#   To authenticate:
# </div>
# <ol>
#   <li>
#     If you'll be using the API a lot, you might want to request a dedicated access token.
#     To get one, send an email to jameslp at umich.edu, and we'll see about securely sending you
#     a new token.
#   </li>
#   <li>
#     Otherwise, you can snag the token from your user account.
#     Head over to <a href="autograder.io">autograder.io</a>, log in,
#     and open up the developer console.</li>
#   <li>
#     Under the "Network" tab, select any of the requests to the
#     "/users/current/my_roles/" endpoint. Find the "Authorization" header and copy the value
#     "Token &lt;token&gt;", where &lt;token&gt; is your authorization
#     token.
#   </li>
#   <li>
#     When sending requests from your own code, set the "Authorization" header with the value
#     "Token &lt;token&gt;"
#   </li>
#   <li>
#     When you click on the "Authorize" or "Try it out" buttons on this page,
#     enter "Token &lt;token&gt;" into the "Value" field.
#   </li>
# </ol>
#         """,
#         # terms_of_service="https://www.google.com/policies/terms/",
#         # contact=openapi.Contact(email="contact@snippets.local"),
#         # license=openapi.License(name="BSD License"),
#     ),
#     public=True,
#     permission_classes=(permissions.AllowAny,),
#     generator_class=AGSchemaGenerator,
# )


urlpatterns = [
    path('oauth2callback/', views.oauth2_callback, name='oauth2callback'),
    path('users/current/', views.CurrentUserView.as_view(), name='current-user'),
    path('users/current/can_create_courses/', views.CurrentUserCanCreateCoursesView.as_view(),
         name='user-can-create-courses'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('users/<username_or_id>/late_days/', views.UserLateDaysView.as_view(),
         name='user-late-days'),
    path('users/<int:pk>/courses_is_admin_for/', views.CoursesIsAdminForView.as_view(),
         name='courses-is-admin-for'),
    path('users/<int:pk>/courses_is_staff_for/', views.CoursesIsStaffForView.as_view(),
         name='courses-is-staff-for'),
    path('users/<int:pk>/courses_is_enrolled_in/', views.CoursesIsEnrolledInView.as_view(),
         name='courses-is-enrolled-in'),
    path('users/<int:pk>/courses_is_handgrader_for/', views.CoursesIsHandgraderForView.as_view(),
         name='courses-is-handgrader-for'),
    path('users/<int:pk>/groups_is_member_of/', views.GroupsIsMemberOfView.as_view(),
         name='groups-is-member-of'),
    path('users/<int:pk>/group_invitations_sent/', views.GroupInvitationsSentView.as_view(),
         name='group-invitations-sent'),
    path('users/<int:pk>/group_invitations_received/',
         views.GroupInvitationsReceivedView.as_view(),
         name='group-invitations-received'),


    path('courses/', views.ListCreateCourseView.as_view(), name='list-create-courses'),
    path('courses/<int:pk>/', views.CourseDetailView.as_view(), name='course-detail'),
    path('courses/<int:pk>/my_roles/',
         views.CourseUserRolesView.as_view(),
         name='course-user-roles'),
    path('course/<str:name>/<str:semester>/<int:year>/',
         views.CourseByNameSemesterYearView.as_view(),
         name='course-by-fields'),
    path('courses/<int:pk>/copy/', views.CopyCourseView.as_view(), name='copy-course'),
    path('courses/<int:pk>/admins/', views.CourseAdminViewSet.as_view(), name='course-admins'),
    path('courses/<int:pk>/staff/', views.CourseStaffViewSet.as_view(), name='course-staff'),
    path('courses/<int:pk>/students/', views.CourseStudentsViewSet.as_view(),
         name='course-students'),
    path('courses/<int:pk>/handgraders/', views.CourseHandgradersViewSet.as_view(),
         name='course-handgraders'),

    path('courses/<int:pk>/projects/', views.ListCreateProjectView.as_view(),
         name='list-create-projects'),
    path('projects/<int:pk>/', views.ProjectDetailView.as_view(), name='project-detail'),
    path('projects/<int:pk>/num_queued_submissions/', views.NumQueuedSubmissionsView.as_view(),
         name='num-queued-submissions'),
    path('projects/<int:project_pk>/copy_to_course/<int:target_course_pk>/',
         views.CopyProjectView.as_view(), name='copy-project'),

    path('projects/<int:pk>/all_submission_files/', views.AllSubmittedFilesTaskView.as_view(),
         name='all-submission-files-task'),
    path('projects/<int:pk>/ultimate_submission_files/',
         views.UltimateSubmissionSubmittedFilesTaskView.as_view(),
         name='ultimate-submission-files-task'),
    path('projects/<int:pk>/all_submission_scores/', views.AllScoresTaskView.as_view(),
         name='all-submission-scores-task'),
    path('projects/<int:pk>/ultimate_submission_scores/',
         views.UltimateSubmissionScoresTaskView.as_view(),
         name='ultimate-submission-scores-task'),

    path('projects/<int:pk>/download_tasks/', views.ListDownloadTasksView.as_view(),
         name='download-tasks'),
    path('download_tasks/<int:pk>/', views.DownloadTaskDetailView.as_view(),
         name='download-task-detail'),
    path('download_tasks/<int:pk>/result/', views.DownloadTaskResultView.as_view(),
         name='download-task-result'),

    path('projects/<int:pk>/results_cache/', views.ClearResultsCacheView.as_view(),
         name='project-results-cache'),

    path('projects/<int:project_pk>/import_handgrading_rubric_from/<int:import_from_project_pk>/',
         views.ImportHandgradingRubricView.as_view(), name='import-handgrading-rubric'),

    path('projects/<int:pk>/instructor_files/', views.ListCreateInstructorFileView.as_view(),
         name='instructor-files'),
    path('instructor_files/<int:pk>/', views.InstructorFileDetailView.as_view(),
         name='instructor-file-detail'),
    path('instructor_files/<int:pk>/name/', views.RenameInstructorFileView.as_view(),
         name='instructor-file-rename'),
    path('instructor_files/<int:pk>/content/', views.InstructorFileContentView.as_view(),
         name='instructor-file-content'),

    path('projects/<int:pk>/expected_student_files/',
         views.ListCreateExpectedStudentFileView.as_view(), name='expected-student-files'),
    path('expected_student_files/<int:pk>/',
         views.ExpectedStudentFileDetailView.as_view(), name='expected-student-file-detail'),


    path('projects/<int:pk>/group_invitations/',
         views.ListCreateGroupInvitationView.as_view(),
         name='group-invitations'),
    path('group_invitations/<int:pk>/', views.GroupInvitationDetailView.as_view(),
         name='group-invitation-detail'),
    path('group_invitations/<int:pk>/accept/', views.AcceptGroupInvitationView.as_view(),
         name='accept-group-invitation'),

    path('projects/<int:project_pk>/groups/',
        views.ListCreateGroupsView.as_view(), name='groups'),
    path('projects/<int:project_pk>/groups/solo_group/',
        views.CreateSoloGroupView.as_view(),
        name='solo_group'),
    path('groups/<int:pk>/', views.GroupDetailView.as_view(),
         name='group-detail'),
    path('groups/<int:pk>/ultimate_submission/', views.GroupUltimateSubmissionView.as_view(),
         name='group-ultimate-submission'),
    path('groups/<int:pk>/merge_with/<int:other_group_pk>/',
         views.MergeGroupsView.as_view(),
         name='merge-groups'),

    path('projects/<int:project_pk>/groups/bonus_submissions/',
         views.EditBonusSubmissionsView.as_view(),
         name='edit-bonus-submissions'),

    path('groups/<int:pk>/submissions/', views.ListCreateSubmissionViewSet.as_view(),
         name='submissions'),
    path('submissions/<int:pk>/', views.SubmissionDetailView.as_view(),
         name='submission-detail'),
    path('submissions/<int:pk>/file/', views.GetSubmittedFileView.as_view(),
         name='submission-file'),
    path('submissions/<int:pk>/remove_from_queue/', views.RemoveSubmissionFromQueueView.as_view(),
         name='remove-submission-from-queue'),

    path('sandbox_docker_images/', views.ListCreateGlobalSandboxDockerImageView.as_view(),
         name='global-sandbox-images'),
    path('courses/<int:pk>/sandbox_docker_images/',
         views.ListCreateSandboxDockerImageForCourseView.as_view(),
         name='course-sandbox-images'),
    path('image_build_tasks/', views.ListGlobalBuildTasksView.as_view(),
         name='list-global-image-builds'),
    path('courses/<int:pk>/image_build_tasks/',
         views.ListBuildTasksForCourseView.as_view(),
         name='list-course-image-builds'),
    path('image_build_tasks/<int:pk>/', views.BuildTaskDetailView.as_view(),
         name='image-build-task-detail'),
    path('image_build_tasks/<int:pk>/cancel/', views.CancelBuildTaskView.as_view(),
         name='cancel-image-build-task'),
    path('sandbox_docker_images/<int:pk>/', views.SandboxDockerImageDetailView.as_view(),
         name='sandbox-docker-image-detail'),
    path('sandbox_docker_images/<int:pk>/rebuild/', views.RebuildSandboxDockerImageView.as_view(),
         name='rebuild-sandbox-docker-image'),

    path('projects/<int:project_pk>/ag_test_suites/',
        views.AGTestSuiteListCreateView.as_view(), name='ag_test_suites'),
    path('projects/<int:project_pk>/ag_test_suites/order/',
        views.AGTestSuiteOrderView.as_view(), name='ag_test_suite_order'),
    path('ag_test_suites/<int:pk>/', views.AGTestSuiteDetailView.as_view(),
         name='ag-test-suite-detail'),

    path('ag_test_suites/<int:ag_test_suite_pk>/ag_test_cases/',
        views.AGTestCaseListCreateView.as_view(), name='ag_test_cases'),
    path('ag_test_suites/<int:ag_test_suite_pk>/ag_test_cases/order/',
        views.AGTestCaseOrderView.as_view(), name='ag_test_case_order'),
    path('ag_test_cases/<int:pk>/', views.AGTestCaseDetailView.as_view(),
         name='ag-test-case-detail'),

    path('ag_test_cases/<int:ag_test_case_pk>/ag_test_commands/',
        views.AGTestCommandListCreateView.as_view(), name='ag_test_commands'),
    path('ag_test_cases/<int:ag_test_case_pk>/ag_test_commands/order/',
        views.AGTestCommandOrderView.as_view(), name='ag_test_command_order'),
    path('ag_test_commands/<int:pk>/', views.AGTestCommandDetailView.as_view(),
         name='ag-test-command-detail'),

    path('projects/<int:project_pk>/student_test_suites/',
        views.StudentTestSuiteListCreateView.as_view(), name='student_test_suites'),
    path('projects/<int:project_pk>/student_test_suites/order/',
        views.StudentTestSuiteOrderView.as_view(), name='student_test_suite_order'),
    path('student_test_suites/<int:pk>/', views.StudentTestSuiteDetailView.as_view(),
         name='student-test-suite-detail'),

    path('projects/<int:project_pk>/rerun_submissions_tasks/',
         views.RerunSubmissionsTaskListCreateView.as_view(),
         name='rerun_submissions_tasks'),
    path('rerun_submissions_tasks/<int:pk>/',
         views.RerunSubmissionsTaskDetailView.as_view(),
         name='rerun-submissions-task-detail'),
    path('rerun_submissions_tasks/<int:pk>/cancel/',
         views.CancelRerunSubmissionsTaskView.as_view(),
         name='cancel-rerun-submissions-task'),

    path('groups/<int:pk>/submissions_with_results/',
         views.ListSubmissionsWithResults.as_view(),
         name='list-submissions-with-results'),

    path('submissions/<int:pk>/results/',
         views.SubmissionResultsView.as_view(),
         name='submission-results'),

    path('projects/<int:project_pk>/all_ultimate_submission_results/',
         views.AllUltimateSubmissionResults.as_view(),
         name='all-ultimate-submission-results'),

    path('submissions/<int:pk>/ag_test_suite_results/<int:result_pk>/stdout/',
         views.AGTestSuiteResultsStdoutView.as_view(),
         name='ag-test-suite-result-stdout'),
    path('submissions/<int:pk>/ag_test_suite_results/<int:result_pk>/stderr/',
         views.AGTestSuiteResultsStderrView.as_view(),
         name='ag-test-suite-result-stderr'),
    path('submissions/<int:pk>/ag_test_suite_results/<int:result_pk>/output_size/',
         views.AGTestSuiteResultsOutputSizeView.as_view(),
         name='ag-test-suite-result-output-size'),

    path('submissions/<int:pk>/ag_test_cmd_results/<int:result_pk>/stdout/',
         views.AGTestCommandResultStdoutView.as_view(),
         name='ag-test-cmd-result-stdout'),
    path('submissions/<int:pk>/ag_test_cmd_results/<int:result_pk>/stderr/',
         views.AGTestCommandResultStderrView.as_view(),
         name='ag-test-cmd-result-stderr'),
    path('submissions/<int:pk>/ag_test_cmd_results/<int:result_pk>/stdout_diff/',
         views.AGTestCommandResultStdoutDiffView.as_view(),
         name='ag-test-cmd-result-stdout-diff'),
    path('submissions/<int:pk>/ag_test_cmd_results/<int:result_pk>/stderr_diff/',
         views.AGTestCommandResultStderrDiffView.as_view(),
         name='ag-test-cmd-result-stderr-diff'),
    path('submissions/<int:pk>/ag_test_cmd_results/<int:result_pk>/output_size/',
         views.AGTestCommandResultOutputSizeView.as_view(),
         name='ag-test-cmd-result-output-size'),

    path('submissions/<int:pk>/student_test_suite_results/<int:result_pk>/setup_stdout/',
         views.StudentTestSuiteResultSetupStdoutView.as_view(),
         name='student-suite-setup-stdout'),
    path('submissions/<int:pk>/student_test_suite_results/<int:result_pk>/setup_stderr/',
         views.StudentTestSuiteResultSetupStderrView.as_view(),
         name='student-suite-setup-stderr'),

    path('submissions/<int:pk>/student_test_suite_results/<int:result_pk>/get_student_test_names_stdout/',  # noqa
         views.StudentTestSuiteResultGetStudentTestsStdoutView.as_view(),
         name='student-suite-get-student-test-names-stdout'),
    path('submissions/<int:pk>/student_test_suite_results/<int:result_pk>/get_student_test_names_stderr/',  # noqa
         views.StudentTestSuiteResultGetStudentTestsStderrView.as_view(),
         name='student-suite-get-student-test-names-stderr'),

    path('submissions/<int:pk>/student_test_suite_results/<int:result_pk>/validity_check_stdout/',
         views.StudentTestSuiteResultValidityCheckStdoutView.as_view(),
         name='student-suite-validity-check-stdout'),
    path('submissions/<int:pk>/student_test_suite_results/<int:result_pk>/validity_check_stderr/',
         views.StudentTestSuiteResultValidityCheckStderrView.as_view(),
         name='student-suite-validity-check-stderr'),

    path('submissions/<int:pk>/student_test_suite_results/<int:result_pk>/grade_buggy_impls_stdout/',  # noqa
         views.StudentTestSuiteResultGradeBuggyImplsStdoutView.as_view(),
         name='student-suite-grade-buggy-impls-stdout'),
    path('submissions/<int:pk>/student_test_suite_results/<int:result_pk>/grade_buggy_impls_stderr/',  # noqa
         views.StudentTestSuiteResultGradeBuggyImplsStderrView.as_view(),
         name='student-suite-grade-buggy-impls-stderr'),

    path('submissions/<int:pk>/student_test_suite_results/<int:result_pk>/output_size/',
         views.StudentTestSuiteOutputSizeView.as_view(),
         name='student-suite-result-output-size'),
]
