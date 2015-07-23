"""django_autograder URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.contrib import admin

from autograder import views, ajax_request_handlers


urlpatterns = [
    url(r'^list-courses/$',
        ajax_request_handlers.ListCourses.as_view(),
        name='list-courses')

    # LANDING PAGE
    # All:
    #   list active/enrolled course-semesters
    # Course admins and Superusers:
    #   list active courses
    #
    # COURSE ADMIN PAGE
    # Course admins and Superusers:
    #   list course-semesters
    # Course admins:
    #   add semester
    # Superusers:
    #   add course
    #   add course admin
    #   remove course admin
    #
    # COURSE-SEMESTER VIEW
    # All:
    #   list visible projects
    # Course admins:
    #   list all projects
    #   add project
    #   edit project
    #   copy project
    #   delete project
    #
    #   list enrolled students (link to student view)
    #   add enrolled students
    #   remove enrolled students
    #
    #   list course-semester staff
    #   add course-semester staff
    #   remove course-semester staff
    #
    # Course-semester staff:
    #   list enrolled students (link to project view for that student)
    #
    #
    #
    # PROJECT VIEW
    # All:
    #   submit
    #   list current user submissions (collapsable detail list)
    # Course-semester staff and Course admins:
    #   list registered submission groups (collapsable submission list)
    # Course admins:
    #   add submission group
    #   remove submission group
    #
    #   add test case
    #   edit test case
    #   delete test case
    #
    #
    # STUDENT VIEW
    # Course-semester staff and Course admins:
    #   list submission groups
    #   list project submissions
    #
    #
    #
    #
    #
    #
    #
    #

]


# urlpatterns = [
#     # url(r'^admin/', include(admin.site.urls)),

#     url(r'^courses/$', views.AllCoursesView.as_view(),
#         name='course-list'),

#     url(r'^courses/(?P<course_name>.+)/$',
#         views.SingleCourseView.as_view(),
#         name='course-detail'),

#     url(r'^delete-course/(?P<pk>.+)/$',
#         views.DeleteCourse.as_view(),
#         name='delete-course'),

#     url(r'^delete-semester/(?P<course_name>.+)/(?P<semester_name>.+)/$',
#         views.DeleteSemester.as_view(),
#         name='delete-semester'),

#     url(r'^semester/(?P<course_name>.+)/(?P<semester_name>.+)/$',
#         views.SemesterView.as_view(),
#         name='semester-detail'),

#     url(r'^delete-project/(?P<course_name>.+)/(?P<semester_name>.+)/(?P<project_name>.+)/$',
#         views.DeleteProject.as_view(),
#         name='delete-project'),

#     url(r'^project/(?P<course_name>.+)/(?P<semester_name>.+)/(?P<project_name>.+)/$',
#         views.ProjectView.as_view(),
#         name='project-detail'),

#     url(r'^add-project-file/(?P<course_name>.+)/(?P<semester_name>.+)/(?P<project_name>.+)/$',
#         views.AddProjectFile.as_view(),
#         name='add-project-file'),

#     url(r'^view-project-file/(?P<course_name>.+)/(?P<semester_name>.+)/(?P<project_name>.+)/(?P<filename>.+)/$',
#         views.ViewProjectFile.as_view(),
#         name='view-project-file'),

#     url(r'^delete-project-file/(?P<course_name>.+)/(?P<semester_name>.+)/(?P<project_name>.+)/(?P<filename>.+)/$',
#         views.DeleteProjectFile.as_view(),
#         name='delete-project-file'),

#     url(r'^add-or-update-test/(?P<course_name>.+)/(?P<semester_name>.+)/(?P<project_name>.+)/$',
#         views.AddOrUpdateAutograderTest.as_view(),
#         name='add-or-update-test'),

#     url(r'^view-submissions/(?P<course_name>.+)/(?P<semester_name>.+)/(?P<project_name>.+)/$',
#         views.SubmissionList.as_view(),
#         name='view-submissions')
# ]
