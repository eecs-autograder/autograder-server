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

    def patch(self, request, project_id):
        try:
            project = Project.objects.get(pk=project_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        can_patch = project.semester.course.is_course_admin(request.user)
        if not can_patch:
            return HttpResponseForbidden()

        request_content = json.loads(request.body.decode('utf-8'))
        to_edit = request_content['data']['attributes']

        if 'visible_to_students' in to_edit:
            project.visible_to_students = to_edit['visible_to_students']

        if 'closing_time' in to_edit:
            project.closing_time = to_edit['closing_time']

        if 'disallow_student_submissions' in to_edit:
            project.disallow_student_submissions = (
                to_edit['disallow_student_submissions'])

        if 'min_group_size' in to_edit:
            project.min_group_size = to_edit['min_group_size']

        if 'max_group_size' in to_edit:
            project.max_group_size = to_edit['max_group_size']

        if 'required_student_files' in to_edit:
            project.required_student_files = to_edit['required_student_files']

        if 'expected_student_file_patterns' in to_edit:
            project.expected_student_file_patterns = (
                to_edit['expected_student_file_patterns'])

        try:
            project.validate_and_save()
            return HttpResponse(status=204)
        except ValidationError as e:
            return JsonResponse(
                {'errors': {'meta': e.message_dict}}, status=409)

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


# -----------------------------------------------------------------------------

class GetProjectFile(LoginRequiredView):
    pass
