from django.conf import settings
from django.conf.urls import include, url
from django.urls import path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions, routers

from autograder.rest_api import views
from autograder.rest_api.views.schema_generation import AGSchemaGenerator

user_router = routers.SimpleRouter()
user_router.register(r'users', views.UserViewSet, base_name='user')

course_router = routers.SimpleRouter()
course_router.register(r'courses', views.CourseViewSet, base_name='course')

project_router = routers.SimpleRouter()
project_router.register(r'projects', views.ProjectDetailViewSet, base_name='project')

project_downloads_router = routers.SimpleRouter()
project_downloads_router.register(r'download_tasks', views.DownloadTaskDetailViewSet,
                                  base_name='download_tasks')

expected_student_pattern_router = routers.SimpleRouter()
expected_student_pattern_router.register(r'expected_student_files',
                                         views.ExpectedStudentFilePatternDetailViewSet,
                                         base_name='expected-student-file')

uploaded_file_router = routers.SimpleRouter()
uploaded_file_router.register(r'instructor_files',
                              views.InstructorFileDetailViewSet,
                              base_name='uploaded-file')

group_invitation_router = routers.SimpleRouter()
group_invitation_router.register(r'group_invitations',
                                 views.GroupInvitationDetailViewSet,
                                 base_name='group-invitation')

group_router = routers.SimpleRouter()
group_router.register(r'groups', views.GroupDetailViewSet, base_name='group')

submission_router = routers.SimpleRouter()
submission_router.register(r'submissions', views.SubmissionDetailViewSet,
                           base_name='submission')


ag_test_suite_detail_router = routers.SimpleRouter()
ag_test_suite_detail_router.register(r'ag_test_suites', views.AGTestSuiteDetailViewSet,
                                     base_name='ag-test-suite')

ag_test_case_detail_router = routers.SimpleRouter()
ag_test_case_detail_router.register(r'ag_test_cases', views.AGTestCaseDetailViewSet,
                                    base_name='ag-test-case')

ag_test_command_detail_router = routers.SimpleRouter()
ag_test_command_detail_router.register(r'ag_test_commands', views.AGTestCommandDetailViewSet,
                                       base_name='ag-test-command')

student_test_suite_detail_router = routers.SimpleRouter()
student_test_suite_detail_router.register(r'student_test_suites',
                                          views.StudentTestSuiteDetailViewSet,
                                          base_name='student-test-suite')

rerun_submissions_task_detail_router = routers.SimpleRouter()
rerun_submissions_task_detail_router.register(r'rerun_submissions_tasks',
                                              views.RerunSubmissionsTaskDetailVewSet,
                                              base_name='rerun-submissions-task')


schema_view = get_schema_view(
    openapi.Info(
        title="Autograder API",
        default_version=settings.VERSION,
        description="""
<h3>Welcome to the Autograder API documentation!</h3>
<div>
  This API is in Beta. Most of the information here is stable, but some of it
  may change in future releases.
</div>
<div>
  You can look around as much as you like, but if you want to send real requests,
  you'll need to authenticate. Here's how:
</div>
<ol>
  <li>
    If you'll be using the API a lot, you might want to request a dedicated access token.
    To get one, send an email to jameslp at umich.edu, and we'll see about securely sending you
    a new token.
  </li>
  <li>
    Otherwise, you can snag the token from your user account.
    Head over to <a href="autograder.io">autograder.io</a>, log in,
    and open up the developer console.</li>
  <li>
    Under the "Network" tab, select any of the requests to the
    "/users/current/my_roles/" endpoint. Find the "Authorization" header and copy the value
    "Token &lt;token&gt;", where &lt;token&gt; is your authorization
    token.
  </li>
  <li>
    When sending requests from your own code, set the "Authorization" header with the value
    "Token &lt;token&gt;"
  </li>
  <li>
    When you click on the "Authorize" or "Try it out" buttons on this page,
    enter "Token &lt;token&gt;" into the "Value" field.
  </li>
</ol>
        """,
        # terms_of_service="https://www.google.com/policies/terms/",
        # contact=openapi.Contact(email="contact@snippets.local"),
        # license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    generator_class=AGSchemaGenerator,
)


urlpatterns = [
    url(r'^docs/$', schema_view.with_ui('swagger'), name='schema-swagger-ui'),

    url(r'^oauth2callback/$', views.oauth2_callback, name='oauth2callback'),

    url(r'', include(user_router.urls)),
    path('users/<int:user_pk>/late_days/', views.UserLateDaysView.as_view(),
         name='user-late-days'),

    url(r'', include(course_router.urls)),
    path('course/<str:name>/<str:semester>/<int:year>/',
         views.CourseByNameSemesterYearView.as_view(),
         name='course-by-fields'),
    path('courses/<int:course_pk>/copy/', views.CopyCourseView.as_view(), name='copy-course'),
    path('courses/<int:pk>/admins/', views.CourseAdminViewSet.as_view(), name='course-admins'),
    path('courses/<int:pk>/staff/', views.CourseStaffViewSet.as_view(), name='course-staff'),
    path('courses/<int:pk>/students/', views.CourseStudentsViewSet.as_view(),
         name='course-students'),
    path('courses/<int:pk>/handgraders/', views.CourseHandgradersViewSet.as_view(),
         name='course-handgraders'),

    path('courses/<int:pk>/projects/', views.ListCreateProjectView.as_view(), name='projects'),
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
]
