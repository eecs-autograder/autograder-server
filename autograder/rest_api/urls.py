from django.conf.urls import url, include
# from rest_framework.urlpatterns import format_suffix_patterns
from autograder.rest_api import views

# import autograder.core.shared.global_constants as gc

# from rest_framework import routers
from rest_framework_nested import routers

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

ag_tests_router = routers.NestedSimpleRouter(
    project_router, r'projects', lookup='project')
ag_tests_router.register(
    r'ag_test_cases', views.ProjectAGTestsViewset,
    base_name='project-ag-tests')


urlpatterns = [
    url(r'', include(course_router.urls)),
    url(r'', include(admin_router.urls)),
    url(r'', include(staff_router.urls)),
    url(r'', include(enrolled_students_router.urls)),
    url(r'', include(course_projects_router.urls)),

    url(r'', include(project_router.urls)),
    url(r'', include(expected_patterns_router.urls)),
    url(r'', include(uploaded_files_router.urls)),
    url(r'', include(groups_router.urls)),
    url(r'', include(ag_tests_router.urls))
]

# print(dir(urlpatterns[0]))
# print(urlpatterns[1].reverse())
# print(urlpatterns[1].urlconf_name)

# user_patterns = [
#     url(r'^$', endpoints.GetUser.as_view(), name='get'),
#     url(r'^courses_is_admin_for/$',
#         endpoints.GetUserCoursesIsAdminForEndpoint.as_view(),
#         name='admin-courses'),
#     url(r'^semesters_is_staff_for/$',
#         endpoints.GetUserSemstersIsStaffForEndpoint.as_view(),
#         name='staff-semesters'),
#     url(r'^semesters_is_enrolled_in/$',
#         endpoints.GetUserSemestersIsEnrolledInEndpoint.as_view(),
#         name='enrolled-semesters'),
#     url(r'^groups_is_member_of/$',
#         endpoints.GetUserGroupsIsMemberOfEndpoint.as_view(),
#         name='submission-groups'),
#     url(r'^group_invitations_sent/$',
#         endpoints.GetGroupInvitationsSentEndpoint.as_view(),
#         name='invitations-sent'),
#     url(r'^group_invitations_received/$',
#         endpoints.GetGroupInvitationsReceivedEndpoint.as_view(),
#         name='invitations-received'),
#     url(r'^notifications/$',
#         endpoints.GetUserNotificationsEndpoint.as_view(),
#         name='notifications'),
# ]

# course_patterns = [
#     url(r'^$', endpoints.GetUpdateCourseEndpoint.as_view(),
#         name='get'),
#     url(r'^administrators/$',
#         endpoints.ListAddRemoveCourseAdministratorsEndpoint.as_view(),
#         name='admins'),
#     url(r'^semesters/$', endpoints.ListAddSemesterEndpoint.as_view(),
#         name='semesters')
# ]

# semester_patterns = [
#     url(r'^$', endpoints.GetUpdateSemesterEndpoint.as_view(),
#         name='get'),
#     url(r'^staff/$', endpoints.ListAddRemoveSemesterStaffEndpoint.as_view(),
#         name='staff'),
#     url(r'^enrolled_students/$',
#         endpoints.ListAddUpdateRemoveEnrolledStudentsEndpoint.as_view(),
#         name='enrolled_students'),
#     url(r'^projects/$', endpoints.ListAddProjectEndpoint.as_view(),
#         name='projects')
# ]

# project_patterns = [
#     url(r'^$', endpoints.GetUpdateProjectEndpoint.as_view(),
#         name='get'),
#     url(r'^uploaded_files/$', endpoints.ListAddProjectFileEndpoint.as_view(),
#         name='files'),
#     url(r'^uploaded_files/(?P<filename>{})/$'.format(
#         gc.PROJECT_FILENAME_WHITELIST_REGEX.pattern),
#         endpoints.GetUpdateDeleteProjectFileEndpoint.as_view(),
#         name='file'),
#     url(r'^autograder_test_cases/$',
#         endpoints.ListAddAutograderTestCaseEndpoint.as_view(),
#         name='ag-tests'),
#     url(r'^student_test_suites/$',
#         endpoints.ListAddStudentTestSuiteEndpoint.as_view(),
#         name='suites'),
#     url(r'^submission_groups/$',
#         endpoints.ListAddSubmissionGroupEndpoint.as_view(),
#         name='groups'),
#     url(r'^submission_group_invitations/$',
#         endpoints.ListAddSubmissionGroupInvitationEndpoint.as_view(),
#         name='invitations'),
# ]

