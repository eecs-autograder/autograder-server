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
from autograder.views import course_views

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),

    url(r'^courses/(?P<course_name>.+)/$',
        course_views.ShowCourseDetail.as_view(),
        name='course-detail'),

    url(r'^courses/', course_views.ShowCourseList.as_view(),
        name='course-list'),

    url(r'^delete-course/(?P<pk>.+)/$',
        course_views.DeleteCourse.as_view(),
        name='delete-course'),

    url(r'^delete-semester/(?P<course_name>.+)/(?P<semester_name>.+)/$',
        course_views.DeleteSemester.as_view(),
        name='delete-semester')
]
