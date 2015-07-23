import os
import json
import traceback
# import datetime

from django.utils import timezone

from django.views.generic.base import View
from django.views.generic.edit import CreateView, DeleteView

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.forms.forms import NON_FIELD_ERRORS

from django.shortcuts import get_object_or_404, render

from django.template import RequestContext
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

# from django.views.decorators.csrf import ensure_csrf_cookie
# from django.utils.decorators import method_decorator
from autograder.models import Course, Semester


class ExceptionLoggingView(View):
    """
    View base class that catches any exceptions thrown from dispatch(),
    prints them to the console, and then rethrows.
    """
    def dispatch(self, *args, **kwargs):
        try:
            return super().dispatch(*args, **kwargs)
        except Exception:
            traceback.print_exc()
            raise


class LoginRequiredView(ExceptionLoggingView):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class ListCourses(LoginRequiredView):
    """
    Reponse list content determinied by user permissions.
    """
    def post(self, request):
        courses = Course.get_courses_for_user(request.user)
        data = [
            {'name': course.name,
             'admins': course.course_admins}
            for course in courses
        ]
        return JsonResponse(data, safe=False)


# Move superuser things to Django Admin page
# class AddCourse(ExceptionLoggingView):
#     """
#     Permissions required: Superuser
#     """
#     pass


# class AddCourseAdmin(ExceptionLoggingView):
#     """
#     Permissions required: Superuser
#     """
#     pass


# class RemoveCourseAdmin(ExceptionLoggingView):
#     """
#     Permissions required: Superuser
#     """
#     pass


# -----------------------------------------------------------------------------

class ListSemesters(LoginRequiredView):
    """
    Reponse list content determinied by user permissions.
    """
    def post(self, request):
        semesters = Semester.get_semesters_for_user(request.user)

class AddSemester(LoginRequiredView):
    """
    Permissions required: Course admin
    """
    pass


class ListSemesterStaff(LoginRequiredView):
    """
    Permissions required: Course admin or Semester staff
    """
    pass


class AddSemesterStaff(LoginRequiredView):
    """
    Permissions required: Course admin
    """
    pass


class RemoveSemesterStaff(LoginRequiredView):
    """
    Permissions required: Course admin
    """
    pass


class ListEnrolledStudents(LoginRequiredView):
    """
    Permissions required: Course admin or Semester staff
    """
    pass


class AddEnrolledStudents(LoginRequiredView):
    """
    Permissions required: Course admin or Semester staff
    """
    pass


class RemoveEnrolledStudents(LoginRequiredView):
    """
    Permissions required: Course admin
    """
    pass


# -----------------------------------------------------------------------------

class ListProjects(LoginRequiredView):
    """
    Reponse list content determinied by choice of Semester
    and user permissions.
    """
    pass


class AddProject(LoginRequiredView):
    """
    Permissions required: Course admin
    """
    pass


class EditProject(LoginRequiredView):
    """
    Permissions required: Course admin
    """
    pass


class DeleteProject(LoginRequiredView):
    """
    Permissions required: Course admin
    """
    pass


class AddTestCase(LoginRequiredView):
    """
    Permissions required: Course admin
    """
    pass


class EditTestCase(LoginRequiredView):
    """
    Permissions required: Course admin
    """
    pass


class DeleteTestCase(LoginRequiredView):
    """
    Permissions required: Course admin
    """
    pass


class CopyTestCase(LoginRequiredView):
    """
    Permissions required: Course admin
    """
    pass


class CopyProjectForNewSemester(LoginRequiredView):
    """
    Permissions required: Course admin
    """
    pass


class SubmitProject(LoginRequiredView):
    """

    """
    pass


class ListSubmissions(LoginRequiredView):
    """
    Reponse list content determinied by user permissions.
    """
    pass


class ListSubmissionGroups(LoginRequiredView):
    """
    Reponse list content determinied by user permissions.
    """
    pass


class AddSubmissionGroup(LoginRequiredView):
    """
    Permissions required: Course admin
    """
    pass


class RemoveSubmissionGroup(LoginRequiredView):
    """
    Permissions required: Course admin
    """
    pass