# ag_test_patterns = [
#     url(r'^$', endpoints.GetUpdateDeleteAutograderTestCaseEndpoint.as_view(),
#         name='get')
# ]

# ag_test_result_patterns = [
#     url(r'^$', endpoints.GetAutograderTestCaseResultEndpoint.as_view(),
#         name='get')
# ]

# suite_patterns = [
#     url(r'^$', endpoints.GetUpdateDeleteStudentTestSuiteEndpoint.as_view(),
#         name='get')
# ]

# suite_result_patterns = [
#     url(r'^$', endpoints.GetStudentTestSuiteResultEndpoint.as_view(),
#         name='get')
# ]

# group_patterns = [
#     url(r'^$', endpoints.GetUpdateDeleteSubmissionGroupEndpoint.as_view(),
#         name='get'),
#     url(r'^submissions/$',
#         endpoints.AddListSubmissionsEndpoint.as_view(),
#         name='submissions')

# ]

# invitation_patterns = [
#     url(r'^$',
#         endpoints.GetRejectSubmissionGroupInvitationEndpoint.as_view(),
#         name='get'),
#     url(r'^accept/$',
#         endpoints.AcceptSubmissionGroupInvitationEndpoint.as_view(),
#         name='accept')
# ]

# submission_patterns = [
#     url(r'^$', endpoints.GetSubmissionEndpoint.as_view(),
#         name='get'),
#     url(r'^submitted_files/$', endpoints.ListSubmittedFilesEndpoint.as_view(),
#         name='files'),
#     url(r'^submitted_files/(?P<filename>{})/$'.format(
#         gc.PROJECT_FILENAME_WHITELIST_REGEX.pattern),
#         endpoints.GetSubmittedFileEndpoint.as_view(),
#         name='file'),
#     url(r'^autograder_test_case_results/$',
#         endpoints.ListAutograderTestCaseResultsEndpoint.as_view(),
#         name='test-results'),
#     url(r'^student_test_suite_results/$',
#         endpoints.ListStudentTestSuiteResultsEndpoint.as_view(),
#         name='suite-results'),
#     url(r'^remove_from_queue/$',
#         endpoints.RemoveSubmissionFromQueue.as_view(),
#         name='remove-from-queue')
# ]

# notification_patterns = [
#     url(r'^$', endpoints.GetUserNotificationEndpoint.as_view(),
#         name='get'),
# ]

# urlpatterns = [
#     url(r'^user/current/$',
#         views.GetCurrentUserEndpoint.as_view(), name='current-user'),
#     url(r'^users/(?P<pk>[0-9]+)/', include(user_patterns, namespace='user')),

    # url(r'^courses/$', endpoints.ListCreateCourseEndpoint.as_view(),
    #     name='courses'),
    # url(r'^courses/(?P<pk>[0-9]+)/',
    #     include(course_patterns, namespace='course')),
    # url(r'^semesters/(?P<pk>[0-9]+)/',
    #     include(semester_patterns, namespace='semester')),
    # url(r'^projects/(?P<pk>[0-9]+)/',
    #     include(project_patterns, namespace='project')),

    # url(r'^autograder_test_cases/(?P<pk>[0-9]+)/',
    #     include(ag_test_patterns, namespace='ag-test')),
    # url(r'^autograder_test_case_results/(?P<pk>[0-9]+)',
    #     include(ag_test_result_patterns, namespace='test-result')),

    # url(r'^student_test_suites/(?P<pk>[0-9]+)/',
    #     include(suite_patterns, namespace='suite')),
    # url(r'^student_test_suite_results/(?P<pk>[0-9]+)/',
    #     include(suite_result_patterns, namespace='suite-result')),

    # url(r'^submission_groups/(?P<pk>[0-9]+)/',
    #     include(group_patterns, namespace='group')),
    # url(r'^submission_group_invitations/(?P<pk>[0-9]+)/',
    #     include(invitation_patterns, namespace='invitation')),

    # url(r'^submissions/(?P<pk>[0-9]+)/',
    #     include(submission_patterns, namespace='submission')),

    # url(r'^notifications/(?P<pk>[0-9]+)/',
    #     include(notification_patterns, namespace='notification'))


    # url(r'^courses/$', views.CourseList.as_view()),
    # url(r'^courses/(?P<pk>[0-9]+)/$', views.CourseDetail.as_view()),
    # url(r'^semesters/$', views.SemesterList.as_view()),
    # url(r'^semesters/(?P<pk>[0-9]+)/$', views.SemesterDetail.as_view()),
# ]

# urlpatterns = format_suffix_patterns(urlpatterns)
