from django.conf.urls import url, include

from rest_framework_nested import routers

from autograder.rest_api import views


user_router = routers.SimpleRouter()
user_router.register(r'users', views.UserViewset, base_name='user')

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
                                  views.CourseEnrolledStudentsViewset,
                                  base_name='course-enrolled-students')
course_projects_router = routers.NestedSimpleRouter(course_router, r'courses',
                                                    lookup='course')
course_projects_router.register(r'projects',
                                views.CourseProjectsViewSet,
                                base_name='course-projects')


project_router = routers.SimpleRouter()
project_router.register(r'projects', views.ProjectViewSet, base_name='project')

expected_patterns_router = routers.NestedSimpleRouter(
    project_router, r'projects', lookup='project')
expected_patterns_router.register(
    r'expected_patterns', views.ProjectExpectedStudentFilePatternsViewSet,
    base_name='project-expected-patterns')

uploaded_files_router = routers.NestedSimpleRouter(
    project_router, r'projects', lookup='project')
uploaded_files_router.register(
    r'uploaded_files', views.ProjectUploadedFilesViewSet,
    base_name='project-uploaded-files')

groups_router = routers.NestedSimpleRouter(
    project_router, r'projects', lookup='project')
groups_router.register(
    r'submission_groups', views.ProjectGroupsViewSet,
    base_name='project-groups')

invitations_router = routers.NestedSimpleRouter(
    project_router, r'projects', lookup='project')
invitations_router.register(
    r'group_invitations', views.ProjectGroupInvitationsViewset,
    base_name='project-group-invitations')

ag_tests_router = routers.NestedSimpleRouter(
    project_router, r'projects', lookup='project')
ag_tests_router.register(
    r'ag_test_cases', views.ProjectAGTestsViewset,
    base_name='project-ag-tests')


expected_pattern_router = routers.SimpleRouter()
expected_pattern_router.register(r'expected_patterns',
                                 views.ExpectedStudentFilePatternViewset,
                                 base_name='expected-pattern')

uploaded_file_router = routers.SimpleRouter()
uploaded_file_router.register(r'uploaded_files',
                              views.UploadedFileViewset,
                              base_name='uploaded-file')

ag_test_router = routers.SimpleRouter()
ag_test_router.register(r'ag_test_cases', views.AGTestCaseViewset,
                        base_name='ag-test')

ag_test_result_router = routers.SimpleRouter()
ag_test_result_router.register(r'ag_test_results', views.AGTestResultViewSet,
                               base_name='ag-test-result')

group_invitation_router = routers.SimpleRouter()
group_invitation_router.register(r'group_invitations',
                                 views.GroupInvitationViewset,
                                 base_name='group-invitation')


group_router = routers.SimpleRouter()
group_router.register(r'groups', views.GroupViewset, base_name='group')

group_submissions_router = routers.NestedSimpleRouter(group_router, r'groups',
                                                      lookup='group')
group_submissions_router.register(r'submissions',
                                  views.GroupSubmissionsViewset,
                                  base_name='group-submissions')


submission_router = routers.SimpleRouter()
submission_router.register(r'submissions', views.SubmissionViewset,
                           base_name='submission')

submission_results_router = routers.NestedSimpleRouter(
    submission_router, r'submissions', lookup='submission')
submission_results_router.register(r'results', views.SubmissionResultsViewset,
                                   base_name='submission-results')


urlpatterns = [
    url(r'^oauth2callback/$', views.oauth2_callback, name='oauth2callback'),

    url(r'', include(user_router.urls)),

    url(r'', include(course_router.urls)),
    url(r'', include(admin_router.urls)),
    url(r'', include(staff_router.urls)),
    url(r'', include(enrolled_students_router.urls)),
    url(r'', include(course_projects_router.urls)),

    url(r'', include(project_router.urls)),
    url(r'', include(expected_patterns_router.urls)),
    url(r'', include(uploaded_files_router.urls)),
    url(r'', include(groups_router.urls)),
    url(r'', include(invitations_router.urls)),
    url(r'', include(ag_tests_router.urls)),

    url(r'', include(expected_pattern_router.urls)),
    url(r'', include(uploaded_file_router.urls)),
    url(r'', include(ag_test_router.urls)),
    url(r'', include(ag_test_result_router.urls)),
    url(r'', include(group_invitation_router.urls)),

    url(r'', include(group_router.urls)),
    url(r'', include(group_submissions_router.urls)),

    url(r'', include(submission_router.urls)),
    url(r'', include(submission_results_router.urls)),
]
