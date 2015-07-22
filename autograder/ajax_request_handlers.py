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
from django.http import HttpResponse, HttpResponseRedirect

# from django.views.decorators.csrf import ensure_csrf_cookie
# from django.utils.decorators import method_decorator


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


class ListCourses(ExceptionLoggingView):
    """
    Permissions required: Course admin or Superuser
    """
    pass


class AddCourse(ExceptionLoggingView):
    """
    Permissions required: Superuser
    """
    pass


class AddCourseAdmin(ExceptionLoggingView):
    """
    Permissions required: Superuser
    """
    pass


class RemoveCourseAdmin(ExceptionLoggingView):
    """
    Permissions required: Superuser
    """
    pass


# -----------------------------------------------------------------------------

class ListSemesters(ExceptionLoggingView):
    """
    Reponse list content determinied by user permissions.
    """
    pass


class AddSemester(ExceptionLoggingView):
    """
    Permissions required: Course admin
    """
    pass


class ListSemesterStaff(ExceptionLoggingView):
    """
    Permissions required: Course admin or Semester staff
    """
    pass


class AddSemesterStaff(ExceptionLoggingView):
    """
    Permissions required: Course admin
    """
    pass


class RemoveSemesterStaff(ExceptionLoggingView):
    """
    Permissions required: Course admin
    """
    pass


class ListEnrolledStudents(ExceptionLoggingView):
    """
    Permissions required: Course admin or Semester staff
    """
    pass


class AddEnrolledStudents(ExceptionLoggingView):
    """
    Permissions required: Course admin or Semester staff
    """
    pass


class RemoveEnrolledStudents(ExceptionLoggingView):
    """
    Permissions required: Course admin
    """
    pass


# -----------------------------------------------------------------------------

class ListProjects(ExceptionLoggingView):
    """
    Reponse list content determinied by user permissions.
    """
    pass


class AddProject(ExceptionLoggingView):
    """
    Permissions required: Course admin
    """
    pass


class EditProject(ExceptionLoggingView):
    """
    Permissions required: Course admin
    """
    pass


class DeleteProject(ExceptionLoggingView):
    """
    Permissions required: Course admin
    """
    pass


class CopyProjectForNewSemester(ExceptionLoggingView):
    """
    Permissions required: Course admin
    """
    pass


class SubmitProject(ExceptionLoggingView):
    """

    """
    pass


class ListSubmissions(ExceptionLoggingView):
    """
    Reponse list content determinied by user permissions.
    """
    pass


class ListSubmissionGroups(ExceptionLoggingView):
    """
    Reponse list content determinied by user permissions.
    """
    pass


class AddSubmissionGroup(ExceptionLoggingView):
    """
    Permissions required: Course admin
    """
    pass


class RemoveSubmissionGroup(ExceptionLoggingView):
    """
    Permissions required: Course admin
    """
    pass
