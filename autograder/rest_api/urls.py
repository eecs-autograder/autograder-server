from django.conf.urls import url, include

from rest_framework_nested import routers

from autograder.rest_api import views


user_router = routers.SimpleRouter()
user_router.register(r'users', views.UserViewSet, base_name='user')

course_router = routers.SimpleRouter()
course_router.register(r'courses', views.CourseViewSet, base_name='course')

admin_router = routers.NestedSimpleRouter(course_router, r'courses', lookup='course')
admin_router.register(r'admins',
                      views.CourseAdminViewSet,
                      base_name='course-admins')
staff_router = routers.NestedSimpleRouter(course_router, r'courses', lookup='course')
staff_router.register(r'staff',
                      views.CourseStaffViewSet,
                      base_name='course-staff')
enrolled_students_router = routers.NestedSimpleRouter(course_router,
                                                      r'courses',
                                                      lookup='course')
enrolled_students_router.register(r'enrolled_students',
                                  views.CourseEnrolledStudentsViewSet,
                                  base_name='course-enrolled-students')
course_projects_router = routers.NestedSimpleRouter(course_router, r'courses',
                                                    lookup='course')

project_router = routers.SimpleRouter()
project_router.register(r'projects', views.ProjectDetailViewSet, base_name='project')

project_downloads_router = routers.SimpleRouter()
project_downloads_router.register(r'download_tasks', views.DownloadTaskDetailViewSet,
                                  base_name='download_tasks')

expected_patterns_router = routers.NestedSimpleRouter(
    project_router, r'projects', lookup='project')
expected_patterns_router.register(
    r'expected_patterns', views.ExpectedStudentFilePatternsViewSet,
    base_name='project-expected-patterns')

uploaded_files_router = routers.NestedSimpleRouter(
    project_router, r'projects', lookup='project')
uploaded_files_router.register(
    r'uploaded_files', views.UploadedFilesViewSet,
    base_name='project-uploaded-files')

groups_router = routers.NestedSimpleRouter(
    project_router, r'projects', lookup='project')
groups_router.register(
    r'submission_groups', views.GroupsViewSet,
    base_name='project-groups')

invitations_router = routers.NestedSimpleRouter(
    project_router, r'projects', lookup='project')
invitations_router.register(
    r'group_invitations', views.GroupInvitationsViewSet,
    base_name='project-group-invitations')

expected_pattern_router = routers.SimpleRouter()
expected_pattern_router.register(r'expected_patterns',
                                 views.ExpectedStudentFilePatternDetailViewSet,
                                 base_name='expected-pattern')

uploaded_file_router = routers.SimpleRouter()
uploaded_file_router.register(r'uploaded_files',
                              views.UploadedFileDetailViewSet,
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



urlpatterns = [
    url(r'^oauth2callback/$', views.oauth2_callback, name='oauth2callback'),

    url(r'', include(user_router.urls)),

    url(r'', include(course_router.urls)),
    url(r'', include(admin_router.urls)),
    url(r'', include(staff_router.urls)),
    url(r'', include(enrolled_students_router.urls)),
    url(r'', include(course_projects_router.urls)),

    url(r'', include(project_router.urls)),
    url(r'', include(project_downloads_router.urls)),
    url(r'', include(expected_patterns_router.urls)),
    url(r'', include(uploaded_files_router.urls)),
    url(r'', include(groups_router.urls)),
    url(r'', include(invitations_router.urls)),

    url(r'', include(expected_pattern_router.urls)),
    url(r'', include(uploaded_file_router.urls)),
    url(r'', include(group_invitation_router.urls)),

    url(r'', include(group_router.urls)),
    url(r'', include(group_submissions_router.urls)),

    url(r'', include(submission_router.urls)),

    url(r'^courses/(?P<pk>[0-9]+)/projects/$',
        views.ListCreateProjectView.as_view(), name='project-list-create'),

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
]
