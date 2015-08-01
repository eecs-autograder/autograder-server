import os
import json
import traceback
# import datetime

from django.utils import timezone

from django.contrib.auth.models import User

from django.views.generic.base import View
from django.views.generic.edit import CreateView, DeleteView

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.forms.forms import NON_FIELD_ERRORS

from django.shortcuts import get_object_or_404, render

from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.http import (
    HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseBadRequest)

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

# from django.views.decorators.csrf import ensure_csrf_cookie
# from django.utils.decorators import method_decorator
from autograder.models import Course, Semester
from autograder.frontend.json_api_serializers import (
    course_to_json, semester_to_json, project_to_json)


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


class GetCourse(LoginRequiredView):
    def get(self, request, course_id):
        try:
            course = Course.objects.get(pk=course_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        if not course.is_course_admin(self.request.user):
            return HttpResponseForbidden()

        response_content = {
            'data': course_to_json(course),
            'included': [
                {
                    'data': semester_to_json(
                        semester, with_fields=False,
                        user_is_semester_staff=True)
                }
                for semester in course.semesters.all().order_by('pk')
            ]
        }

        return JsonResponse(response_content, safe=False)


class ListCourses(LoginRequiredView):
    """
    Reponse list content determinied by user permissions.
    """
    def get(self, request):
        courses = Course.get_courses_for_user(request.user)
        data = {
            'data': [
                course_to_json(course) for course in courses
            ]
        }

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

class SemesterRequestHandler(LoginRequiredView):
    def get(self, request, semester_id):
        try:
            semester = Semester.objects.get(pk=semester_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        is_staff = semester.is_semester_staff(request.user)

        if semester.is_enrolled_student(request.user):
            included = [
                project_to_json(project, with_fields=False) for project in
                semester.projects.filter(visible_to_students=True)
            ]
        elif is_staff:
            included = [
                project_to_json(project, with_fields=False) for project in
                semester.projects.all()
            ]
        else:
            return HttpResponseForbidden()

        data = {
            'data': semester_to_json(
                semester, user_is_semester_staff=is_staff),
            'included': included
        }

        return JsonResponse(data, safe=False)

    def patch(self, request, semester_id):
        try:
            semester = Semester.objects.get(pk=semester_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        if not semester.course.is_course_admin(request.user):
            return HttpResponseForbidden()

        body = json.loads(request.body.decode('utf-8'))
        try:
            patch_instructions = body['meta']
        except KeyError:
            return HttpResponseBadRequest('No metadata included')

        staff_to_add = patch_instructions.get('add_semester_staff', None)
        staff_to_remove = patch_instructions.get('remove_semester_staff', None)

        if staff_to_add and staff_to_remove:
            return HttpResponseBadRequest(
                "Can't add and remove staff in the same PATCH request")

        students_to_add = patch_instructions.get('add_enrolled_students', None)
        students_to_remove = patch_instructions.get(
            'remove_enrolled_students', None)

        if students_to_add and students_to_remove:
            return HttpResponseBadRequest(
                "Can't add and remove students in the same PATCH request")

        if not (staff_to_add or staff_to_remove or
                students_to_add or students_to_remove):
            return HttpResponseBadRequest(
                "No PATCH operations included")

        if staff_to_add:
            users = [User.objects.get_or_create(username=username)[0]
                     for username in staff_to_add]
            semester.add_semester_staff(*users)
        elif staff_to_remove:
            users = [User.objects.get_or_create(username=username)[0]
                     for username in staff_to_remove]
            semester.remove_semester_staff(*users)

        if students_to_add:
            users = [User.objects.get_or_create(username=username)[0]
                     for username in students_to_add]
            semester.add_enrolled_students(*users)
        elif students_to_remove:
            users = [User.objects.get_or_create(username=username)[0]
                     for username in students_to_remove]
            semester.remove_enrolled_students(*users)

        return HttpResponse(status=204)


class ListSemesters(LoginRequiredView):
    """
    Reponse list content determinied by user permissions.
    """
    def get(self, request):
        staff_semesters = Semester.get_staff_semesters_for_user(request.user)
        enrolled_semesters = Semester.get_enrolled_semesters_for_user(
            request.user)

        data = {
            'data': [
                semester_to_json(semester, user_is_semester_staff=True)
                for semester in staff_semesters.all()
            ]
        }

        data['data'] += [
            semester_to_json(semester) for semester in enrolled_semesters.all()
        ]

        return JsonResponse(data, safe=False)


class AddSemester(LoginRequiredView):
    """
    Permissions required: Course admin
    """
    def post(self, request):
        course = Course.objects.get(name=request.POST['course_name'])
        if not course.is_course_admin(request.user):
            return HttpResponseForbidden()

        try:
            new_semester = Semester.objects.validate_and_create(
                name=request.POST['semester_name'],
                course=course)
            return JsonResponse({
                'semester_name': new_semester.name,
                'course_name': course.name
            })
        except ValidationError as e:
            return JsonResponse({'errors': e.message_dict}, safe=False)


class ListSemesterStaff(LoginRequiredView):
    """
    Permissions required: Course admin or Semester staff
    """
    def post(self, request):
        course = Course.objects.get(name=request.POST['course_name'])
        semester = Semester.objects.get(
            name=request.POST['semester_name'], course=course)

        can_view_staff = (
            semester.is_semester_staff(request.user) or
            course.is_course_admin(request.user))
        if not can_view_staff:
            return HttpResponseForbidden()

        data = {
            'semester_name': semester.name,
            'course_name': course.name,
            'semester_staff': semester.semester_staff_names,
            'course_admins': course.course_admin_names
        }

        return JsonResponse(data, safe=False)


class AddSemesterStaff(LoginRequiredView):
    """
    Permissions required: Course admin
    """
    def post(self, request):
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

class ProjectRequestHandler(LoginRequiredView):
    pass


class GetProjectFile(LoginRequiredView):
    pass


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
