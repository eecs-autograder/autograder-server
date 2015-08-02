import json

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.http import (
    HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseBadRequest)

from autograder.frontend.frontend_utils import LoginRequiredView
from autograder.frontend.json_api_serializers import project_to_json

from autograder.models import Semester, Project


class ProjectRequestHandler(LoginRequiredView):
    # def get(self, request, project_id):
    #     pass

    def post(self, request):
        request_content = json.loads(request.body.decode('utf-8'))
        try:
            semester = Semester.objects.get(
                pk=request_content['data']['relationships']['semester']['data']['id']
            )
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

    # def delete(self, request, project_id):
    #     pass


class GetProjectFile(LoginRequiredView):
    pass
