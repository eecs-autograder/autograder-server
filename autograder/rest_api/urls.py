from django.conf import settings
from django.conf.urls import include, url
from django.urls import path
# from drf_yasg import openapi
# from drf_yasg.views import get_schema_view
from rest_framework import permissions, routers
from rest_framework.schemas import get_schema_view

from autograder.rest_api import views
# from autograder.rest_api.views.schema_generation import AGSchemaGenerator

project_router = routers.SimpleRouter()
project_router.register(r'projects', views.ProjectDetailViewSet, basename='project')

project_downloads_router = routers.SimpleRouter()
project_downloads_router.register(r'download_tasks', views.DownloadTaskDetailViewSet,
                                  basename='download_tasks')

expected_student_pattern_router = routers.SimpleRouter()
expected_student_pattern_router.register(r'expected_student_files',
                                         views.ExpectedStudentFilePatternDetailViewSet,
                                         basename='expected-student-file')

uploaded_file_router = routers.SimpleRouter()
uploaded_file_router.register(r'instructor_files',
                              views.InstructorFileDetailViewSet,
                              basename='uploaded-file')

group_invitation_router = routers.SimpleRouter()
group_invitation_router.register(r'group_invitations',
                                 views.GroupInvitationDetailViewSet,
                                 basename='group-invitation')

group_router = routers.SimpleRouter()
group_router.register(r'groups', views.GroupDetailViewSet, basename='group')

submission_router = routers.SimpleRouter()
submission_router.register(r'submissions', views.SubmissionDetailViewSet,
                           basename='submission')

sandbox_docker_image_detail_router = routers.SimpleRouter()
sandbox_docker_image_detail_router.register(
    r'sandbox_docker_images', views.SandboxDockerImageDetailViewSet,
    basename='sandbox-docker-image')
image_build_task_detail_router = routers.SimpleRouter()
image_build_task_detail_router.register(
    r'image_build_tasks', views.BuildTaskDetailViews,
    basename='image-build-task'
)

ag_test_suite_detail_router = routers.SimpleRouter()
ag_test_suite_detail_router.register(r'ag_test_suites', views.AGTestSuiteDetailViewSet,
                                     basename='ag-test-suite')

ag_test_case_detail_router = routers.SimpleRouter()
ag_test_case_detail_router.register(r'ag_test_cases', views.AGTestCaseDetailViewSet,
                                    basename='ag-test-case')

ag_test_command_detail_router = routers.SimpleRouter()
ag_test_command_detail_router.register(r'ag_test_commands', views.AGTestCommandDetailViewSet,
                                       basename='ag-test-command')

student_test_suite_detail_router = routers.SimpleRouter()
student_test_suite_detail_router.register(r'student_test_suites',
                                          views.StudentTestSuiteDetailViewSet,
                                          basename='student-test-suite')

