from django.conf.urls import url, include
from rest_framework.urlpatterns import format_suffix_patterns
from autograder.rest_api import endpoints

user_patterns = [
    # url(r'^$', endpoints.GetUser.as_view(), name='get'),
    # url(r'^courses_is_admin_for/$',
    #     endpoints.GetUserCoursesIsAdminFor.as_view(),
    #     name='admin-courses'),
    # url(r'^semesters_is_staff_for/$',
    #     endpoints.GetUserSemstersIsStaffFor.as_view(),
    #     name='staff-semesters'),
    # url(r'^semesters_is_enrolled_in/$',
    #     endpoints.GetUserSemestersIsEnrolledIn.as_view(),
    #     name='enrolled-semesters'),
    # url(r'^groups_is_member_of/$',
    #     endpoints.GetUserGroupsIsMemberOf.as_view(),
    #     name='submission-groups'),
    # url(r'^pending_group_requests/$',
    #     endpoints.GetUserPendingGroupRequests.as_view(),
    #     name='pending-group-requests'),
    # url(r'^notifications/$',
    #     endpoints.GetUserNotifications.as_view(),
    #     name='notifications'),
]

course_patterns = [
    url(r'^$', endpoints.GetUpdateCourseEndpoint.as_view(),
        name='get'),
    url(r'^administrators/$',
        endpoints.ListAddRemoveCourseAdministratorsEndpoint.as_view(),
        name='admins'),
    url(r'^semesters/$', endpoints.ListAddSemesterEndpoint.as_view(),
        name='semesters')
]

semester_patterns = [
    url(r'^$', endpoints.GetUpdateSemesterEndpoint.as_view(),
        name='get'),
    url(r'^staff/$', endpoints.ListAddRemoveSemesterStaffEndpoint.as_view(),
        name='staff'),
    url(r'^enrolled_students/$', endpoints.ListAddUpdateRemoveEnrolledStudentsEndpoint.as_view(),
        name='enrolled_students'),
    url(r'^projects/$', endpoints.ListAddProjectEndpoint.as_view(),
        name='projects')
]

urlpatterns = [
    url(r'^users/(?P<pk>[0-9]+)/', include(user_patterns, namespace='user')),
    url(r'^courses/$', endpoints.ListCreateCourseEndpoint.as_view(),
        name='courses'),
    url(r'^courses/(?P<pk>[0-9]+)/',
        include(course_patterns, namespace='course')),
    url(r'^semesters/(?P<pk>[0-9]+)/',
        include(semester_patterns, namespace='semester'))


    # url(r'^courses/$', views.CourseList.as_view()),
    # url(r'^courses/(?P<pk>[0-9]+)/$', views.CourseDetail.as_view()),
    # url(r'^semesters/$', views.SemesterList.as_view()),
    # url(r'^semesters/(?P<pk>[0-9]+)/$', views.SemesterDetail.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)
