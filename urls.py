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
from django.contrib.auth import views as auth_views

from autograder.frontend import views, ajax_request_handlers

import autograder.shared.global_constants as gc


urlpatterns = [

    # url(r'^oauth2/', include('provider.oauth2.urls', namespace='oauth2')),

    # url(r'^accounts', include('django.contrib.auth.urls')),
    # url(r'^accounts/login/$', auth_views.login),

    # url(r'^login/$', auth_views.login,
    #     {'template_name': 'autograder/login.html',
    #      'authentication_form': views.LoginForm}, name='login'),

    url(r'^/tasky/$', views.Tasky.as_view(), name='tasky'),

    url(r'^login/$', views.LoginView.as_view(), name='login'),

    url(r'^logout/$', views.LogoutView.as_view(), name='logout'),

    url(r'^callback/$', views.LoginView.as_view(), name='callback'),

    url(r'^courses/course/(?P<course_id>\d+)/$',
        ajax_request_handlers.GetCourse.as_view(),
        name='get-course'),

    url(r'^courses/$',
        ajax_request_handlers.ListCourses.as_view(),
        name='list-courses'),

    url(r'^semesters/semester/(?P<semester_id>\d+)/$',
        ajax_request_handlers.SemesterRequestHandler.as_view(),
        name='semester-handler'),

    url(r'^semesters/semester/$',
        ajax_request_handlers.SemesterRequestHandler.as_view(),
        name='add-semester'),

    url(r'^semesters/$',
        ajax_request_handlers.ListSemesters.as_view(),
        name='list-semesters'),

    url(r'^projects/project/(?P<project_id>\d+)/$',
        ajax_request_handlers.ProjectRequestHandler.as_view(),
        name='project-handler'),

    url(r'^projects/project/$',
        ajax_request_handlers.ProjectRequestHandler.as_view(),
        name='add-project'),

    url(r'^projects/project/(?P<project_id>\d+)/file/(?P<filename>{})/$'.format(
        gc.PROJECT_FILENAME_WHITELIST_REGEX.pattern),
        ajax_request_handlers.ProjectFileRequestHandler.as_view(),
        name='project-file-handler'),

    url(r'^projects/project/(?P<project_id>\d+)/add-file/$',
        ajax_request_handlers.ProjectFileRequestHandler.as_view(),
        name='add-project-file'),

    url(r'^ag-test-cases/ag-test-case/(?P<test_id>\d+)/$',
        ajax_request_handlers.AutograderTestCaseRequestHandler.as_view(),
        name='ag-test-handler'),

    url(r'^ag-test-cases/ag-test-case/$',
        ajax_request_handlers.AutograderTestCaseRequestHandler.as_view(),
        name='add-ag-test-case'),

    url(r'^submission-groups/submission-group/$',
        ajax_request_handlers.SubmissionGroupRequestHandler.as_view(),
        name='submission-group-no-id'),

    url(r'^submission-groups/submission-group/(?P<submission_group_id>\d+)/$',
        ajax_request_handlers.SubmissionGroupRequestHandler.as_view(),
        name='submission-group-with-id'),

    url(r'^submissions/submission/(?P<submission_id>\d+)/$',
        ajax_request_handlers.SubmissionRequestHandler.as_view(),
        name='submission-handler'),

    url(r'^submissions/submission/$',
        ajax_request_handlers.SubmissionRequestHandler.as_view(),
        name='add-submission'),

    url(r'^submissions/submission/(?P<submission_id>\d+)/file/(?P<filename>{})/$'.format(
        gc.PROJECT_FILENAME_WHITELIST_REGEX.pattern),
        ajax_request_handlers.SubmittedFileRequestHandler.as_view(),
        name='get-submitted-file'),

    url(r'^/*', views.MainAppPage.as_view(), name='main-app-page'),

    # --- COURSES ---
    #   json format:
    #   {
    #       'data': {
    #           'type': 'course',
    #           'id': <id>,
    #           'attributes': {
    #               'name': <name>,
    #               'course_admin_names': [<admin username>, ...]
    #           },
    #           'links': {
    #               'self': <self link>
    #           }
    #       },
    #       'included': [
    #           {
    #               'type': 'semester',
    #               'id': <semester-id>,
    #               'links': {
    #                   'self': <link to semester>
    #               }
    #           },
    #           ...
    #       ],
    #
    #       'errors': {
    #           'meta': <json error data from database api>
    #       }
    #   }
    #
    # GET                       /courses
    # POST                      /courses/course
    # GET PATCH (DELETE)        /courses/course/<course-id>
    #
    # --- SEMESTERS ---
    #   json format:
    #   {
    #       'data': {
    #           'type': 'semester',
    #           'id': <id>
    #           'attributes': {
    #               'name': <name>,
    #               'semester_staff_names': [<staff username>, ...],
    #               'enrolled_student_names': [<student username>, ...]
    #           },
    #           'relationships': {
    #               'course': {
    #                   'data': {
    #                       'type': 'course',
    #                       'id': <course-id>,
    #                       'links': {
    #                           'self': <course url>
    #                       }
    #                   }
    #               }
    #           },
    #           'links': {
    #               'self': <self link>
    #           },
    #           'meta': {
    #               'is_staff': <true> | <false
    #           }
    #       },
    #       included: [
    #           {
    #               'type': 'project',
    #               'id': <project-id>,
    #               'links': {
    #                   'self': <link to project>
    #               }
    #           },
    #           ...
    #       ],
    #
    #       'errors': {
    #           'meta': <json error data from database api>
    #       },
    #
    #       'meta': { // for PATCH requests
    #           'add_semester_staff': [<name to add>, ...],
    #           'remove_semester_staff': [<name to add>, ...]
    #       }
    #   }
    #
    # GET                       /semesters
    # POST                      /semesters/semester
    # GET PATCH (DELETE)        /semesters/semester/<semester-id>
    #
    # --- PROJECTS ---
    #   json format:
    #   {
    #       'data': {
    #           'type': 'project',
    #           'id': <id>,
    #           'links': {
    #               'self': <self link>
    #           },
    #           'attributes': {
    #               <project attributes>
    #               ...
    #               'project_files': [
    #                   {
    #                       'filename': <filename>,
    #                       'file_url': <file url>
    #                   },
    #                   ...
    #               ]
    #           },
    #           'relationships': {
    #               'semester': {
    #                   'data': {
    #                       'type': 'semester',
    #                       'id': <semester-id,
    #                       'links': {
    #                           'self': <semester url>,
    #                       }
    #                   }
    #               }
    #           }
    #       },
    #       'included': [
    #           {
    #               'type': 'autograder-test-case',
    #               'id': <id>,
    #               'links': {
    #                   'self': <link for test case>
    #               }
    #           },
    #           ...
    #       ],
    #
    #       'errors': {
    #           'meta': <json error data from database api>
    #       }
    #   }
    #
    # POST                      /projects/project
    # POST                      /projects/project/<project-id>/copy-to-semester/<semester-id>
    # GET PATCH DELETE          /projects/project/<project-id>
    # POST                      /projects/project/<project-id>/add-file
    # GET PATCH DELETE          /projects/project/<project-id>/file/<filename>
    #
    # --- AUTOGRADER TEST CASES ---
    # POST                      /ag-test-cases/ag-test-case
    # POST                      /ag-test-cases/ag-test-case/<ag-test-case-id>/copy
    # GET PATCH DELETE          /ag-test-cases/ag-test-case/<ag-test-case-id>
    #
    # --- SUBMISSIONS ---
    #   json format:
    #   {
    #       'data': {
    #           'type': 'submission',
    #           'id': <id>,
    #           'attributes': {
    #               'status': <status>
    #           },
    #           'relationships': {
    #               'submission_group': {
    #                   'links': {
    #                       'self': <self link>
    #                   },
    #                   'data': {'type': 'submission_group', 'id': <id>}
    #               }
    #           }
    #       }
    #   }
    #
    # GET                       /submissions?project=<project-id>, user=<user-id>, submission-group=<submission-group-id>
    # POST                      /submissions/submission
    # GET PATCH                 /submissions/submission/<submission-id>
    # GET                       /submissions/submission/<submission-id>/file/<filename>
    #
    # --- SUBMISSION GROUPS ---
    #   json format:
    #   {
    #       'data': {
    #           'type': 'submission_group',
    #           'id': <id>,
    #           'attributes': {
    #               'members': [<username>, ...],
    #               'extended_due_date': <date>
    #           },
    #           'relationships': {
    #               'project': {
    #                   'links': {
    #                       'self': <self link>
    #                   },
    #                   'data': {'type': 'project', 'id': <id>}
    #               },
    #           }
    #       }
    #   }
    #
    # POST                      /submission-groups/submission-group
    # GET                       /submission-groups/submission-group/?project=<project-id>&user=<user-id>
    # GET PATCH DELETE          /submission-groups/submission-group/<submission-group-id>
    #
    #
    #
    #


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