rerun_submissions_task_detail_router = routers.SimpleRouter()
rerun_submissions_task_detail_router.register(r'rerun_submissions_tasks',
                                              views.RerunSubmissionsTaskDetailVewSet,
                                              basename='rerun-submissions-task')


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
    # url(r'^docs/?$', schema_view.with_ui('swagger'), name='schema-swagger-ui'),

    url(r'^oauth2callback/$', views.oauth2_callback, name='oauth2callback'),    path('users/current/', views.CurrentUserView.as_view(), name='current-user'),
    path('users/current/can_create_courses/', views.CurrentUserCanCreateCoursesView.as_view(),
         name='user-can-create-courses'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('users/<username_or_pk>/late_days/', views.UserLateDaysView.as_view(),
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
    path('users/<int:pk>/group_invitations_received/', views.GroupInvitationsReceivedView.as_view(),
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

    path('courses/<int:pk>/projects/', views.ListCreateProjectView.as_view(), name='projects'),
    path('projects/<int:project_pk>/copy_to_course/<int:target_course_pk>/',
         views.CopyProjectView.as_view(), name='copy-project'),
    path('projects/<int:project_pk>/import_handgrading_rubric_from/<int:import_from_project_pk>/',
         views.ImportHandgradingRubricView.as_view(), name='import-handgrading-rubric'),
    url(r'', include(project_router.urls)),

    path('projects/<int:pk>/instructor_files/', views.ListCreateInstructorFilesViewSet.as_view(),
         name='instructor-files'),
    url(r'', include(uploaded_file_router.urls)),
    path('instructor_files/<int:pk>/content/', views.InstructorFileContentView.as_view(),
         name='uploaded-file-content'),

    path('projects/<int:pk>/expected_student_files/',
         views.ListCreateExpectedStudentFilesViewSet.as_view(), name='expected-student-files'),
    url(r'', include(expected_student_pattern_router.urls)),

    url(r'', include(project_downloads_router.urls)),

    path('projects/<int:pk>/group_invitations/',
         views.ListCreateGroupInvitationViewSet.as_view(),
         name='group-invitations'),
    url(r'', include(group_invitation_router.urls)),

    url(r'', include(group_router.urls)),

    path('projects/<int:project_pk>/groups/bonus_submissions/',
         views.EditBonusSubmissionsView.as_view(),
         name='edit-bonus-submissions'),

    path('groups/<int:pk>/submissions/', views.ListCreateSubmissionViewSet.as_view(),
         name='submissions'),
    url(r'', include(submission_router.urls)),

    url(r'^projects/(?P<project_pk>[0-9]+)/ag_test_suites/$',
        views.AGTestSuiteListCreateView.as_view(), name='ag_test_suites'),
    url(r'^projects/(?P<project_pk>[0-9]+)/ag_test_suites/order/$',
        views.AGTestSuiteOrderView.as_view(), name='ag_test_suite_order'),
    url(r'', include(ag_test_suite_detail_router.urls)),

    path('sandbox_docker_images/', views.GlobalSandboxDockerImageViews.as_view(),
         name='global-sandbox-images'),
    path('courses/<int:pk>/sandbox_docker_images/',
         views.SandboxDockerImageForCourseViews.as_view(),
         name='course-sandbox-images'),
    path('image_build_tasks/', views.ListGlobalBuildTasksView.as_view(),
         name='list-global-image-builds'),
    path('courses/<int:pk>/image_build_tasks/',
         views.ListBuildTasksForCourseView.as_view(),
         name='list-course-image-builds'),
    url(r'', include(sandbox_docker_image_detail_router.urls)),
    url(r'', include(image_build_task_detail_router.urls)),

    url(r'^ag_test_suites/(?P<ag_test_suite_pk>[0-9]+)/ag_test_cases/$',
        views.AGTestCaseListCreateView.as_view(), name='ag_test_cases'),
    url(r'^ag_test_suites/(?P<ag_test_suite_pk>[0-9]+)/ag_test_cases/order/$',
        views.AGTestCaseOrderView.as_view(), name='ag_test_case_order'),
    url(r'', include(ag_test_case_detail_router.urls)),

    url(r'^ag_test_cases/(?P<ag_test_case_pk>[0-9]+)/ag_test_commands/$',
        views.AGTestCommandListCreateView.as_view(), name='ag_test_commands'),
    url(r'^ag_test_cases/(?P<ag_test_case_pk>[0-9]+)/ag_test_commands/order/$',
        views.AGTestCommandOrderView.as_view(), name='ag_test_command_order'),
    url(r'', include(ag_test_command_detail_router.urls)),

    url(r'^projects/(?P<project_pk>[0-9]+)/student_test_suites/$',
        views.StudentTestSuiteListCreateView.as_view(), name='student_test_suites'),
    url(r'^projects/(?P<project_pk>[0-9]+)/student_test_suites/order/$',
        views.StudentTestSuiteOrderView.as_view(), name='student_test_suite_order'),
    url(r'', include(student_test_suite_detail_router.urls)),

    url(r'^projects/(?P<project_pk>[0-9]+)/rerun_submissions_tasks/$',
        views.RerunSubmissionsTaskListCreateView.as_view(), name='rerun_submissions_tasks'),

    url(r'', include(rerun_submissions_task_detail_router.urls)),

    url(r'^projects/(?P<project_pk>[0-9]+)/groups/$',
        views.GroupsViewSet.as_view(), name='groups'),
    url(r'^projects/(?P<project_pk>[0-9]+)/groups/solo_group/$',
        views.CreateSoloGroupView.as_view({'post': 'create'}),
        name='solo_group'),

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
