from django.conf.urls import url, include
from rest_framework.urlpatterns import format_suffix_patterns
from autograder.rest_api import request_handlers

user_patterns = [
    url(r'^$', request_handlers.GetUser.as_view(), name='get'),
    url(r'^courses_is_admin_for/$',
        request_handlers.GetUserCoursesIsAdminFor.as_view(),
        name='admin-courses'),
    url(r'^semesters_is_staff_for/$',
        request_handlers.GetUserSemstersIsStaffFor.as_view(),
        name='staff-semesters'),
    url(r'^semesters_is_enrolled_in/$',
        request_handlers.GetUserSemestersIsEnrolledIn.as_view(),
        name='enrolled-semesters'),
    url(r'^groups_is_member_of/$',
        request_handlers.GetUserGroupsIsMemberOf.as_view(),
        name='submission-groups'),
    url(r'^pending_group_requests/$',
        request_handlers.GetUserPendingGroupRequests.as_view(),
        name='pending-group-requests'),
    url(r'^notifications/$',
        request_handlers.GetUserNotifications.as_view(),
        name='notifications'),
]

course_patterns = [
    url(r'^$', request_handlers.RetrieveUpdateCourseHandler.as_view(),
        name='get')
]

urlpatterns = [
    url(r'^users/(?P<pk>[0-9]+)/', include(user_patterns, namespace='user')),
    url(r'^courses/(?P<pk>[0-9]+)/',
        include(course_patterns, namespace='course')),



    # url(r'^courses/$', views.CourseList.as_view()),
    # url(r'^courses/(?P<pk>[0-9]+)/$', views.CourseDetail.as_view()),
    # url(r'^semesters/$', views.SemesterList.as_view()),
    # url(r'^semesters/(?P<pk>[0-9]+)/$', views.SemesterDetail.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)
