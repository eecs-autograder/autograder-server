import json

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.http import (
    HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseBadRequest)

from autograder.frontend.frontend_utils import LoginRequiredView
from autograder.frontend.json_api_serializers import (
    semester_to_json, project_to_json)

from autograder.models import Course, Semester


class SemesterRequestHandler(LoginRequiredView):
    def get(self, request, semester_id):
        try:
            semester = Semester.objects.get(pk=semester_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        is_staff = semester.is_semester_staff(request.user)

        if semester.is_enrolled_student(request.user):
            included = [
                project_to_json(project, all_fields=False) for project in
                semester.projects.filter(visible_to_students=True)
            ]
        elif is_staff:
            included = [
                project_to_json(project, all_fields=False) for project in
                semester.projects.all()
            ]
        else:
            return HttpResponseForbidden()

        data = {
            'data': semester_to_json(
                semester, user_is_semester_staff=is_staff),
            'included': included,
            'meta': {
                'is_staff': semester.is_semester_staff(request.user),
                'can_edit': semester.course.is_course_admin(request.user)
            }
        }

        return JsonResponse(data)

    def post(self, request):
        request_json = json.loads(request.body.decode('utf-8'))

        course = Course.objects.get(
            pk=request_json['data']['relationships']['course']['data']['id'])
        if not course.is_course_admin(request.user):
            return HttpResponseForbidden()

        try:
            new_semester = Semester.objects.validate_and_create(
                name=request_json['data']['attributes']['name'],
                course=course)

            response_json = {
                'data': semester_to_json(
                    new_semester, user_is_semester_staff=True)
            }
            return JsonResponse(response_json, status=201)
        except ValidationError as e:
            response_json = {
                'errors': {
                    'meta': e.message_dict
                }
            }
            return JsonResponse(response_json, status=409)

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

        return JsonResponse(data)
