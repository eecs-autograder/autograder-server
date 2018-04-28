from django.conf import settings
from django.conf.urls import url, include
from django.urls import path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import response, permissions
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework_nested import routers

from autograder.rest_api import views
from autograder.rest_api.views.ag_model_views import AlwaysIsAuthenticatedMixin
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

group_submissions_router = routers.NestedSimpleRouter(group_router, r'groups',
                                                      lookup='group')
group_submissions_router.register(r'submissions',
                                  views.SubmissionsViewSet,
                                  base_name='group-submissions')


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


class LogoutView(AlwaysIsAuthenticatedMixin, APIView):
    def post(self, request, *args, **kwargs):
        Token.objects.filter(user=request.user).delete()
        return response.Response(status=status.HTTP_200_OK)


schema_view = get_schema_view(
    openapi.Info(
       title="Autograder API",
       default_version=settings.VERSION,
       # description="Test description",
       # terms_of_service="https://www.google.com/policies/terms/",
       # contact=openapi.Contact(email="contact@snippets.local"),
       # license=openapi.License(name="BSD License"),
    ),
    # validators=['flex', 'ssv'],
    public=True,
    permission_classes=(permissions.AllowAny,),
    generator_class=AGSchemaGenerator,
    # authentication_classes=
)


urlpatterns = [
    url(r'^docs/$', schema_view.with_ui('swagger'), name='schema-swagger-ui'),

    url(r'^oauth2callback/$', views.oauth2_callback, name='oauth2callback'),
    url(r'^logout/$', LogoutView.as_view()),

    url(r'', include(user_router.urls)),

    url(r'', include(course_router.urls)),
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
    path('instructor_files/<int:pk>/content/', views.InstructorFileContentView.as_view(),
         name='uploaded-file-content'),

    path('projects/<int:pk>/expected_student_files/',
         views.ListCreateExpectedStudentFilesViewSet.as_view(), name='expected-student-files'),

    url(r'', include(project_downloads_router.urls)),

    url(r'', include(expected_student_pattern_router.urls)),
    url(r'', include(uploaded_file_router.urls)),

    path('projects/<int:pk>/group_invitations/',
         views.ListCreateGroupInvitationViewSet.as_view(),
         name='group-invitations'),
    url(r'', include(group_invitation_router.urls)),

    url(r'', include(group_router.urls)),
    url(r'', include(group_submissions_router.urls)),

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
        views.CreateSoloGroupView.as_view(), name='solo_group'),
]
