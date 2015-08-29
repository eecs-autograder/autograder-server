import json

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.http import (
    HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound)

from autograder.frontend.frontend_utils import LoginRequiredView
from autograder.frontend.json_api_serializers import (
    autograder_test_case_to_json)

from autograder.models import (
    Project, AutograderTestCaseBase, AutograderTestCaseFactory)


class AutograderTestCaseRequestHandler(LoginRequiredView):
    _EDITABLE_FIELDS = [
        'name',
        'hide_from_students',
        'command_line_arguments',
        'standard_input',
        'test_resource_files',
        'time_limit',
        'expected_return_code',
        'expect_any_nonzero_return_code',
        'expected_standard_output',
        'expected_standard_error_output',
        'use_valgrind',
        'valgrind_flags',
        'compiler',
        'compiler_flags',
        'files_to_compile_together',
        'executable_name'
    ]

    def get(self, request, test_id):
        try:
            test_case = AutograderTestCaseBase.objects.get(pk=test_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        if not test_case.project.semester.is_semester_staff(request.user):
            return HttpResponseForbidden()

        is_admin = (
            test_case.project.semester.course.is_course_admin(request.user))
        response_content = {
            'data': autograder_test_case_to_json(test_case),
            'meta': {
                'permissions': {
                    'can_edit': is_admin,
                    'can_delete': is_admin
                }
            }
        }

        return JsonResponse(response_content)

    def post(self, request):
        request_content = json.loads(request.body.decode('utf-8'))
        project_json = request_content['data']['relationships']['project']
        try:
            project = Project.objects.get(pk=project_json['data']['id'])
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        if not project.semester.course.is_course_admin(request.user):
            return HttpResponseForbidden()

        type_str = request_content['data']['type']

        try:
            new_test = AutograderTestCaseFactory.new_instance(
                type_str, project=project)
            to_set = request_content['data']['attributes']
            for field in AutograderTestCaseRequestHandler._EDITABLE_FIELDS:
                if field in to_set:
                    setattr(new_test, field, to_set[field])
        except ValueError:
            return HttpResponse('Invalid test case type', status=400)

        try:
            new_test.validate_and_save()

            response_content = {
                'data': autograder_test_case_to_json(new_test)
            }

            return JsonResponse(response_content, status=201)
        except ValidationError as e:
            response_content = {
                'errors': {
                    'meta': e.message_dict
                }
            }
            return JsonResponse(response_content, status=409)

    def patch(self, request, test_id):
        try:
            test_case = AutograderTestCaseBase.objects.get(pk=test_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        if not test_case.project.semester.course.is_course_admin(request.user):
            return HttpResponseForbidden()

        request_content = json.loads(request.body.decode('utf-8'))
        to_edit = request_content['data']['attributes']

        for field in AutograderTestCaseRequestHandler._EDITABLE_FIELDS:
            if field in to_edit:
                setattr(test_case, field, to_edit[field])

        try:
            test_case.validate_and_save()
            return HttpResponse(status=204)
        except ValidationError as e:
            return JsonResponse(
                {'errors': {'meta': e.message_dict}}, status=409)

    def delete(self, request, test_id):
        try:
            test_case = AutograderTestCaseBase.objects.get(pk=test_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        if not test_case.project.semester.course.is_course_admin(request.user):
            return HttpResponseForbidden()

        test_case.delete()

        return HttpResponse(status=204)
