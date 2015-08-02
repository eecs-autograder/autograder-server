import json

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.http import (
    HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseBadRequest)

from autograder.frontend.frontend_utils import LoginRequiredView
from autograder.frontend.json_api_serializers import project_to_json

from autograder.models import Semester, Project


class ProjectRequestHandler(LoginRequiredView):
    def get(self, request, project_id):
        try:
            project = Project.objects.get(pk=project_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        is_staff = project.semester.is_semester_staff(request.user)
        is_enrolled = project.semester.is_enrolled_student(request.user)
        can_view_project = (
            is_staff or
            is_enrolled and project.visible_to_students)

        if not can_view_project:
            return HttpResponseForbidden()

        return JsonResponse({'data': project_to_json(project)})

    def post(self, request):
        request_content = json.loads(request.body.decode('utf-8'))
        try:
            semester_json = (
                request_content['data']['relationships']['semester'])
            semester = Semester.objects.get(pk=semester_json['data']['id'])
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        if not semester.course.is_course_admin(request.user):
            return HttpResponseForbidden()

        try:
            project = Project.objects.validate_and_create(
                name=request_content['data']['attributes']['name'],
                semester=semester)
        except ValidationError as e:
            response_content = {
                'errors': {
                    'meta': e.message_dict
                }
            }
            return JsonResponse(response_content, status=409)

        response_content = {
            'data': project_to_json(project)
        }
        return JsonResponse(response_content, status=201)

    # def patch(self, request, project_id):
    #     pass

    def delete(self, request, project_id):
        try:
            project = Project.objects.get(pk=project_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        can_delete = project.semester.course.is_course_admin(request.user)
        if not can_delete:
            return HttpResponseForbidden()

        project.delete()
        return HttpResponse(status=204)


class GetProjectFile(LoginRequiredView):
    pass
